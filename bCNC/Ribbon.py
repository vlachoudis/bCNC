#
# Author: vvlachoudis@gmail.com
# Date: 18-Jun-2015

from tkinter import (
    YES,
    TRUE,
    X,
    Y,
    BOTH,
    LEFT,
    TOP,
    RIGHT,
    BOTTOM,
    NORMAL,
    DISABLED,
    StringVar,
    Menu,
)
from tkinter.ttk import (
    Button,
    Checkbutton,
    Frame,
    Label,
    Radiobutton,
)

import Utils
import tkExtra

__author__ = "Vasilis Vlachoudis"
__email__ = "vvlachoudis@gmail.com"

_TABFONT = ("Sans", "-14", "bold")
_FONT = ("Sans", "-11")

_BACKGROUND = "#E6E2E0"

_BACKGROUND_GROUP2 = "#B0C0C0"

_ACTIVE_COLOR = "LightYellow"
_LABEL_SELECT_COLOR = "#C0FFC0"

# Ribbon show state


# =============================================================================
# Frame Group with a button at bottom
# =============================================================================
class LabelGroup(Frame):
    def __init__(self, master, name, command=None, **kw):
        Frame.__init__(self, master, **kw)
        self.name = name

        # right frame as a separator
        f = tkExtra.Separator(self)
        f.pack(side=RIGHT, fill=Y, padx=0, pady=0)

        # frame to insert the buttons
        self.frame = Frame(self)
        self.frame.pack(side=TOP, expand=TRUE, fill=BOTH, padx=0, pady=0)

        # fixed height caption, the same for the label and the button variants
        caption = Frame(self, height=16)
        caption.pack_propagate(False)
        caption.pack(side=BOTTOM, fill=X)

        if command:
            self.label = Button(
                caption,
                text=name,
                image=Utils.icons["triangle_down"],
                compound=RIGHT,
                command=command,
                style="Caption.TButton",
            )
        else:
            self.label = Label(
                caption,
                style="Caption.TLabel",
                text=_(name),
                font=_FONT,
                anchor="center",
            )
        self.label.pack(fill=BOTH, expand=TRUE)

    # -----------------------------------------------------------------------
    def grid2rows(self):
        self.frame.grid_rowconfigure(0, weight=1)
        self.frame.grid_rowconfigure(1, weight=1)

    # -----------------------------------------------------------------------
    def grid3rows(self):
        self.grid2rows()
        self.frame.grid_rowconfigure(2, weight=1)


# =============================================================================
class _KeyboardFocus:
    # -----------------------------------------------------------------------
    def _bind(self):
        self.bind("<Return>", self._invoke)
        self.bind("<FocusIn>", self._focusIn)
        self.bind("<FocusOut>", self._focusOut)

    # -----------------------------------------------------------------------
    def _focusIn(self, event):
        self.__backgroundColor = self.cget("background")
        self.config(background=_ACTIVE_COLOR)

    # -----------------------------------------------------------------------
    def _focusOut(self, event):
        self.config(background=self.__backgroundColor)

    # -----------------------------------------------------------------------
    def _invoke(self, event):
        self.invoke()


def _ribbonStyle(kw, style):
    """ttk buttons have no anchor, justify, width and background options: the
    left aligned style is used when the icon is beside the text"""
    left = kw.pop("anchor", None) == "w" and kw.get("compound") != TOP
    kw.pop("background", None)
    kw.pop("width", None)
    kw.pop("justify", None)
    kw.setdefault("style", ("Left." if left else "") + style)
    return kw


# =============================================================================
# Button with Label that generates a Virtual Event or calls a command
# =============================================================================
class LabelButton(Button, _KeyboardFocus):
    def __init__(self, master, recipient=None, event=None, **kw):
        Button.__init__(self, master, **_ribbonStyle(kw, "Ribbon.TButton"))
        self.bind("<Return>", self._invoke)
        if recipient is not None:
            self.config(command=self.sendEvent)
            self._recipient = recipient
            self._event = event
        else:
            self._recipient = None
            self._event = None

    # -----------------------------------------------------------------------
    def sendEvent(self):
        self._recipient.event_generate(self._event)


# =============================================================================
class LabelCheckbutton(Checkbutton, _KeyboardFocus):
    def __init__(self, master, **kw):
        Checkbutton.__init__(
            self, master, **_ribbonStyle(kw, "Ribbon.Toolbutton"))
        self.bind("<Return>", self._invoke)


# =============================================================================
class LabelRadiobutton(Radiobutton, _KeyboardFocus):
    def __init__(self, master, **kw):
        Radiobutton.__init__(
            self, master, **_ribbonStyle(kw, "Ribbon.Toolbutton"))
        self.bind("<Return>", self._invoke)


