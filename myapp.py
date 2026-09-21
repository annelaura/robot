import json
import os
import re
import time
import uuid
from collections import deque
from datetime import datetime

import pytz
import streamlit as st

from config import remote_control_file, motor_operation_file
from robot_functions import *


# Configuration

latitude = 55.4199
longitude = 11.5428
timezone = 'Europe/Copenhagen'
timezone_obj = pytz.timezone(timezone)

settings_file = (
    '/home/annelaura/FH/robot/'
    'door_control_settings.json'
)
status_file = (
    '/home/annelaura/FH/robot/'
    'door_control_status.json'
)
log_file = (
    '/home/annelaura/FH/robot/'
    'motor_door.log'
)


def load_motor_operation():
    default = {
        'active': False,
        'door': None,
        'action': None,
        'seconds_remaining': 0
    }

    try:
        with open(motor_operation_file, 'r') as file:
            operation = json.load(file)
    except (
        FileNotFoundError,
        json.JSONDecodeError,
        OSError
    ):
        return default

    if not isinstance(operation, dict):
        return default

    return {**default, **operation}


def save_remote_control(
    mode,
    command_id=None,
    door=None,
    action=None,
    duration=0,
    issued_at=0.0
):
    control = {
        'mode': mode,
        'command_id': command_id,
        'door': door,
        'action': action,
        'duration': duration,
        'issued_at': issued_at
    }

    temporary_file = (
        f"{remote_control_file}."
        f"{os.getpid()}."
        f"{uuid.uuid4().hex}.tmp"
    )

    with open(temporary_file, 'w') as file:
        json.dump(control, file, indent=4)
        file.flush()
        os.fsync(file.fileno())

    os.replace(temporary_file, remote_control_file)


def load_remote_mode():
    return load_remote_control().get(
        'mode',
        'automatic'
    )

def change_remote_mode():
    remote_enabled = st.session_state.get(
        'remote_mode_toggle',
        False
    )

    save_remote_control(
        'remote'
        if remote_enabled
        else 'automatic'
    )


def send_remote_command(door, action, duration):
    if not isinstance(duration, int):
        return

    if not 1 <= duration <= 60:
        return

    save_remote_control(
        mode='remote',
        command_id=uuid.uuid4().hex,
        door=door,
        action=action,
        duration=duration,
        issued_at=time.time()
    )


def stop_remote_motor():
    save_remote_control(mode='remote')


def get_app_lock_state():
    remote = load_remote_control()
    operation = load_motor_operation()

    if remote.get('mode') == 'remote':
        return 'remote', operation

    if operation.get('active'):
        return 'automatic_operation', operation

    return None, None


def operation_description(operation):
    door_labels = {
        'door1': 'Door 1',
        'door2': 'Door 2',
        'nest': 'Nest box'
    }
    action_labels = {
        'open': 'Opening',
        'close': 'Closing'
    }

    door = door_labels.get(
        operation.get('door'),
        str(operation.get('door')).capitalize()
    )
    action = action_labels.get(
        operation.get('action'),
        'Operating'
    )
    seconds = operation.get(
        'seconds_remaining',
        0
    )

    return (
        f"{action} {door} — "
        f"{seconds} seconds remaining"
    )


def display_global_status():
    lock_type, operation = get_app_lock_state()

    if lock_type == 'remote':
        st.warning(
            "Remote control is active. "
            "Other functions are temporarily unavailable."
        )

        if operation and operation.get('active'):
            st.info(operation_description(operation))

    elif lock_type == 'automatic_operation':
        st.info(operation_description(operation))


app_lock_type, app_operation = get_app_lock_state()
display_global_status()


# Create tabs

tab1, tab2, tab3, tab4 = st.tabs(
    [
        "Status",
        "Update Settings",
        "Remote Control",
        "Live streaming"
    ]
)


status = load_status()
settings = load_settings()


