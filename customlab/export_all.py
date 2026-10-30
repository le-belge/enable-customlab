"""Export every part of a device in one go at the device's export scale; the customised part keeps its decoration.

One folder per part inside out_root. Parts other than the customised one are exported as they are (mirrored for a left Kinetic, scaled),
with their licence file. A part whose scale is not computable or outside the documented range is reported and skipped: nothing is corrected.
Pure computation (no widget): safe in a worker thread.
"""
import hashlib
import json
from datetime import datetime
from pathlib import Path

from . import deco
from .meshio import read_stl, write_stl
from .placement import zones_for


def _plain(path, folder, mirror, scale, extra):
    """Unmodified part, mirrored if asked, uniformly scaled; STL + JSON sheet + attribution."""
    src = Path(path).resolve(); folder = Path(folder).resolve()
    if folder == src.parent: raise deco.DecoError("Le dossier d'export ne peut pas être celui de l'original.")
    folder.mkdir(parents=True, exist_ok=True)
    tris = read_stl(src); tris = deco.mirror_tris(tris) if mirror else list(tris)
    if scale not in (None, 100, 100.0): k = scale / 100.0; tris = [tuple(tuple(c * k for c in p) for p in t) for t in tris]
    name = f"{src.stem[:40]}" + (f"_{scale:g}pct" if scale not in (None, 100, 100.0) else "") + ("_miroir" if mirror else "") + ".stl"
    write_stl(folder / name, tris); lic = deco.read_license_info(src)
    side = {"generated": datetime.now().isoformat(timespec="seconds"), "status": "pièce non décorée", "source_file": str(src), "source_sha256": hashlib.sha256(src.read_bytes()).hexdigest(),
            "source_license": lic, "mirrored_x": mirror, "scale_percent_applied": scale, "triangles": len(tris), **(extra or {}),
            "disclaimer": "Aucune impression ni validation physique n'a été faite pour cette pièce."}
    (folder / (Path(name).stem + ".json")).write_text(json.dumps(side, indent=2, ensure_ascii=False), encoding="utf-8")
    lines = ["Pièce dérivée (mise à l'échelle/miroir) — voir le fichier JSON associé."]
    if lic.get("known"):
        lines += [f"Source : {lic['title']} par {lic['author']}", f"Licence de la source : {lic['license']} {lic.get('license_url') or ''}", f"Dérivé de : {lic.get('derived_from')}"]
        if lic["non_commercial"]: lines.append("USAGE NON COMMERCIAL UNIQUEMENT. Ne pas redistribuer sans respecter la licence (attribution).")
        if lic.get("share_alike"): lines.append("PARTAGE DANS LES MÊMES CONDITIONS : cette pièce dérivée ne peut être partagée que sous la même licence que la source.")
    else: lines.append("Provenance/licence du fichier source INCONNUES : ne pas redistribuer.")
    (folder / (Path(name).stem + "_ATTRIBUTION.txt")).write_text("\n".join(lines) + "\n", encoding="utf-8")
    return folder / name


def run(parts, decorated, out_root, ctx, progress=lambda i, n, msg: None, cancelled=lambda: False):
    """parts: [(label, path)]. decorated: None or (path, spec, zones) for the customised part. ctx: mirror_for(path), scale_for(path) -> (percent|None, error|None), extra() -> dict.
    Returns [{"part", "status": ok|skipped|failed, "message", "folder"}]."""
    out_root = Path(out_root); out_root.mkdir(parents=True, exist_ok=True); results = []
    dec_path = Path(decorated[0]).resolve() if decorated else None
    for i, (label, path) in enumerate(parts):
        if cancelled(): break
        progress(i, len(parts), label); r = {"part": label, "file": str(path), "status": "failed", "message": "", "folder": None}
        try:
            mirror = bool(ctx["mirror_for"](path)); scale, err = ctx["scale_for"](path)
            if err: r.update(status="skipped", message=err); results.append(r); continue
            folder = out_root / Path(path).stem[:60]; txt = f"échelle {scale:g} %" if scale else "échelle 100 %"
            if dec_path is not None and Path(path).resolve() == dec_path:
                _, spec, zones = decorated; res = deco.apply_decoration(path, spec, zones)
                if res.errors: r.update(status="skipped", message="décoration impossible : " + "; ".join(res.errors)[:250]); results.append(r); continue
                deco.export_result(res, path, spec, folder, zones, scale, ctx["extra"]()); txt += ", décorée"
            else: _plain(path, folder, mirror, scale, ctx["extra"]()); txt += ", non décorée"
            r.update(status="ok", message=txt, folder=str(folder))
        except Exception as e: r.update(status="failed", message=str(e)[:300])
        results.append(r)
    progress(len(parts), len(parts), "")
    (out_root / "RECAP_export.json").write_text(json.dumps({"generated": datetime.now().isoformat(timespec="seconds"), "parts": results}, indent=2, ensure_ascii=False), encoding="utf-8")
    lines = ["CustomLab — export de toutes les pièces", ""] + [f"[{r['status']}] {r['part']} — {r['message']}" for r in results]
    lines += ["", "Aucune impression ni validation physique n'a été faite."]
    (out_root / "RECAP_export.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return results
