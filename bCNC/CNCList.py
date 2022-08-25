# $Id: CNCEditor.py,v 1.9 2014/10/15 15:04:38 bnv Exp $
#
# Author:       vvlachoudis@gmail.com
# Date: 24-Aug-2014

import json
import re
from tkinter import (
    TclError,
    END,
    ACTIVE,
    Listbox,
)
import tkinter.font as tkfont

import tkExtra
from CNC import CNC, Block

BLOCK_COLOR = "LightYellow"
COMMENT_COLOR = "Blue"
DISABLE_COLOR = "Gray"

MAXINT = 1000000000  # python3 doesn't have maxint


# =============================================================================
# CNC Listbox
# =============================================================================
class CNCListbox(Listbox):
    def __init__(self, master, app, *kw, **kwargs):
        Listbox.__init__(self, master, *kw, **kwargs)
        self.bind("<Button-1>", self.button1)
        self.bind("<ButtonRelease-1>", self.release1)
        self.bind("<Double-1>", self.double)
        self.bind("<Return>", self.edit)
        self.bind("<KP_Enter>", self.edit)
        self.bind("<Insert>", self.insertItem)
        self.bind("<Control-Key-Return>", self.insertItem)
        self.bind("<Control-Key-space>", self.commandFocus)
        self.bind("<Left>", self.toggleKey)
        self.bind("<Right>", self.toggleKey)
        self.bind("<Control-Key-d>", self.clone)
        self.bind("<Control-Key-Up>", self.orderUp)
        self.bind("<Control-Key-Prior>", self.orderUp)
        self.bind("<Control-Key-Down>", self.orderDown)
        self.bind("<Control-Key-Next>", self.orderDown)
        self.bind("<Control-Key-p>", lambda e: "break")
        self.bind("<Control-Key-n>", lambda e: "break")
        self.bind("<Control-Key-D>", self.dump)
        self.bind("<Delete>", self.deleteBlock)
        self.bind("<BackSpace>", self.deleteBlock)
        try:
            self.bind("<KP_Delete>", self.deleteBlock)
        except Exception:
            pass

        self.bind("<Control-Key-b>", self.insertBlock)
        self.bind("<Control-Key-r>", self.fill)

        self._blockPos = []  # listbox position of each block
        self._items = []  # each listbox lien which item (bid,lid) shows
        self.app = app
        self.gcode = app.gcode
        self.font = tkfont.nametofont(self.cget("font"))
        self._ystart = 0
        self._double = False  # double clicked handled
        self._hadfocus = False
        self.filter = None

    # ----------------------------------------------------------------------
    def commandFocus(self, event=None):
        self.app.commandFocus(event)
        return "break"

    # ----------------------------------------------------------------------
    # Change the value of a list item
    # and return the value of the old one
    # ----------------------------------------------------------------------
    def set(self, index, value):
        """Set/Change the value of a list item"""
        try:
            sel = self.selection_includes(index)
            act = self.index(ACTIVE)
            self.delete(index)
        except TclError:
            return
        self.insert(index, value)
        if sel:
            self.selection_set(index)
        self.activate(act)

    # ----------------------------------------------------------------------
    # Fill listbox with enable items
    # ----------------------------------------------------------------------
    def fill(self, event=None):
        ypos = self.yview()[0]
        act = self.index(ACTIVE)

        items = self.getSelection()
        self.delete(0, END)

        del self._blockPos[:]
        del self._items[:]
        y = 0
        for bi, block in enumerate(self.gcode.blocks):
            if self.filter is not None:
                if not (
                    self.filter in block.name()
                    or self.filter == "enable"
                    and block.enable
                    or self.filter == "disable"
                    and not block.enable
                ):
                    self._blockPos.append(None)
                    continue

            self._blockPos.append(y)
            self.insert(END, block.header())
            self._items.append((bi, None))
            self.itemconfig(END, background=BLOCK_COLOR)
            y += 1
            if not block.enable:
                self.itemconfig(END, foreground=DISABLE_COLOR)
            if not block.expand:
                continue

            for lj, line in enumerate(block):
                self.insert(END, line)
                y += 1
                if line and line[0] in ("(", "%"):
                    self.itemconfig(END, foreground=COMMENT_COLOR)
                self._items.append((bi, lj))

        self.select(items)
        self.yview_moveto(ypos)
        self.activate(act)
        self.see(act)

    # ----------------------------------------------------------------------
    # Copy selected items to clipboard
    # ----------------------------------------------------------------------
    def copy(self, event=None):
        jsonobj = []
        for block, line in self.getCleanSelection():
            if line is None:
                jsonobj.append(self.gcode.blocks[block].dump())
            else:
                jsonobj.append(self.gcode.blocks[block][line])
        self.clipboard_clear()
        jsonstring = json.dumps(jsonobj)
        self.clipboard_append(jsonstring)
        return "break"

    # ----------------------------------------------------------------------
    def cut(self, event=None):
        self.copy()
        self.deleteBlock()
        return "break"

    # ----------------------------------------------------------------------
    def paste(self, event=None):
        try:
            clipboard = self.selection_get(selection="CLIPBOARD")
        except Exception:
            return

        ypos = self.yview()[0]
        # paste them after the last selected item
        # bid,lid push them to self so it can be accessed from addLines()
        # python3 might fix this with the inner scope
        try:
            self._bid, self._lid = self._items[self.curselection()[-1]]
        except Exception:
            try:
                self._bid, self._lid = self._items[-1]
            except Exception:
                self._bid = 0
                self._lid = None

        selitems = []
        undoinfo = []

        def addLines(lines):
            for line in lines.splitlines():
                # Create a new block
                if self._lid is None:
                    self._bid += 1
                    if self._bid > len(self.gcode.blocks):
                        self._bid = len(self.gcode.blocks)
                    self._lid = MAXINT
                    block = Block()
                    undoinfo.append(self.gcode.addBlockUndo(self._bid, block))
                    selitems.append((self._bid, None))
                else:
                    block = self.gcode.blocks[self._bid]

                if self._lid == MAXINT:
                    self._lid = len(block)
                    selitems.append((self._bid, len(block)))
                else:
                    self._lid += 1
                    selitems.append((self._bid, self._lid))
                undoinfo.append(
                    self.gcode.insLineUndo(self._bid, self._lid, line))

        try:
            objs = json.loads(clipboard)
        except Exception:
            objs = [clipboard]
        for obj in objs:
            if isinstance(obj, list):
                obj = tuple(obj)
            if isinstance(obj, tuple):
                block = Block.load(obj)
                self._bid += 1
                undoinfo.append(self.gcode.addBlockUndo(self._bid, block))
                selitems.append((self._bid, None))
                self._lid = None
            else:
                addLines(obj)
        if not undoinfo:
            return

        self.gcode.addUndo(undoinfo)

        self.selection_clear(0, END)
        self.fill()
        self.yview_moveto(ypos)
        self.select(selitems, clear=True)

        self.winfo_toplevel().event_generate("<<Modified>>")

    # ----------------------------------------------------------------------
    # Clone selected blocks
    # ----------------------------------------------------------------------
    def clone(self, event=None):
        sel = list(map(int, self.curselection()))
        if not sel:
            return

        ypos = self.yview()[0]
        undoinfo = []
        self.selection_clear(0, END)
        pos = self._items[sel[-1]][0] + 1
        blocks = []
        for i in reversed(sel):
            bid, lid = self._items[i]
            if lid is None:
                undoinfo.append(self.gcode.cloneBlockUndo(bid, pos))
                for i in range(len(blocks)):
                    blocks[i] += 1
                blocks.append(pos)
            else:
                undoinfo.append(self.gcode.cloneLineUndo(bid, lid))
        self.gcode.addUndo(undoinfo)

        self.fill()
        self.yview_moveto(ypos)
        if blocks:
            self.selectBlocks(blocks)
            self.activate(self._blockPos[blocks[-1]])
        else:
            self.selection_set(ACTIVE)
        self.see(ACTIVE)
        self.winfo_toplevel().event_generate("<<Modified>>")
        return "break"

    # ----------------------------------------------------------------------
    # Delete selected blocks of code
    # ----------------------------------------------------------------------
    def deleteBlock(self, event=None):
        sel = list(map(int, self.curselection()))
        if not sel:
            return

        ypos = self.yview()[0]
        undoinfo = []
        for i in reversed(sel):
            bid, lid = self._items[i]
            if isinstance(lid, int):
                undoinfo.append(self.gcode.delLineUndo(bid, lid))
            else:
                undoinfo.append(self.gcode.delBlockUndo(bid))
        self.gcode.addUndo(undoinfo)

        self.selection_clear(0, END)
        self.fill()
        self.yview_moveto(ypos)
        self.selection_set(ACTIVE)
        self.see(ACTIVE)
        self.winfo_toplevel().event_generate("<<Modified>>")

    # ----------------------------------------------------------------------
    # Edit active item
    # ----------------------------------------------------------------------
    def edit(self, event=None):
        active = self.index(ACTIVE)
        txt = self.get(active)
        if event:
            x = event.x
        else:
            x = 0

        ypos = self.yview()[0]
        bid, lid = self._items[active]
        if lid is None:
            txt0 = txt
            txt = self.gcode[bid].name()
            self.set(active, txt)
            edit = tkExtra.InPlaceEdit(self, select=False, bg=self.cget("bg"))
        else:
            edit = tkExtra.InPlaceEdit(
                self, x=x, select=False, bg=self.cget("bg"))

        if edit.value is None or edit.value == txt:
            if lid is None:
                self.set(active, txt0)
                self.itemconfig(active, background=BLOCK_COLOR)
                if not self.gcode[bid].enable:
                    self.itemconfig(active, foreground=DISABLE_COLOR)
            return

        if isinstance(lid, int):
            self.gcode.addUndo(self.gcode.setLineUndo(bid, lid, edit.value))
            self.set(active, edit.value)
            if edit.value and edit.value[0] in ("(", "%"):
                self.itemconfig(active, foreground=COMMENT_COLOR)

        else:
            self.gcode.addUndo(self.gcode.setBlockNameUndo(bid, edit.value))
            self.set(active, self.gcode[bid].header())
            self.itemconfig(active, background=BLOCK_COLOR)
            if not self.gcode[bid].enable:
                self.itemconfig(active, foreground=DISABLE_COLOR)

        self.yview_moveto(ypos)
        self.winfo_toplevel().event_generate("<<Modified>>")

    # ----------------------------------------------------------------------
    # return active block id
    # ----------------------------------------------------------------------
    def activeBlock(self):
        active = self.index(ACTIVE)
        if self._items:
            bid, lid = self._items[active]
        else:
            bid = 0
        return bid

    # ----------------------------------------------------------------------
    # Insert a line or a block
    # ----------------------------------------------------------------------
    def insertItem(self, event=None):
        active = self.index(ACTIVE)
        if active is None:
            return
        if len(self._items) == 0 or self._items[active][1] is None:
            self.insertBlock()
        else:
            self.insertLine()

    # ----------------------------------------------------------------------
    # Insert New Block
    # ----------------------------------------------------------------------
    def insertBlock(self, event=None):
        active = self.index(ACTIVE)
        if self._items:
            bid, lid = self._items[active]
            bid += 1
        else:
            bid = 0

        block = Block()
        block.expand = True
        block.append("g0 x0 y0")
        block.append("g1 z0")
        block.append(CNC.zsafe())
        self.gcode.addUndo(self.gcode.addBlockUndo(bid, block))
        self.selection_clear(0, END)
        self.fill()
        # find location of new block
        while active < self.size():
            if self._items[active][0] == bid:
                break
            active += 1
        self.selection_set(active)
        self.see(active)
        self.activate(active)
        self.edit()
        self.winfo_toplevel().event_generate("<<Modified>>")

    # ----------------------------------------------------------------------
    # Insert a new line below cursor
    # ----------------------------------------------------------------------
    def insertLine(self, event=None):
        active = self.index(ACTIVE)
        if active is None:
            return
        if len(self._items) == 0:
            self.insertBlock()
            return

        bid, lid = self._items[active]

        active += 1

        self.insert(active, "")
        self.selection_clear(0, END)
        self.activate(active)
        self.selection_set(active)
        self.see(active)

        edit = tkExtra.InPlaceEdit(self, bg=self.cget("bg"))
        ypos = self.yview()[0]
        self.delete(active)

        if edit.value is None:
            # Cancel and leave
            active -= 1
            self.activate(active)
            self.selection_set(active)
            self.see(active)
            return

        self.insert(active, edit.value)
        self.selection_set(active)
        self.activate(active)
        if edit.value and edit.value[0] in ("(", "%"):
            self.itemconfig(active, foreground=COMMENT_COLOR)
        self.yview_moveto(ypos)

        # Add line into code

        # Correct pointers
        if lid is None:
            lid = 0
        else:
            lid += 1
        self.gcode.addUndo(self.gcode.insLineUndo(bid, lid, edit.value))

        self._items.insert(active, (bid, lid))
        for i in range(active + 1, len(self._items)):
            b, li = self._items[i]
            if b != bid:
                break
            if isinstance(li, int):
                self._items[i] = (b, li + 1)
        for i in range(bid + 1, len(self._blockPos)):
            if self._blockPos[i] is not None:
                self._blockPos[i] += 1  # shift all blocks below by one

        self.winfo_toplevel().event_generate("<<Modified>>")

    # ----------------------------------------------------------------------
    def toggleKey(self, event=None):
        if not self._items:
            return
        active = self.index(ACTIVE)
        bid, lid = self._items[active]
        if lid is None:
            self.toggleExpand()
        else:
            # Go to header
            self.selection_clear(0, END)
            self.activate(self._blockPos[bid])
            self.selection_set(ACTIVE)
            self.see(ACTIVE)
            self.winfo_toplevel().event_generate("<<ListboxSelect>>")

    # ----------------------------------------------------------------------
    # Button1 clicked
    # ----------------------------------------------------------------------
    def button1(self, event):
        if self._double:
            return

        # Remember if we had the focus before clicking
        # to be used later in editing
        self._hadfocus = self.focus_get() == self

        # from a single click
        self._ystart = self.nearest(event.y)
        selected = self.selection_includes(self._ystart)
        loc = self._headerLocation(event)
        if loc is None:
            pass
        elif self._headerLocation(event) < 2 and selected:
            return "break"  # do not alter selection!

    # ----------------------------------------------------------------------
    # Release button-1. Warning on separation of double or single click or
    # click and drag
    # ----------------------------------------------------------------------
    def release1(self, event):
        if not self._items:
            return
        if self._double:
            self._double = False
            return

        self._double = False
        active = self.index(ACTIVE)

        # from a single click
        y = self.nearest(event.y)
        self.activate(y)
        if y != self._ystart:
            return

        loc = self._headerLocation(event)
        if loc is None:
            # Normal line
            if active == y:
                # In place edit if we had already the focus
                if self._hadfocus:
                    self.edit(event)
        elif loc == 0:
            self.toggleExpand()
        elif loc == 1:
            self.toggleEnable()
        return "break"

    # ----------------------------------------------------------------------
    def double(self, event):
        if self._headerLocation(event) == 2:
            self.edit()
            self._double = True
        else:
            self._double = False

    # ----------------------------------------------------------------------
    # Return location where we clicked on header
    #  0 = expand arrow
    #  1 = enable ballot box
    #  2 = name
    # ----------------------------------------------------------------------
    def _headerLocation(self, event):
        if not self._items:
            return None
        # from a single click
        y = self.nearest(event.y)

        block, line = self._items[y]
        if line is not None:
            return None

        txt = self.get(y)
        if event.x <= self.font.measure(txt[:2]):
            return 0
        elif event.x <= self.font.measure(txt[:5]):
            return 1
        else:
            return 2

    # ----------------------------------------------------------------------
    # Toggle expand selection
    # ----------------------------------------------------------------------
    def toggleExpand(self, event=None):
        if not self._items:
            return None
        items = list(map(int, self.curselection()))
        expand = None
        active = self.index(ACTIVE)
        bactive, lactive = self._items[active]
        blocks = []
        undoinfo = []
        for i in reversed(items):
            bid, lid = self._items[i]
            if lid is not None:
                if bid in blocks:
                    continue
            blocks.append(bid)
            if expand is None:
                expand = not self.gcode[bid].expand
            undoinfo.append(self.gcode.setBlockExpandUndo(bid, expand))

        if undoinfo:
            self.gcode.addUndo(undoinfo)
            self.selection_clear(0, END)
            self.fill()
            active = self._blockPos[bactive]
            for bid in blocks:
                self.selectBlock(bid)
            self.activate(active)
            self.see(active)

        self.winfo_toplevel().event_generate(
            "<<Status>>", data="Toggled Expand of selected objects"
        )

    # ----------------------------------------------------------------------
    def _toggleEnable(self, enable=None):
        if not self._items:
            return None
        items = list(map(int, self.curselection()))
        active = self.index(ACTIVE)
        ypos = self.yview()[0]
        undoinfo = []
        blocks = []
        for i in items:
            bid, lid = self._items[i]
            if lid is not None:
                if bid in blocks:
                    continue
                pos = self._blockPos[bid]
            else:
                pos = i

            blocks.append(bid)
            block = self.gcode[bid]
            if block.name() in ("Header", "Footer"):
                continue
            if enable is None:
                enable = not block.enable
            undoinfo.append(self.gcode.setBlockEnableUndo(bid, enable))

            sel = self.selection_includes(pos)
            self.delete(pos)
            self.insert(pos, block.header())
            self.itemconfig(pos, background=BLOCK_COLOR)
            if not block.enable:
                self.itemconfig(pos, foreground=DISABLE_COLOR)
            if sel:
                self.selection_set(pos)

        if undoinfo:
            self.gcode.calculateEnableMargins()
            self.gcode.addUndo(undoinfo)
            self.activate(active)
            self.yview_moveto(ypos)
            self.winfo_toplevel().event_generate("<<ListboxSelect>>")

    # ----------------------------------------------------------------------
    def enable(self, event=None):
        self._toggleEnable(True)
        self.winfo_toplevel().event_generate(
            "<<Status>>", data="Enabled selected objects"
        )

    # ----------------------------------------------------------------------
    def disable(self, event=None):
        self._toggleEnable(False)
        self.winfo_toplevel().event_generate(
            "<<Status>>", data="Disabled selected objects"
        )

    # ----------------------------------------------------------------------
    # toggle state enable/disable
    # ----------------------------------------------------------------------
    def toggleEnable(self, event=None):
        self._toggleEnable()
        self.winfo_toplevel().event_generate(
            "<<Status>>", data="Toggled Visibility of selected objects"
        )

    # ----------------------------------------------------------------------
    # comment uncomment row
    # ----------------------------------------------------------------------
    def commentRow(self, event=None):
        if not self._items:
            return
        all_items = self._items
        sel_items = list(map(int, self.curselection()))
        mreg = re.compile(r"^\((.*)\)$")
        change = False
        for i in sel_items:
            my_item = all_items[i]
            if my_item[1] is not None:
                change = True
                # check for ()
                line = self.gcode[my_item[0]][my_item[1]]
                m = mreg.search(line)
                if m is None:
                    self.gcode[my_item[0]][my_item[1]] = "(" + line + ")"
                else:
                    self.gcode[my_item[0]][my_item[1]] = m.group(1)
        if change:
            self.fill()

    # ----------------------------------------------------------------------
    # splitBlocks
    # ----------------------------------------------------------------------
    def joinBlocks(self, event=None):
        if not self._items:
            return
        sel_items = list(map(int, self.curselection()))
        change = True
        bl = Block(self.gcode[sel_items[0]].name())
        for bid in sel_items:
            for line in self.gcode[bid]:
                bl.append(line)
            bl.append("( ---------- cut-here ---------- )")
        del bl[-1]
        self.gcode.addUndo(self.gcode.addBlockUndo(bid + 1, bl))
        if change:
            self.fill()
        self.deleteBlock()
        self.winfo_toplevel().event_generate("<<Modified>>")

    # ----------------------------------------------------------------------
    # splitBlocks
    # ----------------------------------------------------------------------
    def splitBlocks(self, event=None):
        if not self._items:
            return
        sel_items = list(map(int, self.curselection()))
        change = True
        for bid in sel_items:
            bl = Block(self.gcode[bid].name())
            for line in self.gcode[bid]:
                if line == "( ---------- cut-here ---------- )":
                    self.gcode.addUndo(self.gcode.addBlockUndo(bid + 1, bl))
                    bl = Block(self.gcode[bid].name())
                else:
                    bl.append(line)
        self.gcode.addUndo(self.gcode.addBlockUndo(bid + 1, bl))
        if change:
            self.fill()
        self.deleteBlock()
        self.winfo_toplevel().event_generate("<<Modified>>")

    # ----------------------------------------------------------------------
    # change color of a block
    # ----------------------------------------------------------------------
    def changeColor(self, event=None):
        items = list(map(int, self.curselection()))
        if not items:
            self.winfo_toplevel().event_generate(
                "<<Status>>", data="Nothing is selected"
            )
            return

        # Find initial color
        bid, lid = self._items[items[0]]

        try:
            rgb, color = tkExtra.askcolor(
                title=_("Color"),
                initialcolor=self.gcode[bid].color,
                parent=self
            )
        except TclError:
            color = None
        if color is None:
            return

        blocks = []
        undoinfo = []
        for i in reversed(items):
            bid, lid = self._items[i]
            if lid is not None:
                if bid in blocks:
                    continue
            blocks.append(bid)
            oldColor = self.gcode[bid].color
            undoinfo.append(self.gcode.setBlockColorUndo(bid, oldColor))

        if undoinfo:
            self.gcode.addUndo(undoinfo)
            for bid in blocks:
                self.gcode[bid].color = color
            self.winfo_toplevel().event_generate("<<Modified>>")
        self.winfo_toplevel().event_generate(
            "<<Status>>", data="Changed color of block"
        )

    # ----------------------------------------------------------------------
    # Select items in the form of (block, item)
    # ----------------------------------------------------------------------
    def select(self, items, double=False, clear=False, toggle=True):
        if clear:
            self.selection_clear(0, END)
            toggle = False
        first = None

        for bi in items:
            bid, lid = bi
            try:
                block = self.gcode[bid]
            except Exception:
                continue

            if double:
                if block.expand:
                    # select whole block
                    y = self._blockPos[bid]
                else:
                    # select all blocks with the same name
                    name = block.nameNop()
                    for i, bl in enumerate(self.gcode.blocks):
                        if name == bl.nameNop():
                            self.selection_set(self._blockPos[i])
                    continue

            elif not block.expand or lid is None:
                # select whole block
                y = self._blockPos[bid]

            elif isinstance(lid, int):
                # find line of block
                y = self._blockPos[bid] + 1 + lid

            else:
                raise
                # continue

            if y is None:
                continue

            if toggle:
                select = not self.selection_includes(y)
            else:
                select = True

            if select:
                self.selection_set(y)
                if first is None:
                    first = y
            elif toggle:
                self.selection_clear(y)

        if first is not None:
            self.activate(first)
            self.see(first)

    # ----------------------------------------------------------------------
    # Select whole block lines if expanded
    # ----------------------------------------------------------------------
    def selectBlock(self, bid):
        start = self._blockPos[bid]
        while True:
            bid += 1
            if bid >= len(self._blockPos):
                end = END
                break
            elif self._blockPos[bid] is not None:
                end = self._blockPos[bid] - 1
                break
        self.selection_set(start, end)

    # ----------------------------------------------------------------------
    def selectBlocks(self, blocks):
        self.selection_clear(0, END)
        for bid in blocks:
            self.selectBlock(bid)

    # ----------------------------------------------------------------------
    def selectAll(self):
        self.selection_set(0, END)

    # ----------------------------------------------------------------------
    def selectClear(self):
        self.selection_clear(0, END)

    # ----------------------------------------------------------------------
    def selectInvert(self):
        for i in range(self.size()):
            if self.selection_includes(i):
                self.selection_clear(i)
            else:
                self.selection_set(i)

    # ----------------------------------------------------------------------
    # Select all blocks with the same name of the selected layer
    # ----------------------------------------------------------------------
    def selectLayer(self):
        for bid in self.getSelectedBlocks():
            name = self.gcode[bid].nameNop()
            for i, bl in enumerate(self.gcode.blocks):
                if name == bl.nameNop():
                    self.selection_set(self._blockPos[i])

    # ----------------------------------------------------------------------
    # Return list of [(blocks,lines),...] currently being selected
    # ----------------------------------------------------------------------
    def getSelection(self):
        return [self._items[int(i)] for i in self.curselection()]

    # ----------------------------------------------------------------------
    # Return all blocks that at least an item is selected
    # ----------------------------------------------------------------------
    def getSelectedBlocks(self):
        blocks = {}
        for i in self.curselection():
            block, line = self._items[int(i)]
            blocks[block] = True
        return list(sorted(blocks.keys()))

    # ----------------------------------------------------------------------
    # Return list of [(blocks,lines),...] currently being selected
    # Filtering all items that the block is also selected
    # ----------------------------------------------------------------------
    def getCleanSelection(self):
        items = [self._items[int(i)] for i in self.curselection()]
        if not items:
            return items
        blocks = {}
        i = 0
        while i < len(items):
            bid, lid = items[i]
            if lid is None:
                blocks[bid] = True
                i += 1
            elif blocks.get(bid, False):
                del items[i]
            else:
                i += 1
        return items

    # ----------------------------------------------------------------------
    def getActive(self):
        active = self.index(ACTIVE)
        if active is None:
            return None
        if not self.selection_includes(active):
            try:
                active = self.curselection()[0]
            except Exception:
                return (0, None)
        return self._items[int(active)]

    # ----------------------------------------------------------------------
    # Move selected items upwards
    # ----------------------------------------------------------------------
    def orderUp(self, event=None):
        items = self.getCleanSelection()
        if not items:
            return
        sel = self.gcode.orderUp(items)
        self.fill()
        self.select(sel, clear=True, toggle=False)
        self.winfo_toplevel().event_generate("<<Modified>>")
        return "break"

    # ----------------------------------------------------------------------
    # Move selected items downwards
    # ----------------------------------------------------------------------
    def orderDown(self, event=None):
        items = self.getCleanSelection()
        if not items:
            return
        sel = self.gcode.orderDown(items)
        self.fill()
        self.select(sel, clear=True, toggle=False)
        self.winfo_toplevel().event_generate("<<Modified>>")
        return "break"

    # ----------------------------------------------------------------------
    # Invert selected blocks
    # ----------------------------------------------------------------------
    def invertBlocks(self, event=None):
        blocks = self.getSelectedBlocks()
        if not blocks:
            return
        self.gcode.addUndo(self.gcode.invertBlocksUndo(blocks))
        self.fill()
        # do not send a modified message, no need to redraw
        return "break"

    # ----------------------------------------------------------------------
    # Dump list and code, check for mismatch
    # ----------------------------------------------------------------------
    def dump(self, event=None):
        if not CNC.developer:
            return
        print("*** LIST ***")
        for i, sel in enumerate(self.get(0, END)):
            # TODO: do we need .encode()???
            print(i, sel.encode("ascii", "replace"))

        print("\n*** ITEMS ***")
        for i, item in enumerate(self._items):
            print(i, item)

        print("\n*** CODE ***")
        for i, block in enumerate(self.gcode.blocks):
            print("Block:", i, block.name())
            for j, line in enumerate(block):
                print("   %3d %s" % (j, line))

        print("\nBLOCKPOS=", self._blockPos)
