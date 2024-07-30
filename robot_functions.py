import ephem
import pandas as pd
from datetime import datetime, timedelta
import pytz
import os
import json
import time
import RPi.GPIO as GPIO

# Configuration
latitude = 55.4199
longitude = 11.5428
timezone = 'Europe/Copenhagen'
timezone_obj = pytz.timezone(timezone)
settings_file = '/home/annelaura/FH/robot/door_control_settings.json'
status_file = '/home/annelaura/FH/robot/door_control_status.json'

# Define GPIO pins for each door
DOOR_CHANNELS = {
    "door1_open": 17,  # GPIO17
    "door1_close": 27,  # GPIO27
    "door2_open": 22,  # GPIO22
    "door2_close": 10,  # GPIO10
    "nest_open": 9,    # GPIO9
    "nest_close": 11,  # GPIO11
}

def create_observer(lat, lon, timezone):
    # Set the location
    observer = ephem.Observer()
    observer.lat = str(latitude)
    observer.lon = str(longitude)

    # Set the timezone
    timezone = 'Europe/Copenhagen'
    timezone_obj = pytz.timezone(timezone)
    observer.date = datetime.now(timezone_obj)

    return observer

def get_astronomical_events(observer):
    sun = ephem.Sun()
    events = {
        'next_sunrise': observer.next_rising(sun).datetime().replace(tzinfo=pytz.UTC).astimezone(timezone_obj),
        'next_sunset': observer.next_setting(sun).datetime().replace(tzinfo=pytz.UTC).astimezone(timezone_obj),
        'previous_sunrise': observer.previous_rising(sun).datetime().replace(tzinfo=pytz.UTC).astimezone(timezone_obj),
        'previous_sunset': observer.previous_setting(sun).datetime().replace(tzinfo=pytz.UTC).astimezone(timezone_obj),
    }

    # Calculate civil twilight (dawn and dusk)
    observer.horizon = '-6'  # Civil twilight horizon

    twilight_events = {
        'next_civil_dawn': observer.next_rising(sun, use_center=True).datetime().replace(tzinfo=pytz.UTC).astimezone(timezone_obj),
        'next_civil_dusk': observer.next_setting(sun, use_center=True).datetime().replace(tzinfo=pytz.UTC).astimezone(timezone_obj),
        'previous_civil_dawn': observer.previous_rising(sun, use_center=True).datetime().replace(tzinfo=pytz.UTC).astimezone(timezone_obj),
        'previous_civil_dusk': observer.previous_setting(sun, use_center=True).datetime().replace(tzinfo=pytz.UTC).astimezone(timezone_obj),
    }

    events.update(twilight_events)

    return events

def create_dataframe(lat, lon, timezone_str):
    timezone_obj = pytz.timezone(timezone_str)
    observer = create_observer(lat, lon, timezone_obj)
    events = get_astronomical_events(observer)
    
    df = pd.DataFrame(events.items(), columns=['Event', 'DateTime']).set_index('Event')
    df['simple_datetime']=df['DateTime'].dt.strftime('%d-%m-%Y %H:%M:%S')
    return df


def calculate_door_time(calculate_by="daily", sunrise_offset=0, sunset_offset=0, fixed_open_hour=5, fixed_open_minute=0, fixed_close_hour=23, fixed_close_minute=0):
    if calculate_by == "daily":
        todays_info = create_dataframe(lat=latitude, lon=longitude, timezone_str=timezone)
        door_open = todays_info.loc['next_sunrise','DateTime']- timedelta(minutes=sunrise_offset)
        door_close = todays_info.loc['next_sunset','DateTime']+timedelta(minutes=sunset_offset)
    elif calculate_by == "fixed":
        today = datetime.today()
        timezone_obj = pytz.timezone(timezone)
        door_open = datetime(today.year, today.month, today.day, fixed_open_hour, fixed_open_minute, tzinfo=timezone_obj)
        door_close = datetime(today.year, today.month, today.day, fixed_close_hour, fixed_close_minute, tzinfo=timezone_obj)
    return door_open, door_close 

def get_next_actions():
    settings = load_settings()
    now = datetime.now(timezone_obj)
    #sunrise, dawn = get_sunrise_dawn_times()
    todays_info = create_dataframe(lat=latitude, lon=longitude, timezone_str=timezone)
    
    next_actions = {}
    for door in settings.get('door_open_times', {}):
        open_time = datetime.strptime(settings['door_open_times'][door]['time'], '%H:%M').time()
        if settings['door_open_times'][door]['type'] == 'daily':
            open_time = (todays_info.loc['next_sunrise','DateTime']- timedelta(minutes=settings['sunrise_offset'])).time()
            print(f"Adjusted open time for {door} to {open_time}.")

        close_time = datetime.strptime(settings['door_close_times'][door]['time'], '%H:%M').time()
        if settings['door_close_times'][door]['type'] == 'daily':
            close_time = (todays_info.loc['next_sunset','DateTime']+timedelta(minutes=settings['sunset_offset'])).time()
            print(f"Adjusted close time for {door} to {close_time}.")
        
        next_actions[door] = {
            'open': open_time,
            'close': close_time
        }

    #door_states = {door: "Unknown" for door in DOOR_CHANNELS.keys() if "open" in door or "close" in door}
    print(f"Next actions: {next_actions}")
    write_status_to_file(door_states, next_sunrise, next_sunset)
    print("Status file updated.")

