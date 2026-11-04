"""Export every part of a device in one go at the device's export scale; the customised part keeps its decoration.

One folder per part inside out_root. Parts other than the customised one are exported as they are (mirrored for a left Kinetic, scaled),
with their licence file. A part whose scale is not computable or outside the documented range is reported and skipped: nothing is corrected.
Pure computation (no widget): safe in a worker thread.
"""
import hashlib
import json
from datetime import datetime
from pathlib import Path

from . import bambu3mf, deco, materials
from .meshio import is_watertight, read_stl, write_stl
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
            "source_license": lic, "mirrored_x": mirror, "scale_percent_applied": scale, "source_watertight": is_watertight(tris), "triangles": len(tris), **(extra or {}),
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
    out_root = Path(out_root); out_root.mkdir(parents=True, exist_ok=True); results = []; pieces = []
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
                pieces.append({"label": label, "path": path, "parts": res.info.get("export_parts") or []})
            else:
                f = _plain(path, folder, mirror, scale, ctx["extra"]()); txt += ", non décorée"
                pieces.append({"label": label, "path": path, "parts": [{"name": Path(f).stem, "triangles": read_stl(f), "extruder": 1, "role": "base"}]})
            r.update(status="ok", message=txt, folder=str(folder))
        except Exception as e: r.update(status="failed", message=str(e)[:300])
        results.append(r)
    if ctx.get("printer") and pieces and not cancelled():
        try: results.append(device_3mf(pieces, out_root, ctx))
        except Exception as e: results.append({"part": "3MF de l'appareil complet", "kind": "device", "file": "", "status": "failed", "message": str(e)[:300], "folder": None})
    progress(len(parts), len(parts), "")
    (out_root / "RECAP_export.json").write_text(json.dumps({"generated": datetime.now().isoformat(timespec="seconds"), "parts": results}, indent=2, ensure_ascii=False), encoding="utf-8")
    lines = ["CustomLab — export de toutes les pièces", ""] + [f"[{r['status']}] {r['part']} — {r['message']}" for r in results]
    lines += ["", "Aucune impression ni validation physique n'a été faite."]
    (out_root / "RECAP_export.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return results


def choice_for(ctx, path):
    """(material, colour) chosen for a part: ctx["materials"][resolved path], else the suggestion from its file name."""
    m = (ctx.get("materials") or {}).get(str(Path(path).resolve()))
    if m: return m
    mat = materials.suggest_material(Path(path).name); return mat, materials.DEFAULT_COLOUR[mat]


def device_3mf(pieces, out_root, ctx):
    """Every exported part on Bambu plate(s), each with the filament of its material + colour; the motif colours of the decorated part
    are extra filaments of that part's material. Refuses (status "skipped") when the printer cannot hold the filaments."""
    lang = ctx.get("lang", "fr"); printer = ctx["printer"]; items, chosen = [], []
    for pc in pieces:
        mat, col = choice_for(ctx, pc["path"])
        motif = [prt.get("colour") or ("#FFFFFF" if materials.colour_hex(col) == "#161616" else "#161616") for prt in pc["parts"] if prt.get("role") == "motif"]
        items.append({"label": pc["label"], "material": mat, "colour": col, "motif_colours": motif}); chosen.append((mat, col, motif))
    pl = materials.plan(items, printer, lang); r = {"part": "3MF de l'appareil complet", "kind": "device", "file": "", "status": "skipped", "message": "", "folder": str(out_root)}
    if pl.errors: r["message"] = " ".join(pl.errors); return r
    objects = []
    for pc, (mat, col, motif) in zip(pieces, chosen):
        parts, k = [], 0
        for prt in pc["parts"]:
            if prt.get("role") == "motif": ext = pl.index(mat, motif[k]); k += 1
            else: ext = pl.index(mat, col)
            parts.append({"name": prt["name"], "triangles": prt["triangles"], "extruder": ext})
        objects.append({"name": pc["label"].split(" — ")[0][:60], "parts": parts})
    bed = materials.PRINTERS[printer]["bed"]; plates, too_big = bambu3mf.pack(objects, bed)
    files = []; types = [(materials.MATERIALS[m]["type"], c) for m, c in pl.filaments]
    for i, placed in enumerate(plates, start=1):
        fn = out_root / ("APPAREIL_Bambu_pret.3mf" if len(plates) == 1 else f"APPAREIL_Bambu_pret_plateau{i}.3mf")
        bambu3mf.write_bambu_plate(fn, placed, types, title="CustomLab"); files.append(fn)
    multi_nozzle = materials.PRINTERS[printer].get("multi_nozzle", False)
    body = {pl.index(m, c) for m, c, mo in chosen}; detail = [n for n in range(1, len(pl.filaments) + 1) if n not in body]   # used only by motif pieces
    lines = ["CustomLab — appareil complet, prêt pour Bambu Studio (EXPÉRIMENTAL)", "",
             f"Imprimante choisie : {materials.PRINTERS[printer]['fr']}", "", "Filaments du projet (à charger dans cet ordre) :"]
    for n, (m, c) in enumerate(pl.filaments, start=1):
        who = [it["label"].split(" — ")[0] for it, (mm, cc, mo) in zip(items, chosen) if (mm, materials.colour_hex(cc)) == (m, c) or (mm == m and c in [materials.colour_hex(x) for x in mo])]
        tip = " — buse 0,2 mm conseillée (détails du motif)" if (multi_nozzle and n in detail) else ""
        lines.append(f"  Filament {n} : {m} {materials.colour_name(c)} ({c}) — {', '.join(who)}{tip}")
    if detail and multi_nozzle:
        lines += ["", "Buses : 0,4 mm pour les pièces, 0,2 mm pour les filaments du motif (texte, logo) si vous voulez des détails plus fins.",
                  "Ce choix se fait dans Bambu Studio (outil par filament) : CustomLab ne l'écrit pas dans le fichier (format non vérifié)."]
    elif detail:
        lines += ["", "Cette imprimante n'a qu'une buse : la même (0,4 mm en général) sert aux pièces et aux détails du motif."]
    lines += ["", "Fichiers : " + ", ".join(f.name for f in files)]
    if too_big: lines.append("Pièces trop grandes pour le plateau (non incluses, imprimez-les à part) : " + ", ".join(too_big))
    lines += ["", "Dans Bambu Studio : vérifiez que chaque filament du projet a la bonne matière (préréglage) et la bonne couleur,",
              "puis associez-le à la bonne bobine avant de trancher. La matière est déclarée dans le fichier, mais cette déclaration",
              "n'a pas encore été vérifiée dans Bambu Studio.", ""] + [f"Attention : {w}" for w in pl.warnings]
    lines += ["", "Matières proposées d'après le nom des fichiers ou choisies à la main : à vérifier dans le manuel de l'appareil.",
              "Aucune impression ni validation physique n'a été faite."]
    (out_root / "APPAREIL_LISEZ-MOI_Bambu.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    msg = f"{len(files)} plateau(x), {len(pl.filaments)} filament(s)" + (f" ; trop grandes : {', '.join(too_big)}" if too_big else "") + ("".join(" ; " + w for w in pl.warnings) if pl.warnings else "")
    r.update(status="ok", message=msg, file=str(files[0]), filaments=[{"filament": n, "material": m, "colour": c, "detail_nozzle_mm": 0.2 if (multi_nozzle and n in detail) else None}
                                                              for n, (m, c) in enumerate(pl.filaments, start=1)])
    return r
