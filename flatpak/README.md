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

Test application running
```
flatpak run io.github.bcnc
```

Launch application with allow device `/dev/ttyUSB1` and home user folder
```
flatpak run --device=/dev/ttyUSB1 --share="$HOME" io.github.bcnc
```

if replace `".."` to `"https://github.com/vlachoudis/bCNC"` in manifest-file
you can use it singly
