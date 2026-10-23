"""Compile and link bCNC shaders with a headless Mesa/EGL OpenGL context."""

import os
import sys
import unittest

# PyOpenGL reads the platform at import time.
os.environ.setdefault("PYOPENGL_PLATFORM", "egl")
os.environ.setdefault("LIBGL_ALWAYS_SOFTWARE", "1")
os.environ.setdefault("GALLIUM_DRIVER", "llvmpipe")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import pathfix  # noqa: F401  # shared unittests bootstrap

from shaders import iter_shader_pairs


def _create_egl_context():
    """Create a 1x1 EGL pbuffer + OpenGL core context. Returns cleanup callable."""
    from OpenGL.EGL import (
        EGL_CONTEXT_MAJOR_VERSION,
        EGL_CONTEXT_MINOR_VERSION,
        EGL_CONTEXT_OPENGL_CORE_PROFILE_BIT,
        EGL_CONTEXT_OPENGL_PROFILE_MASK,
        EGL_DEFAULT_DISPLAY,
        EGL_HEIGHT,
        EGL_NONE,
        EGL_NO_CONTEXT,
        EGL_NO_DISPLAY,
        EGL_NO_SURFACE,
        EGL_OPENGL_API,
        EGL_OPENGL_BIT,
        EGL_PBUFFER_BIT,
        EGL_RENDERABLE_TYPE,
        EGL_SURFACE_TYPE,
        EGL_WIDTH,
        EGLConfig,
        EGLint,
        eglBindAPI,
        eglChooseConfig,
        eglCreateContext,
        eglCreatePbufferSurface,
        eglGetDisplay,
        eglGetError,
        eglInitialize,
        eglMakeCurrent,
        eglTerminate,
    )

    display = eglGetDisplay(EGL_DEFAULT_DISPLAY)
    if display == EGL_NO_DISPLAY:
        raise RuntimeError("eglGetDisplay failed (error %s)" % eglGetError())
    if not eglInitialize(display, None, None):
        raise RuntimeError("eglInitialize failed (error %s)" % eglGetError())

    attribs = [
        EGL_SURFACE_TYPE,
        EGL_PBUFFER_BIT,
        EGL_RENDERABLE_TYPE,
        EGL_OPENGL_BIT,
        EGL_NONE,
    ]
    num = EGLint()
    configs = (EGLConfig * 1)()
    if not eglChooseConfig(display, attribs, configs, 1, num) or int(num.value) < 1:
        eglTerminate(display)
        raise RuntimeError("eglChooseConfig found no OpenGL configs (error %s)" % eglGetError())

    if not eglBindAPI(EGL_OPENGL_API):
        eglTerminate(display)
        raise RuntimeError("eglBindAPI(OPENGL) failed (error %s)" % eglGetError())

    ctx_attribs = [
        EGL_CONTEXT_MAJOR_VERSION,
        3,
        EGL_CONTEXT_MINOR_VERSION,
        2,
        EGL_CONTEXT_OPENGL_PROFILE_MASK,
        EGL_CONTEXT_OPENGL_CORE_PROFILE_BIT,
        EGL_NONE,
    ]
    ctx = eglCreateContext(display, configs[0], EGL_NO_CONTEXT, ctx_attribs)
    if ctx == EGL_NO_CONTEXT:
        eglTerminate(display)
        raise RuntimeError("eglCreateContext failed (error %s)" % eglGetError())

    surf = eglCreatePbufferSurface(
        display, configs[0], [EGL_WIDTH, 1, EGL_HEIGHT, 1, EGL_NONE]
    )
    if surf == EGL_NO_SURFACE:
        eglTerminate(display)
        raise RuntimeError("eglCreatePbufferSurface failed (error %s)" % eglGetError())

    if not eglMakeCurrent(display, surf, surf, ctx):
        eglTerminate(display)
        raise RuntimeError("eglMakeCurrent failed (error %s)" % eglGetError())

    def cleanup():
        eglMakeCurrent(display, EGL_NO_SURFACE, EGL_NO_SURFACE, EGL_NO_CONTEXT)
        eglTerminate(display)

    return cleanup