# =============================================================================
class LabelCombobox(tkExtra.TtkCombobox):
    def __init__(self, master, **kw):
        tkExtra.TtkCombobox.__init__(self, master, state="readonly", **kw)


# =============================================================================
# Button with Label that popup a menu
# =============================================================================
class MenuButton(Button):
    def __init__(self, master, menulist, **kw):
        Button.__init__(
            self, master, command=self.showMenu, **_ribbonStyle(kw, "Ribbon.TButton"))
        self.bind("<Return>", self.showMenu)
        if menulist is not None:
            self._menu = MenuButton.createMenuFromList(self, menulist)
        else:
            self._menu = None

    # -----------------------------------------------------------------------
    def showMenu(self, event=None):
        if self._menu is not None:
            self._showMenu(self._menu)
        else:
            self._showMenu(self.createMenu())

    # -----------------------------------------------------------------------
    def _showMenu(self, menu):
        if menu is not None:
            menu.tk_popup(self.winfo_rootx(),
                          self.winfo_rooty() + self.winfo_height())

    # -----------------------------------------------------------------------
    def createMenu(self):
        return None

    # -----------------------------------------------------------------------
    @staticmethod
    def createMenuFromList(master, menulist):
        mainmenu = menu = Menu(master,
                               tearoff=0, activebackground=_ACTIVE_COLOR)
        for item in menulist:
            if item is None:
                menu.add_separator()
            elif isinstance(item, str):
                menu = Menu(mainmenu)
                mainmenu.add_cascade(label=item, menu=menu)
            else:
                name, icon, cmd = item
                if icon is None:
                    icon = "empty"
                menu.add_command(
                    label=name, image=Utils.icons[icon], compound=LEFT, command=cmd
                )
        return menu


# =============================================================================
# A label group with a drop down menu
# =============================================================================
class MenuGroup(LabelGroup):
    def __init__(self, master, name, menulist=None, **kw):
        LabelGroup.__init__(self, master, name, command=self._showMenu, **kw)
        self._menulist = menulist

    # -----------------------------------------------------------------------
    def createMenu(self):
        if self._menulist is not None:
            return MenuButton.createMenuFromList(self, self._menulist)
        else:
            return None

    # -----------------------------------------------------------------------
    def _showMenu(self):
        menu = self.createMenu()
        if menu is not None:
            menu.tk_popup(self.winfo_rootx(),
                          self.winfo_rooty() + self.winfo_height())


# =============================================================================
# Page Tab buttons
# =============================================================================
class TabButton(Radiobutton):
    def __init__(self, master, **kw):
        Radiobutton.__init__(self, master, style="Tab.Toolbutton", **kw)

    # -----------------------------------------------------------------------
    # Bind events on TabFrame
    # ----------------------------------------------------------------------
    def bindClicks(self, tabframe):
        self.bind("<Double-1>", tabframe.double)
        self.bind("<Button-1>", tabframe.dragStart)
        self.bind("<B1-Motion>", tabframe.drag)
        self.bind("<ButtonRelease-1>", tabframe.dragStop)
        self.bind("<Control-ButtonRelease-1>", tabframe.pinActive)

        self.bind("<Left>", tabframe._tabLeft)
        self.bind("<Right>", tabframe._tabRight)
        self.bind("<Down>", tabframe._tabDown)