def control_doors():
    print('Starting robot control loop.')
    while True:
        settings = load_settings()
        status = load_status()
        now = datetime.now(timezone_obj)
        todays_info = create_dataframe(lat=latitude, lon=longitude, timezone_str=timezone)
        next_sunrise = todays_info.loc['next_sunrise','DateTime']
        next_sunset = todays_info.loc['next_sunset','DateTime']
        door_states = status.get('door_states', {})
        print(door_states)
        door_actions = status.get('door_actions', {})      
        print(door_actions)
        # Calculate door actions based on settings
        for door in settings.get('door_open_times', {}):
            open_time = datetime.strptime(settings['door_open_times'][door]['time'], '%H:%M').time()
            if settings['door_open_times'][door]['type'] == 'daily':
                open_time = (todays_info.loc['next_sunrise','DateTime']- timedelta(minutes=settings['sunrise_offset'])).time().strftime("%H:%M")
                open_time = datetime.strptime(open_time, '%H:%M').time()
            door_actions['open_times'][door] = open_time           
        for door in settings.get('door_close_times', {}):
            close_time = datetime.strptime(settings['door_close_times'][door]['time'], '%H:%M').time()
            if settings['door_close_times'][door]['type'] == 'daily':
                close_time = (todays_info.loc['next_sunset','DateTime']+timedelta(minutes=settings['sunset_offset'])).time().strftime("%H:%M")
                close_time = datetime.strptime(close_time, '%H:%M').time()
            door_actions['close_times'][door] = close_time
        # Perform door control based on actions
        for door in status.get('door_states', {}):
            # Check if remote control has been pressed
            if door_states[door] == "remote_open":
                remote_time = settings['remote_time']
                open_door(door, settings['door_open_times'][door]['duration'])
                print(f"Remote time = {remote_time}")
                print(f"Remote opening {door} for {remote_time} minutes before returning to schedule")
                time.sleep(remote_time*60) # opens for 15 minutes
                door_states[door] = "unknown"
            elif door_states[door] == "remote_close":
                remote_time = settings['remote_time']
                close_door(door, settings['door_close_times'][door]['duration']) 
                print(f"Remote time = {remote_time}")
                print(f"Remote closing {door} for {remote_time} minutes before returning to schedule.")
                time.sleep(remote_time*60)
                door_states[door] = "unknown"
            # Control doors according to time and schedule
            if now.time()>door_actions['open_times'][door] and now.time()<door_actions['close_times'][door]:
                # door should be open
                if door_states[door] in ("closed", "unknown"):
                    print(f"Opening {door}.")
                    open_door(door, settings['door_open_times'][door]['duration'])
                    door_states[door] = "open"
                else:
                    door_states[door] = "open"
            else:
                # door should be closed
                if door_states[door] in ("open", "unknown"):
                    print(f"Closing {door}.")
                    close_door(door, settings['door_close_times'][door]['duration'])
                    door_states[door] = "closed"
                else:
                    door_states[door] = "closed"
        print(f"Current time: {now}")
        write_status_to_file(door_states, next_sunrise, next_sunset, door_actions)
        time.sleep(30)  # Check every 30 seconds

def open_door(door, duration):
    print(f"Opening {door} for {duration} seconds.")
    gpio_output(DOOR_CHANNELS[f"{door}_open"], True)
    # OBS add "opening" door_state to status file
    time.sleep(duration)
    gpio_output(DOOR_CHANNELS[f"{door}_open"], False)
    # OBS add "open" door_state to status file

def close_door(door, duration):
    print(f"Closing {door} for {duration} seconds.")
    gpio_output(DOOR_CHANNELS[f"{door}_close"], True)
    # OBS add "closing" door_state to status file
    time.sleep(duration)
    gpio_output(DOOR_CHANNELS[f"{door}_close"], False)
    # OBS add "closed" door_state to status file

# GPIO setup
def setup_gpio():
    print("Setting up GPIO pins.")
    GPIO.setmode(GPIO.BCM)
    for channel in DOOR_CHANNELS.values():
        GPIO.setup(channel, GPIO.OUT)
        print(f"Setting up GPIO pin {channel} as OUTPUT.")

# GPIO output
def gpio_output(channel, state):
    print(f"Setting GPIO pin {channel} to {'HIGH' if state else 'LOW'}.")
    GPIO.output(channel, GPIO.HIGH if state else GPIO.LOW)

def load_settings():
    if os.path.exists(settings_file):
        with open(settings_file, 'r') as file:
            settings = json.load(file)
            print("Settings file loaded.")
    else:
        settings = {}  # Provide default settings if needed
        print("Settings file not found.")
    return settings

def save_settings(settings):
    with open(settings_file, 'w') as file:
        json.dump(settings, file, indent=4)
        print("Settings file updated.")

def load_status():
    if os.path.exists(status_file):
        with open(status_file, 'r') as file:
            status = json.load(file)
            print("Status file loaded.")
    else:
        status = {}
        print("Status file not found.")
    return status

def write_status_to_file(door_states, next_sunrise, next_sunset, door_actions):
    status = {
        'door_states': door_states,
        'next_sunrise': next_sunrise.strftime('%d-%m-%Y %H:%M:%S'),
        'next_sunset': next_sunset.strftime('%d-%m-%Y %H:%M:%S'),
        'door_actions': door_actions
    }
    with open(status_file, 'w') as file:
        json.dump(status, file, indent=4, default=str)  # Convert datetime to string
        print("Status file updated.")
        print(door_states, next_sunrise, next_sunset)


