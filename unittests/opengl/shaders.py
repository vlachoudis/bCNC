"""Helpers for discovering bCNC OpenGL shader sources."""

import os

OPENGL_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "bCNC", "opengl")
)

SHADER_VERSIONS = ("v100", "v120", "v150")


def version_dirs():
    """Return absolute paths to shader version directories that exist."""
    dirs = []
    for name in SHADER_VERSIONS:
        path = os.path.join(OPENGL_ROOT, name)
        if os.path.isdir(path):
            dirs.append(path)
    if not dirs:
        raise FileNotFoundError("No shader version directories under %s" % OPENGL_ROOT)
    return dirs


def iter_shader_files():
    """Yield (path, stage) for every .shd file. stage is 'vert' or 'frag'."""
    for folder in version_dirs():
        for name in sorted(os.listdir(folder)):
            if not name.endswith(".shd"):
                continue
            path = os.path.join(folder, name)
            if name.endswith("VS.shd"):
                yield path, "vert"
            elif name.endswith("FS.shd"):
                yield path, "frag"
            else:
                raise AssertionError("Unexpected shader name (expected *VS.shd / *FS.shd): %s" % path)


def iter_shader_pairs():
    """Yield (version_name, program_name, vs_path, fs_path) for each VS/FS pair."""
    for folder in version_dirs():
        version = os.path.basename(folder)
        for name in sorted(os.listdir(folder)):
            if not name.endswith("VS.shd"):
                continue
            program = name[: -len("VS.shd")]
            vs_path = os.path.join(folder, name)
            fs_path = os.path.join(folder, program + "FS.shd")
            if not os.path.isfile(fs_path):
                raise FileNotFoundError("Missing fragment shader for %s: %s" % (vs_path, fs_path))
            yield version, program, vs_path, fs_path
