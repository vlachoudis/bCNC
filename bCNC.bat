@echo off
set DIR=%~dp0
set DIR=%DIR%bCNC\
set PYTHONPATH=%DIR%lib;%DIR%plugins;%PYTHONPATH%
cd %~dp0
start python -m bCNC
