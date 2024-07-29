import streamlit as st
from datetime import datetime
import json
import os

status_file = '/Users/tzx804/projects/privat/FH/pi/robot/door_control_status.json'
settings_file = '/Users/tzx804/projects/privat/FH/pi/robot/door_control_settings.json'

def load_settings():
    if os.path.exists(settings_file):
        with open(settings_file, 'r') as file:
            settings = json.load(file)
    else:
        st.error("Settings file not found.")
        settings = {}
    return settings

def load_status():
    if os.path.exists(status_file):
        with open(status_file, 'r') as file:
            status = json.load(file)
    else:
        st.error("Status file not found.")
        status = {}
    return status

def display_current_status():
    status = load_status()
    now = datetime.now()
    st.header("Current Date and Time")
    st.write(f"**Current Time**: {now.strftime('%Y-%m-%d %H:%M:%S')}")
    
    st.header("Current Door States")
    door_states = status.get('door_states', {})
    st.write(f"**Door1**: {door_states.get('door1', 'Unknown')}")
    st.write(f"**Door2**: {door_states.get('door2', 'Unknown')}")
    st.write(f"**Nest**: {door_states.get('nest', 'Unknown')}")
    
    st.header("Next Actions")
    st.write(f"**Sunrise**: {status.get('sunrise', 'Unknown')}")
    st.write(f"**Dawn**: {status.get('dawn', 'Unknown')}")
    
    next_actions = status.get('next_actions', {})
    for door, times in next_actions.items():
        st.write(f"**{door.capitalize()}**:")
        st.write(f"  - Open at: {times.get('open', 'Unknown')}")
        st.write(f"  - Close at: {times.get('close', 'Unknown')}")

def update_settings():
    settings = load_settings()
    
    st.header("Update Settings")
    
    with st.form(key='update_settings'):
        st.subheader("Door Open Times")
        for door in settings.get('door_open_times', {}):
            door_open_time = st.time_input(f"Open Time for {door.capitalize()}", value=datetime.strptime(settings['door_open_times'][door]['time'], '%H:%M').time())
            door_open_type = st.selectbox(f"Open Type for {door.capitalize()}", options=['specific', 'sunrise'], index=0 if settings['door_open_times'][door]['type'] == 'specific' else 1)
            door_open_duration = st.number_input(f"Open Duration (seconds) for {door.capitalize()}", min_value=1, value=settings['door_open_times'][door]['duration'])
            settings['door_open_times'][door] = {'time': door_open_time.strftime('%H:%M'), 'type': door_open_type, 'duration': door_open_duration}
        
        st.subheader("Door Close Times")
        for door in settings.get('door_close_times', {}):
            door_close_time = st.time_input(f"Close Time for {door.capitalize()}", value=datetime.strptime(settings['door_close_times'][door]['time'], '%H:%M').time())
            door_close_type = st.selectbox(f"Close Type for {door.capitalize()}", options=['specific', 'dawn'], index=0 if settings['door_close_times'][door]['type'] == 'specific' else 1)
            door_close_duration = st.number_input(f"Close Duration (seconds) for {door.capitalize()}", min_value=1, value=settings['door_close_times'][door]['duration'])
            settings['door_close_times'][door] = {'time': door_close_time.strftime('%H:%M'), 'type': door_close_type, 'duration': door_close_duration}
        
        dawn_offset = st.number_input("Dawn Offset (minutes)", min_value=0, value=settings.get('dawn_offset', 0))
        sunset_offset = st.number_input("Sunset Offset (minutes)", min_value=0, value=settings.get('sunset_offset', 0))
        settings['dawn_offset'] = dawn_offset
        settings['sunset_offset'] = sunset_offset
        
        if st.form_submit_button("Update Settings"):
            save_settings(settings)
            st.success("Settings updated successfully!")

def save_settings(settings):
    with open(settings_file, 'w') as file:
        json.dump(settings, file, indent=4)

def main():
    display_current_status()
    update_settings()

if __name__ == "__main__":
    main()
