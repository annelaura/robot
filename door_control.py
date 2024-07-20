import RPi.GPIO as GPIO
import time
from datetime import datetime, timedelta
from astral import LocationInfo
from astral.sun import sun
import pytz
import sys

# GPIO setup
GPIO.setmode(GPIO.BCM)
DOOR_CHANNELS = {
    "door1_open": 2,
    "door1_close": 3,
    "door2_open": 4,
    "door2_close": 5,
    "nest_open": 6,
    "nest_close": 7,
}

for channel in DOOR_CHANNELS.values():
    GPIO.setup(channel, GPIO.OUT)
    GPIO.output(channel, GPIO.LOW)

# Set your location using latitude and longitude
latitude = 55.4199  # Your latitude
longitude = 11.5428  # Your longitude
city = LocationInfo(latitude=latitude, longitude=longitude)

# Timezone setup
local_tz = pytz.timezone('Europe/Copenhagen')

# Function to calculate sunset and dawn
def get_sun_times():
    # Get current date in local timezone
    now = datetime.now(local_tz)
    s = sun(city.observer, date=now.date())
    dawn = local_tz.localize(s['dawn'])  # Ensure dawn is timezone-aware
    sunset = local_tz.localize(s['sunset'])  # Ensure sunset is timezone-aware
    return dawn, sunset

def open_door(door, open_time):
    GPIO.output(DOOR_CHANNELS[f"{door}_open"], GPIO.HIGH)
    time.sleep(open_time)
    GPIO.output(DOOR_CHANNELS[f"{door}_open"], GPIO.LOW)

def close_door(door, close_time):
    GPIO.output(DOOR_CHANNELS[f"{door}_close"], GPIO.HIGH)
    time.sleep(close_time)
    GPIO.output(DOOR_CHANNELS[f"{door}_close"], GPIO.LOW)

def check_time_and_control_doors(door_open_times, door_close_times, dawn_offset, sunset_offset):
    while True:
        now = datetime.now(local_tz)  # Ensure now is timezone-aware
        dawn, sunset = get_sun_times()
        dawn += timedelta(minutes=dawn_offset)
        sunset -= timedelta(minutes=sunset_offset)

        # Perform the door control operations based on local time
        if dawn <= now < dawn + timedelta(minutes=1):
            open_door("door1", door_open_times['door1'])
            open_door("door2", door_open_times['door2'])
        elif sunset <= now < sunset + timedelta(minutes=1):
            close_door("door1", door_close_times['door1'])
            close_door("door2", door_close_times['door2'])

        current_time = now.strftime("%H:%M")
        if current_time == "02:00":
            open_door("nest", door_open_times['nest'])
        elif current_time == "16:00":
            close_door("nest", door_close_times['nest'])

        time.sleep(60)  # Check every minute

if __name__ == "__main__":
    door_open_times = {
        'door1': 5,  # Default value in seconds
        'door2': 5,
        'nest': 5
    }
    door_close_times = {
        'door1': 5,  # Default value in seconds
        'door2': 5,
        'nest': 5
    }
    dawn_offset = 0  # Default dawn offset in minutes
    sunset_offset = 0  # Default sunset offset in minutes

    if len(sys.argv) > 1:
        door_open_times['door1'] = int(sys.argv[1])
        door_open_times['door2'] = int(sys.argv[2])
        door_open_times['nest'] = int(sys.argv[3])
        door_close_times['door1'] = int(sys.argv[4])
        door_close_times['door2'] = int(sys.argv[5])
        door_close_times['nest'] = int(sys.argv[6])
        dawn_offset = int(sys.argv[7])
        sunset_offset = int(sys.argv[8])

    try:
        check_time_and_control_doors(door_open_times, door_close_times, dawn_offset, sunset_offset)
    except KeyboardInterrupt:
        GPIO.cleanup()

