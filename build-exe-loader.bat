pip2 install pyinstaller
pip2 install --upgrade setuptools
pyinstaller --onefile --distpath . --hidden-import tkinter --paths bCNC --icon bCNC/bCNC.ico --name bCNC bCNC.py
pause
