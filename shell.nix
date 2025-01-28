let
  pkgs = import <nixpkgs> {};
in pkgs.mkShell {
  packages = [
    (pkgs.python3.withPackages (python-pkgs: [
      python-pkgs.tkinter
      python-pkgs.numpy
      python-pkgs.svgelements
      python-pkgs.pyserial
      python-pkgs.pillow
    ]))
  ];
}
