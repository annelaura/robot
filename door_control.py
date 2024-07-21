import time
from datetime import datetime, timedelta
import pytz
import ephem
import json
import os

# Configuration
latitude = 55.4199
longitude = 11.5428
timezone = 'Europe/Copenhagen'
timezone_obj = pytz.timezone(timezone)
settings_file = '/Users/tzx804/projects/privat/FH/pi/robot/door_control_settings.json'
status_file = '/Users/tzx804/projects/privat/FH/pi/robot/door_control_status.json'

# Define GPIO pins for each door (for simulation purposes)
DOOR_CHANNELS = {
    "door1_open": 2,
    "door1_close": 3,
    "door2_open": 4,
    "door2_close": 5,
    "nest_open": 6,
    "nest_close": 7,
}

# Simulate GPIO setup
def setup_gpio():
    print("GPIO setup simulated.")
    for channel in DOOR_CHANNELS.values():
        print(f"Setting up GPIO pin {channel} as OUTPUT.")

# Simulate GPIO output
def gpio_output(channel, state):
    print(f"Setting GPIO pin {channel} to {'HIGH' if state else 'LOW'}.")

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

def write_status_to_file(door_states, next_actions, sunrise, dawn):
    status = {
        'door_states': door_states,
        'next_actions': next_actions,
        'sunrise': sunrise.strftime('%Y-%m-%d %H:%M:%S'),
        'dawn': dawn.strftime('%Y-%m-%d %H:%M:%S')
    }
    with open(status_file, 'w') as file:
        json.dump(status, file, indent=4, default=str)  # Convert datetime to string
        print("Status file updated.")

def calculate_sunrise_dawn(date, latitude, longitude, timezone):
    observer = ephem.Observer()
    observer.lat = str(latitude)
    observer.lon = str(longitude)
    observer.date = date

    sunrise_time = observer.next_rising(ephem.Sun()).datetime().replace(tzinfo=pytz.UTC).astimezone(timezone)
    dawn_time = observer.next_rising(ephem.Sun(), start=sunrise_time).datetime().replace(tzinfo=pytz.UTC).astimezone(timezone)

    print(f"Sunrise: {sunrise_time}")
    print(f"Dawn: {dawn_time}")
    
    return sunrise_time, dawn_time

def get_sunrise_dawn_times():
    now = datetime.now(timezone_obj)
    sunrise, dawn = calculate_sunrise_dawn(now, latitude, longitude, timezone_obj)
    return sunrise, dawn

def get_next_actions():
    settings = load_settings()
    now = datetime.now(timezone_obj)
    sunrise, dawn = get_sunrise_dawn_times()

    next_actions = {}
    for door in settings.get('door_open_times', {}):
        open_time = datetime.strptime(settings['door_open_times'][door]['time'], '%H:%M').time()
        if settings['door_open_times'][door]['type'] == 'sunrise':
            open_time = (sunrise - timedelta(minutes=settings['sunrise_offset'])).time()
            print(f"Adjusted open time for {door} to {open_time}.")

        close_time = datetime.strptime(settings['door_close_times'][door]['time'], '%H:%M').time()
        print(f"Adjusted close time for {door} to {close_time}.")

        if settings['door_close_times'][door]['type'] == 'dawn':
            close_time = (dawn + timedelta(minutes=settings['dawn_offset'])).time()
            print(f"Adjusted close time for {door} to {close_time}.")
        
        next_actions[door] = {
            'open': open_time,
            'close': close_time
        }

    door_states = {door: "Unknown" for door in DOOR_CHANNELS.keys() if "open" in door or "close" in door}
    print(f"Next actions: {next_actions}")
    write_status_to_file(door_states, next_actions, sunrise, dawn)
    print("Status file updated.")

def control_doors():
    settings = load_settings()
    while True:
        now = datetime.now(timezone_obj)
        sunrise, dawn = get_sunrise_dawn_times()

        # Perform door control based on settings
        for door in settings.get('door_open_times', {}):
            open_time = datetime.strptime(settings['door_open_times'][door]['time'], '%H:%M').time()
            if settings['door_open_times'][door]['type'] == 'sunrise':
                open_time = (sunrise - timedelta(minutes=settings['sunrise_offset'])).time()
            if now.time() == open_time:
                open_door(door, settings['door_open_times'][door]['duration'])

        for door in settings.get('door_close_times', {}):
            close_time = datetime.strptime(settings['door_close_times'][door]['time'], '%H:%M').time()
            if settings['door_close_times'][door]['type'] == 'dawn':
                close_time = (dawn + timedelta(minutes=settings['dawn_offset'])).time()
            if now.time() == close_time:
                close_door(door, settings['door_close_times'][door]['duration'])
        print(f"Current time: {now}")
        time.sleep(60)  # Check every minute

def open_door(door, duration):
    print(f"Opening {door} for {duration} seconds.")
    gpio_output(DOOR_CHANNELS[f"{door}_open"], True)
    time.sleep(duration)
    gpio_output(DOOR_CHANNELS[f"{door}_open"], False)

def close_door(door, duration):
    print(f"Closing {door} for {duration} seconds.")
    gpio_output(DOOR_CHANNELS[f"{door}_close"], True)
    time.sleep(duration)
    gpio_output(DOOR_CHANNELS[f"{door}_close"], False)

if __name__ == "__main__":
    try:
        control_doors()
    except KeyboardInterrupt:
        print("Program interrupted and stopped.")
    finally:
        # Ensure GPIO cleanup if using actual hardware
        pass
