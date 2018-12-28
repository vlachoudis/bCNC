#!/usr/bin/env bash
set -x
set -e

MAIN_DIR=$(pwd)

pip install -e .

echo "Validating syntax"
test -L bCNC/bCNC.py
test -z $(find -name '*.pyc' -o -name '*.pyo')
python -tt -m compileall -f bCNC
python setup.py sdist

echo "Installing Test Requirements"
pip install grbl-receiver
pip install imageio==2.2.0
pip install python-xlib==0.20
pip install pytest==3.2.3
pip install requests==2.18.4
pip install pyautogui==0.9.36
