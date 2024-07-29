import streamlit as st
from datetime import datetime
import pytz
from collections import deque
from robot_functions import *

# Create tabs
tab1, tab2, tab3 = st.tabs(["Status", "Update Settings", "Remote Control"])

#Configuration
latitude = 55.4199
longitude = 11.5428
timezone = 'Europe/Copenhagen'
timezone_obj = pytz.timezone(timezone)
now = datetime.now(timezone_obj)
today_midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)

# Status
settings_file = '/Users/tzx804/projects/privat/FH/pi/robot/door_control_settings.json'
status_file = '/Users/tzx804/projects/privat/FH/pi/robot/door_control_status.json'
status = load_status()
settings = load_settings()
log_file = '/Users/tzx804/projects/privat/FH/pi/robot/motor_door.log'

def display_warning_banner():
    remote_in_use = 0
    remote_time = settings['remote_time']
    door_states = status.get('door_states', {})
    for door in door_states:
        # Check if remote control has been pressed
        if door_states[door] in ["remote_close","remote_open"]:
            remote_in_use += 1
    if remote_in_use > 0:
        st.warning(f"Remote control is in use. Please note that changes in settings will not be effectuated before the {remote_time} minutes remote window has passed.")
            
with tab1:
    st.header("Current Date and Time")
    # display warning banner if remote is beeing used:
    display_warning_banner()  # Display the banner if needed
    st.write(f"**Current Time**: {now.strftime('%d-%m-%Y %H:%M')}")

    st.header("Today's Sun")
    st.write("Lattiude: {} and Longitude: {}".format(latitude, longitude))
    next_sunrise = status.get('next_sunrise', {})
    next_sunset = status.get('next_sunset', {})
    st.write("**Sunrise**: {}".format(next_sunrise.split(' ')[1][:5]))
    st.write("**Sunset**: {}".format(next_sunset.split(' ')[1][:5]))


    st.header("Door status")
    door_states = status.get('door_states', {})
    for door in door_states:
        st.write(f"**{door.capitalize()}**: {door_states[door]}")

    st.header("Door actions")
    door_actions = status.get('door_actions', {})
    for action in door_actions:
        st.write(f"**{action.capitalize()}**:") 
        bullet_points = "\n".join([f"- {key}: {value}" for key, value in door_actions[action].items()])
        st.write(bullet_points)

    st.header('Motor Door Program Log')
    def read_last_lines(file_path, num_lines):
        with open(file_path, 'r') as file:
            lines = deque(file, num_lines)
        return ''.join(lines)

    log_placeholder = st.empty()

    def display_log_content():
        log_content = read_last_lines(log_file, 20)
        log_placeholder.code(log_content, language='bash')

    display_log_content()

with tab2:
    st.header("Update Settings")
    display_warning_banner()  # Display the banner if needed
    show_sunrise_offset = False
    show_sunset_offset = False

    with st.form(key='update_settings'):
        st.subheader("Door Open Times")
        for door in settings.get('door_open_times', {}):
            st.write(f"**{door.capitalize()}**")
            door_open_type = st.selectbox(f"Open Type for {door.capitalize()}", options=['specific', 'daily'], index=0 if settings['door_open_times'][door]['type'] == 'specific' else 1)
            if door_open_type == 'specific':
                door_open_time = st.time_input(f"Open Time for {door.capitalize()}", value=datetime.strptime(settings['door_open_times'][door]['time'], '%H:%M').time())
                settings['door_open_times'][door]['time'] = door_open_time.strftime('%H:%M')
            else:
                show_sunrise_offset = True
            door_open_duration = st.number_input(f"Open Duration (seconds) for {door.capitalize()}", min_value=1, value=settings['door_open_times'][door]['duration'])
            settings['door_open_times'][door] = {'type': door_open_type, 'time': settings['door_open_times'][door].get('time', '00:00'), 'duration': door_open_duration}
        if show_sunrise_offset:
            st.write("**Sunrise Offset**")
            sunrise_offset = st.number_input("Minutes before sunrise:", min_value=0, value=settings.get('sunrise_offset', 0))
            settings['sunrise_offset'] = sunrise_offset

        st.subheader("Door Close Times")
        for door in settings.get('door_close_times', {}):
            st.write(f"**{door.capitalize()}**")
            door_close_type = st.selectbox(f"Close Type for {door.capitalize()}", options=['specific', 'daily'], index=0 if settings['door_close_times'][door]['type'] == 'specific' else 1)
            if door_close_type == 'specific':
                door_close_time = st.time_input(f"Close Time for {door.capitalize()}", value=datetime.strptime(settings['door_close_times'][door]['time'], '%H:%M').time())
                settings['door_close_times'][door]['time'] = door_close_time.strftime('%H:%M')
            else:
                show_sunset_offset = True
            door_close_duration = st.number_input(f"Close Duration (seconds) for {door.capitalize()}", min_value=1, value=settings['door_close_times'][door]['duration'])
            settings['door_close_times'][door] = {'type': door_close_type, 'time': settings['door_close_times'][door].get('time', '00:00'), 'duration': door_close_duration}
        if show_sunset_offset:
            st.write("**Sunset Offset**")
            sunset_offset = st.number_input("Minutes after sunset:", min_value=0, value=settings.get('sunset_offset', 0))
            settings['sunset_offset'] = sunset_offset

        st.subheader("Remote Time")
        remote_time = st.number_input("Remote Time (minutes):", min_value=1, value=settings.get('remote_time', 5))
        settings['remote_time'] = remote_time
        
        if st.form_submit_button("Update Settings"):
            save_settings(settings)
            st.success("Settings updated successfully!")

def control_door(door, action):
    # Simulate sending command to open/close the door
    st.write(f"{action.capitalize()} command sent to {door.capitalize()}.")
    # Update status file to reflect the action
    status['door_states'][door] = action
    with open(status_file, 'w') as file:
        json.dump(status, file, indent=4)
    remote_time = settings['remote_time']
    st.success(f"{door.capitalize()} {action} will last the next {remote_time} minutes and then return to schedule.")

with tab3:
    st.header("Remote Control")
    st.write("Use the buttons below to manually control the doors.")
    for door in status['door_states']:
        st.markdown(f"**{door.capitalize()}**")
        col1, col2 = st.columns(2)
        with col1:
            if st.button(f"Open {door.capitalize()}", key=f'open_{door}'):
                control_door(door, "remote_open")
        with col2:
            if st.button(f"Close {door.capitalize()}", key=f'close_{door}'):
                control_door(door, "remote_close")

# Auto-refresh the page every minute
time.sleep(60)
st.rerun()



# TODO:

# add output from the background process to the app (maybe save the output to a file and display it in the app): add "nohup python3 motor_door.py > motor_door.log 2>&1 &" to .sh file
# remember to add a clean status file upon pi restart

# get "fast ip" with TDC - ask for 2 sim? and move privete phones to TDC
# order pi stuff
