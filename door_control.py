import RPi.GPIO as GPIO
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
settings_file = '/home/annelaura/FH/robot/door_control_settings.json'

# Define GPIO pins for each door
DOOR_CHANNELS = {
    "door1_open": 2,
    "door1_close": 3,
    "door2_open": 4,
    "door2_close": 5,
    "nest_open": 6,
    "nest_close": 7,
}

# Setup GPIO
GPIO.setmode(GPIO.BCM)
for channel in DOOR_CHANNELS.values():
    GPIO.setup(channel, GPIO.OUT)
    GPIO.output(channel, GPIO.LOW)

def load_settings():
    if os.path.exists(settings_file):
        with open(settings_file, 'r') as file:
            settings = json.load(file)
    else:
        settings = default_settings
        save_settings(settings)
    return settings

def save_settings(settings):
    with open(settings_file, 'w') as file:
        json.dump(settings, file, indent=4)

def calculate_sunset_dusk(date, latitude, longitude, timezone):
    observer = ephem.Observer()
    observer.lat = str(latitude)
    observer.lon = str(longitude)
    observer.date = date

    sunset_time = observer.next_setting(ephem.Sun()).datetime().replace(tzinfo=pytz.UTC).astimezone(timezone)
    dusk_time = observer.next_transit(ephem.Sun(), start=sunset_time).datetime().replace(tzinfo=pytz.UTC).astimezone(timezone)

    return sunset_time, dusk_time

def get_sunset_dusk_times():
    now = datetime.now(timezone_obj)
    sunset, dusk = calculate_sunset_dusk(now, latitude, longitude, timezone_obj)
    return sunset, dusk

def get_next_actions():
    settings = load_settings()
    now = datetime.now(timezone_obj)
    sunset, dusk = get_sunset_dusk_times()

    next_actions = {}
    for door in settings['door_open_times']:
        if settings['door_open_times'][door]['type'] == 'specific':
            open_time = datetime.strptime(settings['door_open_times'][door]['time'], '%H:%M').time()
        else:  # 'sunset'
            open_time = (sunset - timedelta(minutes=settings['door_open_times'][door]['offset'])).time()

        if settings['door_close_times'][door]['type'] == 'specific':
            close_time = datetime.strptime(settings['door_close_times'][door]['time'], '%H:%M').time()
        else:  # 'dusk'
            close_time = (dusk + timedelta(minutes=settings['door_close_times'][door]['offset'])).time()

        next_actions[door] = {
            'open': open_time,
            'close': close_time
        }

    return {
        'current_time': now.strftime('%Y-%m-%d %H:%M:%S'),
        'sunset': sunset.strftime('%Y-%m-%d %H:%M:%S'),
        'dusk': dusk.strftime('%Y-%m-%d %H:%M:%S'),
        'next_actions': next_actions,
        'door_states': door_states
    }

def control_doors():
    settings = load_settings()
    while True:
        now = datetime.now(timezone_obj)
        sunset, dusk = get_sunset_dusk_times()
        dawn = (sunset - timedelta(minutes=settings['dawn_offset']))

        # Perform door control based on settings
        for door in settings['door_open_times']:
            if settings['door_open_times'][door]['type'] == 'specific':
                open_time = datetime.strptime(settings['door_open_times'][door]['time'], '%H:%M').time()
                if now.time() == open_time:
                    open_door(door, settings['door_open_times'][door]['duration'])
            else:  # 'sunset'
                open_time = (sunset - timedelta(minutes=settings['door_open_times'][door]['offset'])).time()
                if now.time() == open_time:
                    open_door(door, settings['door_open_times'][door]['duration'])

        for door in settings['door_close_times']:
            if settings['door_close_times'][door]['type'] == 'specific':
                close_time = datetime.strptime(settings['door_close_times'][door]['time'], '%H:%M').time()
                if now.time() == close_time:
                    close_door(door, settings['door_close_times'][door]['duration'])
            else:  # 'dusk'
                close_time = (dusk + timedelta(minutes=settings['door_close_times'][door]['offset'])).time()
                if now.time() == close_time:
                    close_door(door, settings['door_close_times'][door]['duration'])

        time.sleep(60)  # Check every minute

def open_door(door, duration):
    print(f"Opening {door} for {duration} seconds.")
    GPIO.output(DOOR_CHANNELS[f"{door}_open"], GPIO.HIGH)
    time.sleep(duration)
    GPIO.output(DOOR_CHANNELS[f"{door}_open"], GPIO.LOW)

def close_door(door, duration):
    print(f"Closing {door} for {duration} seconds.")
    GPIO.output(DOOR_CHANNELS[f"{door}_close"], GPIO.HIGH)
    time.sleep(duration)
    GPIO.output(DOOR_CHANNELS[f"{door}_close"], GPIO.LOW)

if __name__ == "__main__":
    try:
        control_doors()
    except KeyboardInterrupt:
        print("Program interrupted and stopped.")
    finally:
        GPIO.cleanup()
