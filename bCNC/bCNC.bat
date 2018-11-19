@echo off
echo "###########################################"
echo "WARNING! THIS IS LEGACY MODE!"
echo "DO NOT USE THIS IF YOU ARE A BCNC DEVELOPER"
echo "GO TO REPOSITORY ROOT AND LAUNCH BCNC USING"
echo "FOLLOWING COMMAND:"
echo
echo "python2 -m bCNC"
echo "###########################################"
echo

set DIR=%~dp0
set PYTHONPATH=%DIR%lib;%DIR%plugins;%PYTHONPATH%
start python "%DIR%bCNC.py"