# =============================================================================
# Page
# =============================================================================
class Page:  # <--- should be possible to be a toplevel as well
    _motionClasses = (
        LabelButton,
        LabelRadiobutton,
        LabelCheckbutton,
        LabelCombobox,
        MenuButton,
    )
    _name_ = None
    _icon_ = None
    _doc_ = "Tooltip"

    # -----------------------------------------------------------------------
    def __init__(self, master, **kw):
        self.master = master
        self.name = self._name_
        self._icon = Utils.icons[self._icon_]
        self._tab = None  # Tab button
        self.ribbons = []
        self.frames = []
        self.init()
        self.create()

    # -----------------------------------------------------------------------
    # Override initialization
    # -----------------------------------------------------------------------
    def init(self):
        pass

    # -----------------------------------------------------------------------
    # The tab page can change master if undocked
    # -----------------------------------------------------------------------
    # FIXME XXX SHOULD BE REMOVED
    # -----------------------------------------------------------------------
    def create(self):
        self.createPage()

    # -----------------------------------------------------------------------
    # FIXME XXX SHOULD BE REMOVED
    # -----------------------------------------------------------------------
    def createPage(self):
        self.page = Frame(self.master._pageFrame)
        return self.page

    # -----------------------------------------------------------------------
    # Called when a page is activated
    # -----------------------------------------------------------------------
    def activate(self):
        pass

    # -----------------------------------------------------------------------
    def refresh(self):
        pass

    # ----------------------------------------------------------------------
    def canUndo(self):
        return True

    # ----------------------------------------------------------------------
    def canRedo(self):
        return True

    # ----------------------------------------------------------------------
    def resetUndo(self):
        pass

    # ----------------------------------------------------------------------
    def undo(self, event=None):
        pass

    # ----------------------------------------------------------------------
    def redo(self, event=None):
        pass

    # ----------------------------------------------------------------------
    def refreshUndoButton(self):
        # Check if frame provides undo/redo
        if self.master is None:
            return
        if self.page is None:
            return

        if self.canUndo():
            state = NORMAL
        else:
            state = DISABLED
        self.master.tool["undo"].config(state=state)
        self.master.tool["undolist"].config(state=state)

        if self.canRedo():
            state = NORMAL
        else:
            state = DISABLED
        self.master.tool["redo"].config(state=state)

    # -----------------------------------------------------------------------
    def keyboardFocus(self):
        self._tab.focus_set()

    # -----------------------------------------------------------------------
    # Return the closest widget along a direction
    # -----------------------------------------------------------------------
    @staticmethod
    def __compareDown(x, y, xw, yw):
        return yw > y + 1

    @staticmethod
    def __compareUp(x, y, xw, yw):
        return yw < y - 1

    @staticmethod
    def __compareRight(x, y, xw, yw):
        return xw > x + 1

    @staticmethod
    def __compareLeft(x, y, xw, yw):
        return xw < x - 1

    # -----------------------------------------------------------------------
    @staticmethod
    def __closest(widget, compare, x, y):
        closest = None
        dc2 = 10000000
        if widget is None:
            return closest, dc2
        for child in widget.winfo_children():
            for class_ in Page._motionClasses:
                if isinstance(child, class_):
                    if child["state"] == DISABLED:
                        continue
                    xw = child.winfo_rootx()
                    yw = child.winfo_rooty()
                    if compare(x, y, xw, yw):
                        d2 = (xw - x) ** 2 + (yw - y) ** 2
                        if d2 < dc2:
                            closest = child
                            dc2 = d2
                    break
            else:
                c, d2 = Page.__closest(child, compare, x, y)
                if d2 < dc2:
                    closest = c
                    dc2 = d2
        return closest, dc2

    # -----------------------------------------------------------------------
    # Select/Focus the closest element
    # -----------------------------------------------------------------------
    def _ribbonUp(self, event=None):
        x = event.widget.winfo_rootx()
        y = event.widget.winfo_rooty()
        closest, d2 = Page.__closest(self.ribbon, Page.__compareUp, x, y)
        if closest is not None:
            closest.focus_set()

    # -----------------------------------------------------------------------
    def _ribbonDown(self, event=None):
        x = event.widget.winfo_rootx()
        y = event.widget.winfo_rooty()
        closest, d2 = Page.__closest(self.ribbon, Page.__compareDown, x, y)
        if closest is not None:
            closest.focus_set()

    # -----------------------------------------------------------------------
    def _ribbonLeft(self, event=None):
        x = event.widget.winfo_rootx()
        y = event.widget.winfo_rooty()
        closest, d2 = Page.__closest(self.ribbon, Page.__compareLeft, x, y)
        if closest is not None:
            closest.focus_set()

    # -----------------------------------------------------------------------
    def _ribbonRight(self, event=None):
        x = event.widget.winfo_rootx()
        y = event.widget.winfo_rooty()
        closest, d2 = Page.__closest(self.ribbon, Page.__compareRight, x, y)
        if closest is not None:
            closest.focus_set()


