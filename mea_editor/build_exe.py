"""
Build a standalone executable for the MEA Editor.

Usage:
    mea-editor-build
    # or: python -m mea_editor.build_exe

Prerequisites:
    pip install "mea-editor[build]"
    # or: pip install mea-editor pyinstaller

The executable is written to dist/ in the current working directory.
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

from ._version import __version__

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
EXE_BASENAME = "ElectrodeArrayEditor"

HIDDEN_IMPORTS = (
    "PySide6.QtCore",
    "PySide6.QtGui",
    "PySide6.QtWidgets",
    "shiboken6",
    "openpyxl",
    "openpyxl.cell._writer",
    "mea_editor._version",
    "mea_editor.array_integrity",
    "mea_editor.attribute_schema",
    "mea_editor.contact_shape",
    "mea_editor.electrode",
    "mea_editor.electrode_array_dialogs",
    "mea_editor.electrode_array_editor_io",
    "mea_editor.electrode_array_editor_qt",
    "mea_editor.electrode_array_view",
    "mea_editor.electrode_table_window",
    "mea_editor.electrode_view",
    "mea_editor.grid_scene",
    "mea_editor.pad",
    "mea_editor.pad_layout",
    "mea_editor.pad_view",
    "mea_editor.view_style",
)

EXCLUDED_MODULES = (
    "tkinter",
    "matplotlib",
    "numpy",
    "scipy",
    "pandas",
    "IPython",
    "pytest",
)


def executable_name(platform: str | None = None) -> str:
    """Return the onefile name for the given platform (default: current)."""
    system = sys.platform if platform is None else platform
    if system == "win32":
        return f"{EXE_BASENAME}.exe"
    return EXE_BASENAME


def pyinstaller_command(
    *,
    launcher: Path,
    project_root: Path,
    output_dir: Path,
    specpath: Path,
    python_executable: str | None = None,
) -> list[str]:
    """Build the PyInstaller command used by `mea-editor-build`."""
    cmd = [
        python_executable or sys.executable,
        "-m",
        "PyInstaller",
        f"--name={EXE_BASENAME}",
        "--windowed",
        "--onefile",
        "--clean",
        "--noconfirm",
        "--paths",
        str(project_root),
        "--collect-submodules=mea_editor",
        "--collect-submodules=openpyxl",
        "--distpath",
        str(output_dir),
        "--specpath",
        str(specpath),
        "--workpath",
        str(specpath / "work"),
    ]
    for name in HIDDEN_IMPORTS:
        cmd.extend(["--hidden-import", name])
    for name in EXCLUDED_MODULES:
        cmd.extend(["--exclude-module", name])
    cmd.append(str(launcher.resolve()))
    return cmd


def main() -> None:
    output_dir = Path.cwd() / "dist"
    exe_path = output_dir / executable_name()

    try:
        import PyInstaller  # noqa: F401
    except ImportError:
        print("ERROR: PyInstaller is required to build the executable.")
        print('Install with: pip install "mea-editor[build]"')
        sys.exit(1)

    if exe_path.exists():
        try:
            exe_path.unlink()
        except PermissionError:
            print("ERROR: The executable is locked (running or in use by another program).")
            print("Close ElectrodeArrayEditor and try again.")
            sys.exit(1)

    launcher = SCRIPT_DIR / "run_mea_editor.py"
    if not launcher.is_file():
        print(f"ERROR: Launcher not found: {launcher}")
        sys.exit(1)

    print(f"Building {EXE_BASENAME} {__version__} -> {exe_path}")
    with tempfile.TemporaryDirectory() as tmp:
        cmd = pyinstaller_command(
            launcher=launcher,
            project_root=PROJECT_ROOT,
            output_dir=output_dir,
            specpath=Path(tmp),
        )
        subprocess.run(cmd, check=True, cwd=Path.cwd())

    if not exe_path.exists():
        print(f"ERROR: PyInstaller finished but {exe_path} is missing.")
        sys.exit(1)
    print(f"\nExecutable created: {exe_path}")


if __name__ == "__main__":
    main()
