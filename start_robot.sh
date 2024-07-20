#!/bin/bash

# Activate the virtual environment
source /home/annelaura/FH/robot/robot/bin/activate

# Start the door control script in the background
python /home/annelaura/FH/robot/door_control.py 50 50 50 50 50 50 0 30 55.4299 11.5428 &

# Start the Streamlit app
streamlit run /home/annelaura/FH/robot/app.py