# =============================================================================
# TabRibbonFrame
# =============================================================================
class TabRibbonFrame(Frame):
    def __init__(self, master, **kw):
        Frame.__init__(self, master, **kw)

        self.oldActive = None
        self.activePage = StringVar(self)
        self.tool = {}
        self.pages = {}

        # === Top frame with buttons ===
        frame = Frame(self)
        frame.pack(side=TOP, fill=X)

        # --- Basic buttons ---
        b = LabelButton(
            frame,
            self,
            "<<New>>",
            image=Utils.icons["new"],
            style="TButton",
        )
        tkExtra.Balloon.set(b, _("New file"))
        b.pack(side=LEFT)

        b = LabelButton(
            frame,
            self,
            "<<Open>>",
            image=Utils.icons["load"],
            style="TButton",
        )
        tkExtra.Balloon.set(b, _("Open file [Ctrl-O]"))
        b.pack(side=LEFT)

        b = LabelButton(
            frame,
            self,
            "<<Save>>",
            image=Utils.icons["save"],
            style="TButton",
        )
        tkExtra.Balloon.set(b, _("Save all [Ctrl-S]"))
        b.pack(side=LEFT)

        b = LabelButton(
            frame,
            self,
            "<<Undo>>",
            image=Utils.icons["undo"],
            style="TButton",
        )
        tkExtra.Balloon.set(b, _("Undo [Ctrl-Z]"))
        b.pack(side=LEFT)
        self.tool["undo"] = b

        b = LabelButton(
            frame,
            image=Utils.icons["triangle_down"],
            command=self.undolist,
            style="TButton",
        )
        b.pack(side=LEFT, fill=Y)
        self.tool["undolist"] = b

        b = LabelButton(
            frame,
            self,
            "<<Redo>>",
            image=Utils.icons["redo"],
            style="TButton",
        )
        tkExtra.Balloon.set(b, _("Redo [Ctrl-Y]"))
        b.pack(side=LEFT)
        self.tool["redo"] = b

        tkExtra.Separator(frame).pack(
            side=LEFT, fill=Y
        )

        # --- Help ---
        b = LabelButton(
            frame,
            self,
            "<<Help>>",
            image=Utils.icons["info"],
            style="TButton",
        )
        tkExtra.Balloon.set(b, _("Help [F1]"))
        b.pack(side=RIGHT)

        tkExtra.Separator(frame).pack(
            side=RIGHT, fill=Y
        )

        # --- TabBar ---
        self._tabFrame = Frame(frame)
        self._tabFrame.pack(side=LEFT, fill=BOTH, expand=YES)

        # ==== Ribbon Frame ====
        self._ribbonFrame = Frame(self)
        self._ribbonHeight = 0
        self._ribbonFrame.pack(fill=BOTH, expand=YES, padx=0, pady=0)

        self.setPageFrame(None)

    # -----------------------------------------------------------------------
    def setPageFrame(self, frame):
        self._pageFrame = frame

    # -----------------------------------------------------------------------
    def undolist(self, event=None):
        self.event_generate("<<UndoList>>")

    # -----------------------------------------------------------------------
    def getActivePage(self):
        return self.pages[self.activePage.get()]

    # -----------------------------------------------------------------------
    # Add page to the tabs
    # -----------------------------------------------------------------------
    def addPage(self, page, side=LEFT):
        self.pages[page.name] = page
        page._tab = TabButton(
            self._tabFrame,
            image=page._icon,
            text=_(page.name),
            compound=LEFT,
            value=page.name,
            variable=self.activePage,
            command=self.changePage,
        )
        tkExtra.Balloon.set(page._tab, page.__doc__)

        page._tab.pack(side=side, fill=Y)
        self.after_idle(self._equalTabs)

    # ----------------------------------------------------------------------
    # Same width for all the tabs
    # ----------------------------------------------------------------------
    def _equalTabs(self):
        tabs = [page._tab for page in self.pages.values()]
        for tab in tabs:
            tab.pack_configure(ipadx=0)
        self.update_idletasks()
        width = max(tab.winfo_reqwidth() for tab in tabs)
        for tab in tabs:
            tab.pack_configure(ipadx=(width - tab.winfo_reqwidth()) // 2)

    # ----------------------------------------------------------------------
    # Same ribbon height for all the pages
    # ----------------------------------------------------------------------
    def _equalHeight(self):
        if self._ribbonHeight:
            return
        self.update_idletasks()
        height = max(
            frame.winfo_reqheight()
            for page in self.pages.values()
            for frame, args in page.ribbons
        )
        self._ribbonFrame.pack_propagate(False)
        self._ribbonFrame.configure(height=height)
        self._ribbonHeight = height


    # ----------------------------------------------------------------------
    # Unpack the old page
    # ----------------------------------------------------------------------
    def _forgetPage(self):
        if self.oldActive:
            for frame, args in self.oldActive.ribbons:
                frame.pack_forget()
            for frame, args in self.oldActive.frames:
                frame.pack_forget()
            self.oldActive = None

    # ----------------------------------------------------------------------
    # Change ribbon and page
    # ----------------------------------------------------------------------
    def changePage(self, page=None):
        if page is not None:
            if not isinstance(page, Page):
                try:
                    page = self.pages[page]
                except KeyError:
                    return
            self.activePage.set(page.name)
        else:
            try:
                page = self.pages[self.activePage.get()]
            except KeyError:
                return

        if page is self.oldActive:
            return

        self._forgetPage()
        self._equalHeight()

        for frame, args in page.ribbons:
            frame.pack(in_=self._ribbonFrame, **args)

        for frame, args in page.frames:
            frame.pack(in_=self._pageFrame,
                       **{"pady": (0, tkExtra.PANEL_GAP), **args})

        self.oldActive = page
        page.activate()
        self.event_generate("<<ChangePage>>", data=page.name)
