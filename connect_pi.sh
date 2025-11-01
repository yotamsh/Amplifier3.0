#!/bin/bash
#
# Connect to Raspberry Pi and set up development environment
#

echo "Connecting to Raspberry Pi..."
ssh -t yotam@raspberrypi.local "./AmpSync/Amp3/sync/setup_pi_env.sh"

# Available commands on Pi:
# run <script.py>        - Run src/script.py with sudo (for LED control)
# python3 <script.py>    - Run Python script normally

# Example: run main.py
# Example: run tests/debug_leds.py

# Notes:

# To shutdown the Raspberry Pi:
# sudo shutdown -h now

# To disconnect from the ssh (CTRL + D)
# exit

# to edit boot config:
# sudo nano /boot/config.txt

# adding to config:
# # enable SPI
# dtparam=spi=on
# # Disable audio since we use PWM channels for Leds (loads snd_bcm2835)
# dtparam=audio=off
# # make GPIO3 to shutdown btn
# dtoverlay=gpio-shutdown,gpio_pin=3


# on sudo nano /etc/ssh/sshd_config, add:
# PasswordAuthentication yes