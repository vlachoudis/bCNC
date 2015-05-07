@echo off
set DIR=%~dp0
set PYTHONPATH=%DIR%lib;%PYTHONPATH%
start python "%DIR%bCNC.py"
