#!/usr/bin/env python3

import os
import sys
import getopt

PRGPATH = os.path.abspath(os.path.dirname(__file__))
sys.path.append(PRGPATH)
sys.path.append(os.path.join(PRGPATH, "lib"))
sys.path.append(os.path.join(PRGPATH, "plugins"))
sys.path.append(os.path.join(PRGPATH, "controllers"))

# -----------------------------------------------------------------------------
def usage(rc):
    import Utils
    wrt = sys.stdout.write
    wrt(
        f"{Utils.__prg__} V{Utils.__version__} [{Utils.__date__}] "
        + f"{Utils.__platform_fingerprint__}\n"
    )
    wrt(f"{Utils.__author__} <{Utils.__email__}>\n\n")
    wrt("Usage: [options] [filename...]\n\n")
    wrt("Options:\n")
    wrt("\t-b # | --baud #\t\tSet the baud rate\n")
    wrt("\t-d\t\t\tEnable developer features\n")
    wrt("\t-D\t\t\tDisable developer features\n")
    wrt("\t-f | --fullscreen\tEnable fullscreen mode\n")
    wrt("\t-g #\t\t\tSet the default geometry\n")
    wrt("\t-h | -? | --help\tThis help page\n")
    wrt("\t-i # | --ini #\t\tAlternative ini file for testing\n")
    wrt("\t-l | --list\t\tList all recently opened files\n")
    wrt("\t-p # | --pendant #\tOpen pendant to specified port\n")
    wrt("\t-P\t\t\tDo not start pendant\n")
    wrt("\t-r | --recent\t\tLoad the most recent file opened\n")
    wrt("\t-R #\t\t\tLoad the recent file matching the argument\n")
    wrt("\t-s # | --serial #\tOpen serial port specified\n")
    wrt("\t-S\t\t\tDo not open serial port\n")
    wrt("\t--run\t\t\tDirectly run the file once loaded\n")
    wrt("\n")
    sys.exit(rc)


# -----------------------------------------------------------------------------
def main():
    import Helpers
    import bmain
    import tkExtra
    import Utils
    import Updates
    from CNC import CNC
    try:
        import serial
    except ImportError:
        serial = None
        print("testing mode, could not import serial")

    # Parse arguments
    try:
        optlist, args = getopt.getopt(
            sys.argv[1:],
            "?b:dDfhi:g:rlpPSs:",
            [
                "help",
                "ini=",
                "fullscreen",
                "recent",
                "list",
                "pendant=",
                "serial=",
                "baud=",
                "run",
            ],
        )
    except getopt.GetoptError:
        usage(1)

    recent = None
    run = False
    fullscreen = False
    for opt, val in optlist:
        if opt in ("-h", "-?", "--help"):
            usage(0)
        elif opt in ("-i", "--ini"):
            Utils.iniUser = val
            Utils.loadConfiguration()
        elif opt == "-d":
            CNC.developer = True
        elif opt == "-D":
            CNC.developer = False
        elif opt in ("-r", "-R", "--recent", "-l", "--list"):
            if opt in ("-r", "--recent"):
                r = 0
            elif opt in ("--list", "-l"):
                r = -1
            else:
                try:
                    r = int(val) - 1
                except Exception:
                    # Scan in names
                    for r in range(Utils._maxRecent):
                        filename = Utils.getRecent(r)
                        if filename is None:
                            break
                        fn, ext = os.path.splitext(os.path.basename(filename))
                        if fn == val:
                            break
                    else:
                        r = 0
            if r < 0:
                # display list of recent files
                maxlen = 10
                for i in range(Utils._maxRecent):
                    try:
                        filename = Utils.getRecent(i)
                    except Exception:
                        continue
                    maxlen = max(maxlen, len(os.path.basename(filename)))

                sys.stdout.write("Recent files:\n")
                for i in range(Utils._maxRecent):
                    filename = Utils.getRecent(i)
                    if filename is None:
                        break
                    d = os.path.dirname(filename)
                    fn = os.path.basename(filename)
                    sys.stdout.write(f"  {i + 1:2d}: {fn:<{maxlen}}  {d}\n")

                try:
                    sys.stdout.write("Select one: ")
                    r = int(sys.stdin.readline()) - 1
                except Exception:
                    pass
            try:
                recent = Utils.getRecent(r)
            except Exception:
                pass

        elif opt in ("-f", "--fullscreen"):
            fullscreen = True

        elif opt == "-p":
            pass  # startPendant()

        elif opt == "-P":
            pass  # stopPendant()

        elif opt == "--pendant":
            pass  # startPendant on port

        elif opt == "--run":
            run = True

    application = bmain.Application(className=f"  {Utils.__prg__}  ")

    palette = {"background": application.cget("background")}

    color_count = 0
    custom_color_count = 0
    for color_name in (
        "background",
        "foreground",
        "activeBackground",
        "activeForeground",
        "disabledForeground",
        "highlightBackground",
        "highlightColor",
        "selectBackground",
        "selectForeground",
    ):
        color2 = Utils.getStr("Color", "global." + color_name.lower(), None)
        color_count += 1
        if (color2 is not None) and (color2.strip() != ""):
            palette[color_name] = color2.strip()
            custom_color_count += 1

            if color_count == 0:
                tkExtra.GLOBAL_CONTROL_BACKGROUND = color2
            elif color_count == 1:
                tkExtra.GLOBAL_FONT_COLOR = color2

    if custom_color_count > 0:
        print("Changing palette")
        application.tk_setPalette(**palette)

    if fullscreen:
        application.attributes("-fullscreen", True)

    # Parse remaining arguments except files
    if recent:
        args.append(recent)
    for fn in args:
        application.load(fn)

    if serial is None:
        application.showSerialError()

    if Updates.need2Check():
        application.checkUpdates()

    if run:
        application.run()

    try:
        application.mainloop()
    except KeyboardInterrupt:
        application.quit()

    application.close()
    Utils.saveConfiguration()

if __name__ == "__main__":
	sys.stdout.write("=" * 80 + "\n")
	sys.stdout.write(
		"WARNING: bCNC was recently ported to only support \n"
		+ "python3.8 and newer.\n"
	)
	sys.stdout.write(
		"Most things seem to work reasonably well.\n"
	)
	sys.stdout.write(
		"Please report any issues to: "
		+ "https://github.com/vlachoudis/bCNC/issues\n"
	)
	sys.stdout.write("=" * 80 + "\n")

	main()
