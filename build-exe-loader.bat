pip2 install pyinstaller
pyinstaller --onefile --distpath . --hidden-import tkinter --paths bCNC --icon bCNC/bCNC.ico --name bCNC bCNC.exe
pause
