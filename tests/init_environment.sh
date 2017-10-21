#!/usr/bin/env bash
set -x
set -e

MAIN_DIR=$(pwd)

echo "Installing GRBL Simulator"
# GRBL 0.9; later versions are not supported by the simulator
git clone https://github.com/grbl/grbl.git
cd grbl/grbl
git checkout 3ce1a9d637f05e28462a36cb8b166386aab94afc

git clone https://github.com/grbl/grbl-sim.git
cd grbl-sim
git checkout ff1e887d1fd68cfa3dedc50d78ee928c8358d6ba
make new
cd $MAIN_DIR
# EEPROM data saved from manually running the simulator -- these
# settings should allow the emulator to run a ton faster than an
# actual device would be able to.
cp tests/static/EEPROM.DAT .

echo "Installing bCNC Requirements"
pip install pyserial==3.4
cp tests/travis_bcnc_config.ini ~/.bCNC

echo "Installing Test Requirements"
pip install imageio==2.2.0
pip install python-xlib==0.20
pip install pytest==3.2.3
pip install requests==2.18.4
pip install pyautogui==0.9.36
