pip2 install pyinstaller
pyinstaller --onefile --distpath . --hidden-import tkinter --paths lib;plugins;controllers --name bCNC __main__.py
pause
