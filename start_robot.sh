#!/bin/bash

cd /home/annelaura/FH/robot/

# Activate the virtual environment
source robot/bin/activate

# Start the door control script in the background and write the output to a log file
nohup python3 my_control.py > motor_door.log 2>&1 &

# Start the Streamlit app
streamlit run myapp.py

