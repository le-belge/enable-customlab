"""Local parts library: STL files found under the project's sources/ folder, with their licence.

Nothing is bundled or copied: this only lists what the user has placed there.
"""
import hashlib
import re
from pathlib import Path

from . import paths
from .licenseinfo import read_license_info

BUNDLED_ROOT = Path(__file__).resolve().parent / "bundled_parts"
_PART = re.compile(r"_([A-Za-z]+?)\d{8}-")
SKIP_DIRS = ("grouped stls", "digital fitment", "advanced scaling")        # plates / low-res fitment files / workshop files: not parts to decorate


def _sha(f): return hashlib.sha256(Path(f).read_bytes()).hexdigest()


def scan_all(roots=None):
    """Bundled parts first, then the user's own sources/; identical files (same SHA-256) are listed once."""
    roots = roots or (BUNDLED_ROOT, paths.sources_dir())
    items = [it for r in roots for it in scan(r, bundled=(Path(r) == BUNDLED_ROOT))]
    sizes = {}
    for it in items: sizes.setdefault(Path(it["path"]).stat().st_size, []).append(it)
    seen, out = set(), []
    for it in items:                                     # only files of identical size can be duplicates: hash those only (the Kinetic sets weigh GBs)
        if len(sizes[Path(it["path"]).stat().st_size]) > 1:
            h = _sha(it["path"])
            if h in seen: continue
            seen.add(h)
        out.append(it)
    return out


def scan(root=None, bundled=False):
    items = []
    root = Path(root or paths.sources_dir())
    if not root.is_dir(): return items
    for f in sorted(p for p in root.rglob("*") if p.suffix.lower() == ".stl"):
        if any(d in (x.lower() for x in f.parts) for d in SKIP_DIRS): continue
        lic = read_license_info(f)
        low = [x.lower() for x in f.parts]
        device = "kinetic_hand" if "kinetic_hand" in low else "kinetic_arm" if "kinetic_arm" in low else "unlimbited_arm" if "unlimbited_arm" in low else "phoenix_hand"
        m = _PART.search(f.name); part = m.group(1) if m else re.sub(r"\s*\(.*\)\s*$", "", f.stem)
        side = next((p.name for p in f.parents if p.name in ("left", "right")), "")
        if device.startswith("kinetic"):
            mm = re.search(r"\((RH|LH)[^,)]*(?:,\s*([^)]*))?\)", f.stem); side = (mm.group(1) if mm else "") + (f" · {mm.group(2).strip()}" if mm and mm.group(2) else "")
            part = re.sub(r"\s*\(.*\)\s*$", "", f.stem)
            if mm: side = side.replace("RH", "RH 100 %").replace("LH", "LH 100 %")
        lab = f"{part}" + (f" · {side}" if side else "") + " — " + (lic["license"] if lic.get("known") else "licence inconnue")
        lab += " (incluse)" if bundled else ""
        items.append({"path": str(f), "label": lab, "bundled": bundled, "device": device, "part": part, "side": side, "license": lic})
    return items
