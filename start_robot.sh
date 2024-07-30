#!/bin/bash

cd /home/annelaura/FH/robot/

# Activate the virtual environment
source robot/bin/activate

# Send IP address
python3 send_ip_on_startup.py

# Reset the status of the robot
cp start_status.json door_control_status.json

# Start the door control script in the background and write the output to a log file
nohup python3 my_control.py > motor_door.log 2>&1 &

# Start the Streamlit app
streamlit run myapp.py

