"""Self-test of an installed or frozen CustomLab, without any visible window: `CustomLab --selftest [--report FILE]`.

Checks, in order: imports (GUI included, Qt offscreen), device profiles, bundled resources, Phoenix scale formula, then the export of
one bundled Phoenix part at a non-100 % scale into a temporary folder (STL + JSON sheet + attribution), compared with the source.
Exit code 0 when everything passes, 1 otherwise. Run in CI on the PyInstaller build (Windows .exe, macOS .app): the Windows build has
no console (console=False), so `--report FILE` also writes the report to a file.
"""
import os
import sys
import tempfile
import traceback
from pathlib import Path

WRIST_MM, PART = 40.0, "Box"          # 40 mm + 5 mm margin -> 104.65 %; Box is the smallest bundled Phoenix part


def _imports():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    import customlab.gui, customlab.placement, customlab.deco, customlab.export_all  # noqa: F401,E401
    from PySide6.QtWidgets import QApplication
    customlab.deco._ensure_qt()                         # same Qt start as the engine (Windows fonts in offscreen mode)
    app = QApplication.instance()
    return f"Qt {app.platformName()}"


def _profiles():
    from .profiles import list_profiles, load_profile
    ids = [p["id"] for p in list_profiles()]
    missing = {"phoenix_hand", "kinetic_hand", "kinetic_arm", "unlimbited_arm"} - set(ids)
    if missing: raise AssertionError(f"profils absents / missing profiles: {sorted(missing)}")
    for i in ids: load_profile(i)
    return ", ".join(ids)


def _resources():
    from . import paths, theme
    from .library import BUNDLED_ROOT
    need = [theme.LOGO, paths.resource_dir() / "docs" / "TUTO_ECHELLES.md", paths.resource_dir() / "examples" / "star.svg", BUNDLED_ROOT]
    absent = [str(p) for p in need if not Path(p).exists()]
    if absent: raise AssertionError(f"ressources absentes / missing resources: {absent}")
    return f"{len(need)} ok"


def _scale():
    from .profiles import compute_phoenix_sizing
    r = compute_phoenix_sizing("left", PART, WRIST_MM)
    pct = r.measurements["scale_percent"]
    if abs(pct - 104.65) > 1e-9: raise AssertionError(f"échelle Phoenix inattendue / unexpected Phoenix scale: {pct}")
    return pct


def _export(pct):
    from . import export_all
    from .library import BUNDLED_ROOT, scan
    from .meshio import bbox, read_stl
    parts = [it for it in scan(BUNDLED_ROOT, bundled=True) if it["part"] == PART and it["side"] == "left"]
    if len(parts) != 1: raise AssertionError(f"pièce Phoenix {PART} gauche introuvable / bundled part not found ({len(parts)})")
    src = Path(parts[0]["path"])
    with tempfile.TemporaryDirectory(prefix="customlab_selftest_") as d:
        ctx = {"mirror_for": lambda p: False, "scale_for": lambda p: (pct, None), "extra": lambda: {"device": "phoenix_hand", "selftest": True}}
        res = export_all.run([(parts[0]["label"], src)], None, Path(d) / "export", ctx)
        if [r["status"] for r in res] != ["ok"]: raise AssertionError(f"export : {res}")
        folder = Path(res[0]["folder"]); stls = list(folder.glob("*.stl"))
        if len(stls) != 1 or not list(folder.glob("*.json")) or not list(folder.glob("*_ATTRIBUTION.txt")):
            raise AssertionError(f"fichiers exportés incomplets / incomplete export: {sorted(p.name for p in folder.iterdir())}")
        a, b = read_stl(src), read_stl(stls[0])
        if len(a) != len(b): raise AssertionError(f"triangles {len(a)} -> {len(b)}")
        (a0, a1), (b0, b1) = bbox(a), bbox(b); k = pct / 100.0
        for i in range(3):
            if abs((b1[i] - b0[i]) - (a1[i] - a0[i]) * k) > 1e-3: raise AssertionError(f"axe {i} : mise à l'échelle incorrecte / wrong scaling")
        return f"{stls[0].name}, {len(b)} triangles"


STEPS = [("imports", _imports), ("profils / profiles", _profiles), ("ressources / resources", _resources)]


def run(report=print):
    """Runs every step, reports each one; -> 0 if all pass, 1 otherwise."""
    from . import __version__
    report(f"CustomLab {__version__} selftest - Python {sys.version.split()[0]} - {sys.platform} - frozen={bool(getattr(sys, 'frozen', False))}")
    ok, pct = True, None
    steps = STEPS + [("échelle Phoenix / Phoenix scale", _scale), ("export Phoenix", lambda: _export(pct))]
    for name, fn in steps:
        try:
            val = fn()
            if fn is _scale: pct = val
            report(f"[OK] {name} : {val}")
        except Exception as e:
            ok = False; report(f"[ÉCHEC / FAILED] {name} : {e}"); report(traceback.format_exc().rstrip())
            if fn is _scale: break                       # the export needs the scale
    report("selftest " + ("OK" if ok else "ÉCHEC / FAILED"))
    return 0 if ok else 1


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(prog="CustomLab --selftest")
    ap.add_argument("--selftest", action="store_true"); ap.add_argument("--report", help="also write the report to this file (UTF-8)")
    a, _ = ap.parse_known_args(sys.argv[1:] if argv is None else argv)
    lines = []

    def report(s):
        lines.append(s)
        stream = sys.stdout
        if stream is not None:                           # None in the windowed Windows build (console=False)
            try: print(s, file=stream, flush=True)
            except (OSError, UnicodeEncodeError): pass
    code = run(report)
    if a.report:
        try: Path(a.report).write_text("\n".join(lines) + "\n", encoding="utf-8")
        except OSError: code = 1
    return code


if __name__ == "__main__":
    raise SystemExit(main())
