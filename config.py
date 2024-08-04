# config.py
import pytz
import os

# Logging configuration
LOG_FILE = 'motor_door.log'
MAX_LOG_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
BACKUP_COUNT = 5

# Configuration
latitude = 55.4199
longitude = 11.5428
timezone = 'Europe/Copenhagen'
timezone_obj = pytz.timezone(timezone)

# Define GPIO pins for each door
DOOR_CHANNELS = {
    "door1_open": 27,  # GPIO27
    "door1_close": 17,  # GPIO17
    "door2_open": 10,  # GPIO10
    "door2_close": 22,  # GPIO22
    "nest_open": 9,    # GPIO9
    "nest_close": 11,  # GPIO11
}

# Define file paths for settings and status
settings_file = '/home/annelaura/FH/robot/door_control_settings.json'
status_file = '/home/annelaura/FH/robot/door_control_status.json'

