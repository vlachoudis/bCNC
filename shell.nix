# Dev shell mirroring install_requires in setup.py (Linux).
# Requires a reasonably recent nixpkgs (tkinter-gl / pyglm).
# Darwin-only deps (pyobjc*) are omitted.
let
  pkgs = import <nixpkgs> {};
  python = pkgs.python3.override {
    packageOverrides = self: super: {
      # Not packaged in nixpkgs yet; version matches setup.py
      shxparser = super.buildPythonPackage rec {
        pname = "shxparser";
        version = "0.0.2";
        format = "setuptools";
        src = super.fetchPypi {
          inherit pname version;
          hash = "sha256-hUHkvOYodoIsk/OVnn9pCe8b+DUmkbNDus2qqbkv8nA=";
        };
        pythonImportsCheck = [ "shxparser" ];
      };
    };
  };
in pkgs.mkShell {
  packages = [
    (python.withPackages (ps: [
      ps.tkinter
      ps.numpy
      ps.svgelements
      ps.pyserial
      ps.pillow
      ps.opencv4
      ps.shxparser
      ps.tkinter-gl
      ps.pyopengl
      ps.pyglm
    ]))
  ];
}
