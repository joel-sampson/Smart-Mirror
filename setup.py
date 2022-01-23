#!/usr/bin/python

import os
import sys

# Must be ran as root or as sudo
if os.getuid() == 0:
    print("ERROR: Do not run as root")
    sys.exit(1)

# Install the requirements if the system does not have it installed
# print("INFO: Checking and installing requirements")
os.system("! dpkg -S python3-tk python3-pil.imagetk && sudo apt install python3-tk python3-pil.imagetk")

# Generate the requirements from the file for old instructions
print("INFO: Generating the requirements from requirements.txt")
packages = []
for line in open("requirements.txt", "r"):
    if not line.startswith("#"):
        packages.append(line.strip())

# Run pip
print("INFO: installing pip packages")
os.system("python3 -m pip install --user -r requirements.txt")
