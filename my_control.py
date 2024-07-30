from robot_functions import *
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

# Define GPIO pins for each door (for simulation purposes)
DOOR_CHANNELS = {
    "door1_open": 2,
    "door1_close": 3,
    "door2_open": 4,
    "door2_close": 5,
    "nest_open": 6,
    "nest_close": 7,
}

if __name__ == "__main__":
    try:
        control_doors()
    except KeyboardInterrupt:
        print("Program interrupted and stopped.")
    finally:
        GPIO.cleanup()