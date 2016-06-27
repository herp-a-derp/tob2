#!/bin/bash

# So ubuntu continues to spectacularly fuck up their python distro, in this
# case the broke parts of pip (which is now baked into python 3.4 by default).
# see https://bugs.launchpad.net/ubuntu/+source/python3.4/+bug/1290847

# Anyways, build a venv that works.

python3 -m venv --without-pip flask
wget https://bootstrap.pypa.io/get-pip.py
./flask/bin/python3 get-pip.py
rm get-pip
./flask/bin/pip install -r requirements.txt