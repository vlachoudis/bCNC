from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from ToolsPage import Plugin
from tkinter import messagebox

class Tool(Plugin):
    def __init__(self, master):
        Plugin.__init__(self, master, "Oprava_G0_na_G1")
        self.icon = "cod"
        self.group = "Artistic"
        self.buttons.append("exe")

    def execute(self, app):
        try:
            modified = False
            
            # Projdeme všechny bloky
            for block in app.gcode.blocks:
                # Předpokládáme, že blok je seznam řádků
                if not isinstance(block, list):
                    continue
                    
                new_lines = []
                
                # Úprava řádků
                for line in block:
                    if not isinstance(line, str):
                        continue
                        
                    stripped = line.strip()
                    if stripped.startswith("G0") and "F" in stripped:
                        new_lines.append(line.replace("G0", "G1", 1))
                        modified = True
                    else:
                        new_lines.append(line)
                
                # Aktualizujeme blok
                if new_lines != block:
                    block[:] = new_lines  # Upravíme obsah původního bloku
            
            if modified:
                messagebox.showinfo("Hotovo", "Příkazy G0 s F byly převedeny na G1.")
            else:
                messagebox.showinfo("Info", "Nebyl nalezen žádný G0 s parametrem F.")
                
        except Exception as e:
            messagebox.showerror("Chyba", f"Došlo k chybě: {str(e)}")  
        

      