def _compile_program(vs_src, fs_src):
    from OpenGL.GL import (
        GL_COMPILE_STATUS,
        GL_FRAGMENT_SHADER,
        GL_LINK_STATUS,
        GL_VERTEX_SHADER,
        glAttachShader,
        glCompileShader,
        glCreateProgram,
        glCreateShader,
        glDeleteProgram,
        glDeleteShader,
        glGetProgramInfoLog,
        glGetProgramiv,
        glGetShaderInfoLog,
        glGetShaderiv,
        glLinkProgram,
        glShaderSource,
    )

    vs = glCreateShader(GL_VERTEX_SHADER)
    glShaderSource(vs, vs_src)
    glCompileShader(vs)
    if not glGetShaderiv(vs, GL_COMPILE_STATUS):
        log = glGetShaderInfoLog(vs)
        glDeleteShader(vs)
        raise RuntimeError("vertex compile failed: %s" % log)

    fs = glCreateShader(GL_FRAGMENT_SHADER)
    glShaderSource(fs, fs_src)
    glCompileShader(fs)
    if not glGetShaderiv(fs, GL_COMPILE_STATUS):
        log = glGetShaderInfoLog(fs)
        glDeleteShader(vs)
        glDeleteShader(fs)
        raise RuntimeError("fragment compile failed: %s" % log)

    program = glCreateProgram()
    glAttachShader(program, vs)
    glAttachShader(program, fs)
    glLinkProgram(program)
    glDeleteShader(vs)
    glDeleteShader(fs)
    if not glGetProgramiv(program, GL_LINK_STATUS):
        log = glGetProgramInfoLog(program)
        glDeleteProgram(program)
        raise RuntimeError("link failed: %s" % log)
    glDeleteProgram(program)


def _require_tools():
    return os.environ.get("CI") or os.environ.get("BCNC_REQUIRE_SHADER_TOOLS")


def _egl_probe():
    """Return (ok, error_message)."""
    try:
        cleanup = _create_egl_context()
        cleanup()
        return True, ""
    except Exception as exc:
        return False, str(exc)


_EGL_OK, _EGL_ERROR = _egl_probe()


@unittest.skipUnless(
    _EGL_OK or _require_tools(),
    "EGL/OpenGL context not available: %s" % _EGL_ERROR,
)
class TestMesaCompileLink(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not _EGL_OK:
            raise RuntimeError(
                "EGL/OpenGL context not available "
                "(required when CI or BCNC_REQUIRE_SHADER_TOOLS is set): %s"
                % _EGL_ERROR
            )
        cls._cleanup = _create_egl_context()
        from OpenGL.GL import (
            GL_RENDERER,
            GL_SHADING_LANGUAGE_VERSION,
            GL_VENDOR,
            GL_VERSION,
            glGetString,
        )

        cls.gl_info = (
            "vendor=%r renderer=%r version=%r glsl=%r"
            % (
                glGetString(GL_VENDOR),
                glGetString(GL_RENDERER),
                glGetString(GL_VERSION),
                glGetString(GL_SHADING_LANGUAGE_VERSION),
            )
        )

    @classmethod
    def tearDownClass(cls):
        if getattr(cls, "_cleanup", None):
            cls._cleanup()

    def test_all_shader_pairs_compile_and_link(self):
        failures = []
        count = 0
        for version, program, vs_path, fs_path in iter_shader_pairs():
            count += 1
            with open(vs_path, "r") as fh:
                vs_src = fh.read()
            with open(fs_path, "r") as fh:
                fs_src = fh.read()
            try:
                _compile_program(vs_src, fs_src)
            except Exception as exc:
                failures.append("%s/%s: %s" % (version, program, exc))
        self.assertGreater(count, 0, "no shader pairs found")
        if failures:
            self.fail(
                "%d shader program(s) failed compile/link (%s):\n\n%s"
                % (len(failures), self.gl_info, "\n".join(failures))
            )


if __name__ == "__main__":
    unittest.main()
