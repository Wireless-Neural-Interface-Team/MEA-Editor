"""PyInstaller command used by mea-editor-build."""

from __future__ import annotations

import unittest
from pathlib import Path

from mea_editor.build_exe import (
    EXE_BASENAME,
    HIDDEN_IMPORTS,
    executable_name,
    pyinstaller_command,
)


class BuildExeTests(unittest.TestCase):
    def test_windows_executable_name(self) -> None:
        self.assertEqual(executable_name("win32"), f"{EXE_BASENAME}.exe")
        self.assertEqual(executable_name("linux"), EXE_BASENAME)

    def test_command_collects_package_and_openpyxl(self) -> None:
        cmd = pyinstaller_command(
            launcher=Path("mea_editor/run_mea_editor.py"),
            project_root=Path("."),
            output_dir=Path("dist"),
            specpath=Path("tmp"),
            python_executable="python",
        )
        joined = " ".join(cmd)
        self.assertIn("--onefile", cmd)
        self.assertIn("--windowed", cmd)
        self.assertIn("--collect-submodules=mea_editor", cmd)
        self.assertIn("--collect-submodules=openpyxl", cmd)
        self.assertIn("mea_editor.array_integrity", joined)
        self.assertIn("mea_editor.electrode_array_editor_io", joined)
        self.assertIn("mea_editor.electrode_table_window", joined)
        self.assertIn("openpyxl.cell._writer", joined)
        self.assertTrue(set(HIDDEN_IMPORTS).issubset(set(cmd)))
        self.assertTrue(any(item.endswith("run_mea_editor.py") for item in cmd))


if __name__ == "__main__":
    unittest.main()