@st.fragment(run_every="1s")
def display_live_status():
    lock_type, operation = get_app_lock_state()

    if lock_type == 'remote':
        st.info(
            "This view is unavailable while Remote control "
            "is active. Switch back to Automatic schedule "
            "to unlock it."
        )
        return

    if lock_type == 'automatic_operation':
        st.info(
            "This view is unavailable while the automatic "
            "controller is moving a door. It will unlock "
            "when the movement is complete."
        )
        return

    live_status = load_status()
    live_now = datetime.now(timezone_obj)
    door_states = live_status.get('door_states', {})

    st.header("Current Date and Time")
    st.write(
        "**Current Time**: "
        f"{live_now.strftime('%d-%m-%Y %H:%M:%S')}"
    )

    st.header("Today's Sun")
    st.write(
        f"Latitude: {latitude} and Longitude: {longitude}"
    )

    next_sunrise = live_status.get('next_sunrise', '')
    next_sunset = live_status.get('next_sunset', '')

    if next_sunrise:
        st.write(
            f"**Sunrise**: "
            f"{next_sunrise.split(' ')[1][:5]}"
        )

    if next_sunset:
        st.write(
            f"**Sunset**: "
            f"{next_sunset.split(' ')[1][:5]}"
        )

    st.header("Door status")

    for door, door_state in door_states.items():
        st.write(
            f"**{door.capitalize()}**: {door_state}"
        )

    st.header("Door actions")
    door_actions = live_status.get(
        'door_actions',
        {}
    )

    for action, actions in door_actions.items():
        st.write(f"**{action.capitalize()}**:")
        bullet_points = "\n".join(
            [
                f"- {key}: {value}"
                for key, value in actions.items()
            ]
        )
        st.write(bullet_points)

    st.header("Motor Door Program Log")

    try:
        with open(log_file, 'r') as file:
            lines = deque(file, 20)
    except OSError:
        lines = []

    log_content = ''.join(reversed(lines))
    log_content = re.sub(
        (
            r'^(\d{4})-(\d{2})-(\d{2}) '
            r'(\d{2}:\d{2}:\d{2}),\d{3} '
            r'- [A-Z]+ - '
        ),
        r'\3-\2 \4  ',
        log_content,
        flags=re.MULTILINE
    )
    st.code(log_content, language='bash')


with tab1:
    display_live_status()

with tab2:
    if app_lock_type == 'remote':
        st.info(
            "Settings are unavailable while Remote control "
            "is active. Switch back to Automatic schedule "
            "to unlock them."
        )
    elif app_lock_type == 'automatic_operation':
        st.info(
            "Settings are unavailable while the automatic "
            "controller is moving a door. They will unlock "
            "when the movement is complete."
        )
    else:
        st.header("Update Settings")
        show_sunrise_offset = False
        show_sunset_offset = False

        with st.form(key='update_settings'):
            st.subheader("Door Open Times")

            for door in settings.get(
                'door_open_times',
                {}
            ):
                st.write(f"**{door.capitalize()}**")

                current_open = (
                    settings['door_open_times'][door]
                )

                door_open_type = st.selectbox(
                    (
                        "Open Type for "
                        f"{door.capitalize()}"
                    ),
                    options=['specific', 'daily'],
                    index=(
                        0
                        if current_open['type']
                        == 'specific'
                        else 1
                    )
                )

                if door_open_type == 'specific':
                    door_open_time = st.time_input(
                        (
                            "Open Time for "
                            f"{door.capitalize()}"
                        ),
                        value=datetime.strptime(
                            current_open['time'],
                            '%H:%M'
                        ).time()
                    )
                    current_open['time'] = (
                        door_open_time.strftime('%H:%M')
                    )
                else:
                    show_sunrise_offset = True

                door_open_duration = st.number_input(
                    (
                        "Open Duration (seconds) for "
                        f"{door.capitalize()}"
                    ),
                    min_value=1,
                    value=current_open['duration']
                )

                settings['door_open_times'][door] = {
                    'type': door_open_type,
                    'time': current_open.get(
                        'time',
                        '00:00'
                    ),
                    'duration': door_open_duration
                }

            if show_sunrise_offset:
                st.write("**Sunrise Offset**")
                settings['sunrise_offset'] = (
                    st.number_input(
                        "Minutes before sunrise:",
                        min_value=0,
                        value=settings.get(
                            'sunrise_offset',
                            0
                        )
                    )
                )

            st.subheader("Door Close Times")

            for door in settings.get(
                'door_close_times',
                {}
            ):
                st.write(f"**{door.capitalize()}**")

                current_close = (
                    settings['door_close_times'][door]
                )

                door_close_type = st.selectbox(
                    (
                        "Close Type for "
                        f"{door.capitalize()}"
                    ),
                    options=['specific', 'daily'],
                    index=(
                        0
                        if current_close['type']
                        == 'specific'
                        else 1
                    )
                )

                if door_close_type == 'specific':
                    door_close_time = st.time_input(
                        (
                            "Close Time for "
                            f"{door.capitalize()}"
                        ),
                        value=datetime.strptime(
                            current_close['time'],
                            '%H:%M'
                        ).time()
                    )
                    current_close['time'] = (
                        door_close_time.strftime('%H:%M')
                    )
                else:
                    show_sunset_offset = True

                door_close_duration = st.number_input(
                    (
                        "Close Duration (seconds) for "
                        f"{door.capitalize()}"
                    ),
                    min_value=1,
                    value=current_close['duration']
                )

                settings['door_close_times'][door] = {
                    'type': door_close_type,
                    'time': current_close.get(
                        'time',
                        '00:00'
                    ),
                    'duration': door_close_duration
                }

            if show_sunset_offset:
                st.write("**Sunset Offset**")
                settings['sunset_offset'] = (
                    st.number_input(
                        "Minutes after sunset:",
                        min_value=0,
                        value=settings.get(
                            'sunset_offset',
                            0
                        )
                    )
                )

            if st.form_submit_button("Update Settings"):
                save_settings(settings)
                st.success(
                    "Settings updated successfully!"
                )


