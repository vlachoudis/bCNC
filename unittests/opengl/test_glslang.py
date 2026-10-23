"""Static GLSL validation via glslangValidator (no GL context required)."""

import os
import shutil
import subprocess
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import pathfix  # noqa: F401  # shared unittests bootstrap

from shaders import iter_shader_files


def _glslang():
    return shutil.which("glslangValidator") or shutil.which("glslang")


def _require_tools():
    return os.environ.get("CI") or os.environ.get("BCNC_REQUIRE_SHADER_TOOLS")


@unittest.skipUnless(
    _glslang() or _require_tools(),
    "glslangValidator not installed",
)
class TestGlslangValidate(unittest.TestCase):
    def test_all_shaders_validate(self):
        glslang = _glslang()
        if not glslang:
            self.fail(
                "glslangValidator not installed "
                "(required when CI or BCNC_REQUIRE_SHADER_TOOLS is set)"
            )
        failures = []
        count = 0
        for path, stage in iter_shader_files():
            count += 1
            proc = subprocess.run(
                [glslang, "-S", stage, path],
                capture_output=True,
                text=True,
            )
            if proc.returncode != 0:
                failures.append(
                    "%s\n%s%s"
                    % (path, proc.stdout or "", proc.stderr or "")
                )
        self.assertGreater(count, 0, "no shader files found")
        if failures:
            self.fail(
                "%d shader(s) failed glslang validation:\n\n%s"
                % (len(failures), "\n---\n".join(failures))
            )


if __name__ == "__main__":
    unittest.main()
