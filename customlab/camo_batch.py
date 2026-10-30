"""Camouflage on several parts of a device in one go (a whole hand): one export folder per part, a summary file at the end.

Each part gets its own view axis (cached proposal), its own saved forbidden zones, the device's export scale for that part and a
different variant of the pattern (seed + position). A part with nothing decorable, or whose scale is outside the documented range, is
reported and skipped: nothing is corrected silently. Pure computation (no widget): safe in a worker thread.
"""
import json
from dataclasses import replace
from datetime import datetime
from pathlib import Path

from . import cache, deco
from .meshio import read_stl
from .placement import CustomizePage, zones_for


def run(parts, base_spec, out_root, ctx, progress=lambda i, n, msg: None, cancelled=lambda: False, vary=True):
    """parts: [(label, path)]. ctx: mirror_for(path) -> bool, scale_for(path) -> (percent|None, error|None), extra() -> dict.
    Returns [{"part", "status": ok|skipped|failed, "message", "folder"}]."""
    out_root = Path(out_root); out_root.mkdir(parents=True, exist_ok=True); results = []
    for i, (label, path) in enumerate(parts):
        if cancelled(): break
        progress(i, len(parts), label); r = {"part": label, "file": str(path), "status": "failed", "message": "", "folder": None}
        try:
            mirror = bool(ctx["mirror_for"](path)); scale, err = ctx["scale_for"](path)
            if err: r.update(status="skipped", message=err); results.append(r); continue
            tris = read_stl(path); tris = deco.mirror_tris(tris) if mirror else tris
            axis = CustomizePage._axis_for(path, mirror, tris)
            seed = base_spec.camo_seed + (i if vary else 0)
            spec = replace(base_spec, axis=axis, mirror_x=mirror, camo_seed=seed); zones = zones_for(path, axis, mirror)
            res = deco.apply_decoration(path, spec, zones)
            if res.errors: r.update(status="skipped", message="; ".join(res.errors)[:300]); results.append(r); continue
            folder = out_root / Path(path).stem[:60]; deco.export_result(res, path, spec, folder, zones, scale, ctx["extra"]())
            r.update(status="ok", message=f"variante {seed}, vue {axis}" + (f", échelle {scale:g} %" if scale else ""), folder=str(folder))
        except Exception as e: r.update(status="failed", message=str(e)[:300])
        results.append(r)
    progress(len(parts), len(parts), "")
    summary = {"generated": datetime.now().isoformat(timespec="seconds"), "status": "EXPERIMENTAL", "spec": deco._spec_dict(base_spec), "parts": results,
               "disclaimer": deco.DISCLAIMER}
    (out_root / "RECAP_camouflage.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    lines = ["CustomLab — camouflage sur plusieurs pièces (EXPÉRIMENTAL)", "", deco.DISCLAIMER, ""]
    for r in results: lines.append(f"[{r['status']}] {r['part']} — {r['message']}")
    lines += ["", "Chaque dossier contient le fichier 3MF prêt pour Bambu Studio, les STL séparés, une fiche JSON et l'attribution de la pièce d'origine.", "Aucune impression ni validation physique n'a été faite."]
    (out_root / "RECAP_camouflage.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return results