@st.fragment
def display_remote_control():
    st.header("Remote Control")

    if app_lock_type == 'automatic_operation':
        st.info(
            "Remote control is unavailable while the "
            "automatic controller is moving a door. "
            "It will unlock when the movement is complete."
        )
        return

    current_mode = load_remote_mode()

    left, toggle_column, right = st.columns(
        [2, 1, 2]
    )

    with left:
        st.markdown("**Automatic schedule**")

    with toggle_column:
        remote_enabled = st.toggle(
            "Control mode",
            value=current_mode == 'remote',
            key='remote_mode_toggle',
            on_change=change_remote_mode,
            label_visibility="collapsed"
        )

    with right:
        st.markdown("**Remote control**")

    selected_mode = load_remote_mode()

    if selected_mode == 'automatic':
        st.info(
            "The robot is following its automatic schedule."
        )
        return

    st.warning(
        "Automatic schedule is paused. Select a duration "
        "and press Open or Close. The motor stops "
        "automatically when the selected time has elapsed."
    )

    operation = load_motor_operation()
    if operation.get('active'):
        st.info(operation_description(operation))

    if st.button(
        "Stop motor",
        key="stop_remote_motor",
        type="primary",
        use_container_width=True
    ):
        stop_remote_motor()
        st.success("Stop command sent.")

    door_labels = {
        'door1': 'Door 1',
        'door2': 'Door 2',
        'nest': 'Nest box'
    }

    for door in load_status().get(
        'door_states',
        {}
    ):
        door_label = door_labels.get(
            door,
            door.capitalize()
        )

        st.markdown(f"### {door_label}")

        duration = st.slider(
            f"Movement duration for {door_label}",
            min_value=0,
            max_value=60,
            value=20,
            step=1,
            key=f"duration_{door}"
        )

        st.caption(
            f"Selected duration: {duration} seconds"
        )

        open_column, close_column = st.columns(2)

        with open_column:
            if st.button(
                "Open",
                key=f"open_{door}",
                disabled=duration == 0,
                use_container_width=True
            ):
                send_remote_command(
                    door,
                    'open',
                    duration
                )

        with close_column:
            if st.button(
                "Close",
                key=f"close_{door}",
                disabled=duration == 0,
                use_container_width=True
            ):
                send_remote_command(
                    door,
                    'close',
                    duration
                )


with tab3:
    display_remote_control()


with tab4:
    if app_lock_type == 'remote':
        st.info(
            "Live streaming is unavailable while Remote "
            "control is active. Switch back to Automatic "
            "schedule to unlock it."
        )
    elif app_lock_type == 'automatic_operation':
        st.info(
            "Live streaming is unavailable while the "
            "automatic controller is moving a door. "
            "It will unlock when the movement is complete."
        )
    else:
        st.header(
            "Live streaming from chicken coop"
        )
