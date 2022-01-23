#!/usr/bin/python

import os
import sys

APT_PKGS = [
    "python3-tk",
    "python3-pil.imagetk",
]

# Must NOT be run as sudo
if os.getuid() == 0:
    print("ERROR: Do not run as root")
    sys.exit(1)

# Install the requirements if the system does not have it installed
# print("INFO: Checking and installing requirements")
for pkg in APT_PKGS:
    os.system(f"! dpkg -S {pkg} && sudo apt install {pkg}")

# Run pip
print("INFO: installing pip packages")
os.system("python3 -m pip install --user -r requirements.txt")
