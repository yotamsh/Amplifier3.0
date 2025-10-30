#!/bin/bash
#
# Connect to Raspberry Pi and set up development environment
#

echo "Connecting to Raspberry Pi..."
ssh -t yotam@raspberrypi.local "cd /home/yotam/AmpSync/Amp3; source venv_pi/bin/activate; bash --rcfile <(echo 'PS1=\"(venv_pi) \u@\h:\w\$ \"')"

# To run the main.py file:
# sudo ./venv_pi/bin/python3 main.py

# To shutdown the Raspberry Pi:
# sudo shutdown -h now

# To disconnect from the ssh (CTRL + D)
# exit
