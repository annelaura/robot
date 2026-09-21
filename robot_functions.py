import ephem
import pandas as pd
from datetime import datetime, timedelta
import pytz
import os
import json
import time
import RPi.GPIO as GPIO
from config import DOOR_CHANNELS, REMOTE_POLL_SECONDS, latitude, longitude, timezone, timezone_obj, settings_file, status_file, remote_control_file, motor_operation_file
import logging
from logging.handlers import RotatingFileHandler

# Configure logging with size-based rotation
log_handler = RotatingFileHandler(
    'motor_log.txt',       # Log file name
    maxBytes=10 * 1024 * 1024,  # Max file size in bytes (10 MB here)
    backupCount=5          # Number of backup files to keep
)
log_handler.setLevel(logging.INFO)
log_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))

logger = logging.getLogger()
logger.setLevel(logging.INFO)
logger.addHandler(log_handler)
_gpio_states = {}
_active_remote_command = None
_last_remote_command_id = None

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
            logging.info(f"Adjusted open time for {door} to {open_time}.")

        close_time = datetime.strptime(settings['door_close_times'][door]['time'], '%H:%M').time()
        if settings['door_close_times'][door]['type'] == 'daily':
            close_time = (todays_info.loc['next_sunset','DateTime']+timedelta(minutes=settings['sunset_offset'])).time()
            logging.info(f"Adjusted close time for {door} to {close_time}.")
        
        next_actions[door] = {
            'open': open_time,
            'close': close_time
        }

    #door_states = {door: "Unknown" for door in DOOR_CHANNELS.keys() if "open" in door or "close" in door}
    logging.info(f"Next actions: {next_actions}")
    write_status_to_file(door_states, next_sunrise, next_sunset)
    logging.info("Status file updated.")

def control_doors():
    logging.info('Starting robot control loop.')
    setup_gpio()
    
    try:
        while True:
            settings = load_settings()
            status = load_status()
            now = datetime.now(timezone_obj)
            remote_control = load_remote_control()

            if remote_control['mode'] == 'remote':
                run_remote_control(remote_control)
                time.sleep(REMOTE_POLL_SECONDS)
                continue
            
            update_remote_log(None)
            stop_all_motors()
            todays_info = create_dataframe(lat=latitude, lon=longitude, timezone_str=timezone)
            next_sunrise = todays_info.loc['next_sunrise','DateTime']
            next_sunset = todays_info.loc['next_sunset','DateTime']
            door_states = status.get('door_states', {})
            door_actions = status.get('door_actions', {})      
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
                # Control doors according to time and schedule
                if now.time()>door_actions['open_times'][door] and now.time()<door_actions['close_times'][door]:
                    # door should be open
                    if door_states[door] in ("closed", "unknown"):
                        logging.info(f"Opening {door}.")
                        if open_door(
                            door,
                            settings['door_open_times'][door]['duration']
                        ):
                            door_states[door] = "open"
                        else:
                            door_states[door] = "unknown"
                            break
                    else:
                        door_states[door] = "open"
                else:
                    # door should be closed
                    if door_states[door] in ("open", "unknown"):
                        logging.info(f"Closing {door}.")
                        if close_door(
                            door,
                            settings['door_close_times'][door]['duration']
                        ):
                            door_states[door] = "closed"
                        else:
                            door_states[door] = "unknown"
                            break
                    else:
                        door_states[door] = "closed"
            logging.info("Controller heartbeat")
            write_status_to_file(door_states, next_sunrise, next_sunset, door_actions)
            if load_remote_control()['mode'] == 'remote':
                continue
            time.sleep(10)  # Check every 10 seconds
    except KeyboardInterrupt:
        logging.info("Program interrupted and stopped.")
    finally:
        stop_all_motors()
        GPIO.cleanup()  # Ensure that GPIO resources are cleaned up

def load_remote_control():
    default = {
        'mode': 'automatic',
        'command_id': None,
        'door': None,
        'action': None,
        'duration': 0,
        'issued_at': 0.0
    }

    try:
        with open(remote_control_file, 'r') as file:
            control = json.load(file)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return default

    if control.get('mode') not in ('automatic', 'remote'):
        return default

    return {**default, **control}

def update_remote_log(command):
    global _active_remote_command

    if command == _active_remote_command:
        return

    action_labels = {
        'open': 'opening',
        'close': 'closing'
    }
    door_labels = {
        'door1': 'Door 1',
        'door2': 'Door 2',
        'nest': 'Nest box'
    }

    if _active_remote_command:
        old_door, old_action = _active_remote_command
        logging.info(
            f"Remote {action_labels[old_action]} stopped "
            f"for {door_labels.get(old_door, old_door)}."
        )

    if command:
        door, action = command
        logging.info(
            f"Remote {action_labels[action]} started "
            f"for {door_labels.get(door, door)}."
        )

    _active_remote_command = command

