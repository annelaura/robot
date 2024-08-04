#!/bin/bash

cd /home/annelaura/FH/robot/

# Activate the virtual environment
source robot/bin/activate

# Reset the status of the robot
cp start_status.json door_control_status.json

# Start the Streamlit app
streamlit run myapp.py
