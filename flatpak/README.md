Flatpak build and run
===

Download data if need
```
git clone https://github.com/vlachoudis/bCNC
cd bCNC/flatpak
```

Build flatpak packet from manifest-file `io.github.bcnc.json`
```
flatpak-builder --force-clean                  builddir io.github.bcnc.json
flatpak-builder --force-clean --user --install builddir io.github.bcnc.json
# For remove application use
# flatpak-builder remove                                io.github.bcnc
```

To give (read-only) access to host filesystem run:
```
flatpak override --user --filesystem=host:ro io.github.bcnc
```

To launch the application from the command line run:
```
flatpak run io.github.bcnc
```

Launch application with access to serial devices run:
```
flatpak run --device=all io.github.bcnc
```

if replace `".."` to `"https://github.com/vlachoudis/bCNC"` in manifest-file
you can use it singly
