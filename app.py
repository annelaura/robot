import streamlit as st
from datetime import datetime
import json
import os

settings_file = '/home/pi/door_control_settings.json'

def load_settings():
    if os.path.exists(settings_file):
        with open(settings_file, 'r') as file:
            settings = json.load(file)
    else:
        st.error("Settings file not found.")
        settings = {}
    return settings

def display_current_status():
    settings = load_settings()
    now = datetime.now()
    st.header("Current Date and Time")
    st.write(f"**Current Time**: {now.strftime('%Y-%m-%d %H:%M:%S')}")
    
    st.header("Current Door States")
    st.write(f"**Door1**: {settings['door_states']['door1']}")
    st.write(f"**Door2**: {settings['door_states']['door2']}")
    st.write(f"**Nest**: {settings['door_states']['nest']}")
    
    st.header("Next Actions")
    st.write(f"**Sunset**: {settings['sunset']}")
    st.write(f"**Dusk**: {settings['dusk']}")
    
    for door, times in settings['next_actions'].items():
        st.write(f"**{door.capitalize()}**:")
        st.write(f"  - Open at: {times['open']}")
        st.write(f"  - Close at: {times['close']}")

def update_settings():
    settings = load_settings()
    
    st.header("Update Settings")
    
    with st.form(key='update_settings'):
        st.subheader("Door Open Times")
        for door in settings['door_open_times']:
            door_open_time = st.time_input(f"Open Time for {door.capitalize()}", value=datetime.strptime(settings['door_open_times'][door]['time'], '%H:%M').time())
            door_open_type = st.selectbox(f"Open Type for {door.capitalize()}", options=['specific', 'sunset'], index=0 if settings['door_open_times'][door]['type'] == 'specific' else 1)
            door_open_duration = st.number_input(f"Open Duration (seconds) for {door.capitalize()}", min_value=1, value=settings['door_open_times'][door]['duration'])
            settings['door_open_times'][door] = {'time': door_open_time.strftime('%H:%M'), 'type': door_open_type, 'duration': door_open_duration}
        
        st.subheader("Door Close Times")
        for door in settings['door_close_times']:
            door_close_time = st.time_input(f"Close Time for {door.capitalize()}", value=datetime.strptime(settings['door_close_times'][door]['time'], '%H:%M').time())
            door_close_type = st.selectbox(f"Close Type for {door.capitalize()}", options=['specific', 'dusk'], index=0 if settings['door_close_times'][door]['type'] == 'specific' else 1)
            door_close_duration = st.number_input(f"Close Duration (seconds) for {door.capitalize()}", min_value=1, value=settings['door_close_times'][door]['duration'])
            settings['door_close_times'][door] = {'time': door_close_time.strftime('%H:%M'), 'type': door_close_type, 'duration': door_close_duration}
        
        dawn_offset = st.number_input("Dawn Offset (minutes)", min_value=0, value=settings['dawn_offset'])
        sunset_offset = st.number_input("Sunset Offset (minutes)", min_value=0, value=settings['sunset_offset'])
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
