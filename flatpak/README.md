Flatpak - how to build, install and run
===

Download the source code:
```
$ git clone https://github.com/vlachoudis/bCNC
$ cd bCNC/flatpak
```

Build flatpak bundle from the manifest-file `io.github.bcnc.json`:
```
$ flatpak-builder --ccache --jobs=$(getconf _NPROCESSORS_ONLN) --force-clean builddir io.github.bcnc.json
```

Install the application using:
```
$ flatpak-builder --force-clean --user --install builddir io.github.bcnc.json
```

For uninstalling the application use:
```
$ flatpak-builder remove io.github.bcnc
```

You should be able to launch the application from your desktop
environment. To launch the application from the command line run:
```
$ flatpak run io.github.bcnc
```
