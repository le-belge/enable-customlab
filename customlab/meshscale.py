"""Uniform scaling of user-provided official STL parts (mesh architecture).

Valid only where the model's own documentation scales uniformly (Phoenix: scale %). Output is
rendered through OpenSCAD (scale + import) so the same toolchain is exercised as for .scad models,
and cross-checked against a pure-Python scaling in tests.
"""
import tempfile
from pathlib import Path

from . import openscad
from .meshio import read_stl, write_stl


def scale_stl_python(src, dst, percent):
    k = percent / 100.0
    write_stl(dst, [tuple(tuple(c * k for c in p) for p in t) for t in read_stl(src)])


def scale_stl_openscad(src, dst, percent):
    with tempfile.TemporaryDirectory() as d:
        scad = Path(d) / "s.scad"
        scad.write_text(f'scale({percent / 100.0!r}) import("{Path(src).resolve().as_posix()}");\n')
        openscad.render(scad, dst, {})
    return Path(dst)
