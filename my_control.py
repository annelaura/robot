import time
from datetime import datetime, timedelta
import pytz
import ephem
import json
import os
from robot_functions import *

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

if __name__ == "__main__":
    try:
        control_doors()
    except KeyboardInterrupt:
        print("Program interrupted and stopped.")
    finally:
        # Ensure GPIO cleanup if using actual hardware
        pass