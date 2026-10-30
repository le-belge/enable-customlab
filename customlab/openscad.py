"""Run OpenSCAD headless on a user-provided .scad file."""
import shutil
import subprocess
from pathlib import Path

from . import paths

LOCAL = paths.resource_dir() / "tools" / "OpenSCAD.app" / "Contents" / "MacOS" / "OpenSCAD"
CANDIDATES = [str(LOCAL), "/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD", "/opt/homebrew/bin/openscad", "/usr/local/bin/openscad",
              "C:/Program Files/OpenSCAD/openscad.exe", "C:/Program Files (x86)/OpenSCAD/openscad.exe", "C:/Program Files/OpenSCAD (Nightly)/openscad.exe"]


class OpenSCADUnavailable(RuntimeError):
    pass


def find_openscad():
    found = shutil.which("openscad")
    if found:
        return found
    for c in CANDIDATES:
        if Path(c).exists():
            return c
    return None


def format_define(name, value):
    if isinstance(value, str):
        escaped = value.replace("\\", "\\\\").replace('"', '\\"')
        return f'{name}="{escaped}"'
    return f"{name}={value:g}" if isinstance(value, float) else f"{name}={value}"


def build_command(binary, scad_file, out_file, defines):
    cmd = [binary, "-o", str(out_file)]
    for k, v in defines.items():
        cmd += ["-D", format_define(k, v)]
    cmd.append(str(scad_file))
    return cmd


def render(scad_file, out_file, defines, timeout=600):
    binary = find_openscad()
    if not binary:
        raise OpenSCADUnavailable("OpenSCAD not found; install it and retry.")
    r = subprocess.run(build_command(binary, scad_file, out_file, defines),
                       capture_output=True, text=True, timeout=timeout)
    if r.returncode != 0 or not Path(out_file).exists():
        raise RuntimeError(f"OpenSCAD failed: {r.stderr[-500:]}")
    return Path(out_file)
