import streamlit as st
import os

st.title("Chicken Coop Door Control")

door1_open_time = st.number_input("Set Door 1 open time (seconds):", min_value=1, max_value=60, value=5)
door2_open_time = st.number_input("Set Door 2 open time (seconds):", min_value=1, max_value=60, value=5)
nest_open_time = st.number_input("Set Nest Box open time (seconds):", min_value=1, max_value=60, value=5)
door1_close_time = st.number_input("Set Door 1 close time (seconds):", min_value=1, max_value=60, value=5)
door2_close_time = st.number_input("Set Door 2 close time (seconds):", min_value=1, max_value=60, value=5)
nest_close_time = st.number_input("Set Nest Box close time (seconds):", min_value=1, max_value=60, value=5)
dawn_offset = st.number_input("Set Dawn offset (minutes):", min_value=-120, max_value=120, value=0)
sunset_offset = st.number_input("Set Sunset offset (minutes):", min_value=-120, max_value=120, value=0)

latitude = st.number_input("Set Latitude:", value=34.0522)
longitude = st.number_input("Set Longitude:", value=-118.2437)

if st.button("Apply Settings"):
    os.system(f"python3 door_control.py {door1_open_time} {door2_open_time} {nest_open_time} {door1_close_time} {door2_close_time} {nest_close_time} {dawn_offset} {sunset_offset}")

if st.button("Open Door 1"):
    os.system(f"python3 door_control.py open door1 {door1_open_time}")

if st.button("Close Door 1"):
    os.system(f"python3 door_control.py close door1 {door1_close_time}")

if st.button("Open Door 2"):
    os.system(f"python3 door_control.py open door2 {door2_open_time}")

if st.button("Close Door 2"):
    os.system(f"python3 door_control.py close door2 {door2_close_time}")

if st.button("Open Nest Box"):
    os.system(f"python3 door_control.py open nest {nest_open_time}")

if st.button("Close Nest Box"):
    os.system(f"python3 door_control.py close nest {nest_close_time}")

# Function to check door status (implement this function)
def door_is_open(door):
    # Implement actual door status checking logic
    return False

st.write("Door 1 is currently: ", "Open" if door_is_open(1) else "Closed")
st.write("Door 2 is currently: ", "Open" if door_is_open(2) else "Closed")
st.write("Nest Box is currently: ", "Open" if door_is_open("nest") else "Closed")

