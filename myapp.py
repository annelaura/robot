import streamlit as st
from datetime import datetime
import pytz
from robot_functions import *

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

st.header("Current Date and Time")
st.write(f"**Current Time**: {now.strftime('%H:%M:%S %d-%m-%Y')}")

st.header("Today's Sun")
next_sunrise = status.get('next_sunrise', {})
next_sunset = status.get('next_sunset', {})

st.write("**Sunrise**: {}".format(next_sunrise))
st.write("**Dusk**: {}".format(next_sunset))

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

# TODO:
# DONE: change next_civil_dusk to next_sunset + 60 minutes
# DONE add next actions
# add settings and their values
# enable change in settings
# add the possibility to open and close the doors with a button (with or without changing the status?)--> do not change status, but put a red banner in the status on the app that the status has been overwritten by the button
# add a sms service that sends sms when there is no wifi connection (or the pi gets power off)
# add output from the background process to the app (maybe save the output to a file and display it in the app)