def run_remote_control(control):
    global _last_remote_command_id

    command_id = control.get('command_id')
    door = control.get('door')
    action = control.get('action')
    duration = control.get('duration', 0)
    issued_at = control.get('issued_at', 0.0)

    valid_doors = {
        key.rsplit('_', 1)[0]
        for key in DOOR_CHANNELS
    }

    command_is_valid = (
        isinstance(command_id, str)
        and bool(command_id)
        and command_id != _last_remote_command_id
        and door in valid_doors
        and action in ('open', 'close')
        and isinstance(duration, (int, float))
        and not isinstance(duration, bool)
        and 0 < duration <= 60
        and isinstance(issued_at, (int, float))
        and 0 <= time.time() - issued_at <= 2.0
    )

    if not command_is_valid:
        update_remote_log(None)
        stop_all_motors()
        return

    # Mark it before starting so the same command cannot run twice.
    _last_remote_command_id = command_id

    channel = DOOR_CHANNELS[f'{door}_{action}']
    deadline = time.monotonic() + duration
    last_seconds = None

    stop_all_motors()
    update_remote_log((door, action))
    gpio_output(channel, True)

    try:
        while time.monotonic() < deadline:
            current_control = load_remote_control()

            command_still_active = (
                current_control.get('mode') == 'remote'
                and current_control.get('command_id') == command_id
            )

            if not command_still_active:
                logging.info(
                    "Remote movement stopped by user."
                )
                return

            remaining = max(
                0,
                int(
                    deadline
                    - time.monotonic()
                    + 0.999
                )
            )

            if remaining != last_seconds:
                write_motor_operation(
                    active=True,
                    door=door,
                    action=action,
                    seconds_remaining=remaining
                )
                last_seconds = remaining

            time.sleep(REMOTE_POLL_SECONDS)

    finally:
        gpio_output(channel, False)
        update_remote_log(None)
        write_motor_operation()
        mark_door_unknown(door)

def stop_all_motors():
    for channel in DOOR_CHANNELS.values():
        gpio_output(channel, False)

def mark_door_unknown(door):
    try:
        status = load_status()
        door_states = status.get('door_states', {})

        if door not in door_states:
            logging.warning(
                f"Could not mark unknown door: {door}."
            )
            return

        door_states[door] = 'unknown'

        temporary_file = (
            f"{status_file}."
            f"{os.getpid()}.tmp"
        )

        with open(temporary_file, 'w') as file:
            json.dump(
                status,
                file,
                indent=4,
                default=str
            )
            file.flush()
            os.fsync(file.fileno())

        os.replace(temporary_file, status_file)

        logging.info(
            f"Door state set to unknown after "
            f"remote movement: {door}."
        )

    except (
        OSError,
        json.JSONDecodeError
    ):
        logging.exception(
            f"Could not update remote door state: {door}."
        )


def write_motor_operation(
    active=False,
    door=None,
    action=None,
    seconds_remaining=0
):
    operation = {
        'active': active,
        'door': door,
        'action': action,
        'seconds_remaining': seconds_remaining
    }

    temporary_file = (
        f"{motor_operation_file}."
        f"{os.getpid()}.tmp"
    )

    with open(temporary_file, 'w') as file:
        json.dump(operation, file, indent=4)
        file.flush()
        os.fsync(file.fileno())

    os.replace(
        temporary_file,
        motor_operation_file
    )


def open_door(door, duration):
    logging.info(
        f"Opening {door} for {duration} seconds."
    )
    return run_scheduled_motor(
        door,
        'open',
        duration
    )


def close_door(door, duration):
    logging.info(
        f"Closing {door} for {duration} seconds."
    )
    return run_scheduled_motor(
        door,
        'close',
        duration
    )


def run_scheduled_motor(door, action, duration):
    channel = DOOR_CHANNELS[
        f"{door}_{action}"
    ]
    deadline = time.monotonic() + duration
    last_seconds = None

    gpio_output(channel, True)

    try:
        while time.monotonic() < deadline:
            remaining = max(
                0,
                int(
                    deadline
                    - time.monotonic()
                    + 0.999
                )
            )

            if remaining != last_seconds:
                write_motor_operation(
                    active=True,
                    door=door,
                    action=action,
                    seconds_remaining=remaining
                )
                last_seconds = remaining

            if load_remote_control()['mode'] == 'remote':
                logging.info(
                    "Scheduled movement interrupted "
                    "by remote mode."
                )
                return False

            time.sleep(REMOTE_POLL_SECONDS)

        return True
    finally:
        gpio_output(channel, False)
        write_motor_operation()

# GPIO setup
def setup_gpio():
    logging.info("Setting up GPIO pins.")
    GPIO.setmode(GPIO.BCM)
    for channel in DOOR_CHANNELS.values():
        GPIO.setup(channel, GPIO.OUT, initial=GPIO.LOW)
        _gpio_states[channel] = False
        logging.info(f"Setting up GPIO pin {channel} as OUTPUT.")

# GPIO output
def gpio_output(channel, state):
    if _gpio_states.get(channel) == state:
        return

    logging.info(
        f"Setting GPIO pin {channel} to {'HIGH' if state else 'LOW'}."
    )
    GPIO.output(channel, GPIO.HIGH if state else GPIO.LOW)
    _gpio_states[channel] = state

def load_settings():
    if os.path.exists(settings_file):
        with open(settings_file, 'r') as file:
            settings = json.load(file)
    else:
        settings = {}  # Provide default settings if needed
        logging.info("Settings file not found.")
    return settings

def save_settings(settings):
    with open(settings_file, 'w') as file:
        json.dump(settings, file, indent=4)
        logging.info("Settings file updated.")

def load_status():
    if os.path.exists(status_file):
        with open(status_file, 'r') as file:
            status = json.load(file)
    else:
        status = {}
        logging.info("Status file not found.")
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


