"""Materials and printers for multi-colour / multi-material exports.

A device is printed from several parts; each part gets a material (PLA, PETG, TPU...) and a colour. The decorated part also brings
the colours of its motif. `plan()` turns these choices into the list of filaments of the project (one per distinct material + colour)
and checks them against the chosen printer. Nothing here is validated by a print: materials are suggestions to check against the
device's manual (e.g. Kinetic Hand: hinges and palm cover in TPU), never a guarantee.
"""
import re
from dataclasses import dataclass, field

# Bambu Studio "filament_type" values; temperatures are only used for the compatibility warning (typical bed temperature ranges).
MATERIALS = {
    "PLA":     {"type": "PLA",  "flexible": False, "family": "PLA"},
    "PETG":    {"type": "PETG", "flexible": False, "family": "PETG"},
    "ASA":     {"type": "ASA",  "flexible": False, "family": "ASA"},
    "TPU 95A": {"type": "TPU",  "flexible": True,  "family": "TPU"},
    "TPU 85A": {"type": "TPU",  "flexible": True,  "family": "TPU"},
}
DEFAULT_MATERIAL = "PLA"

COLOURS = {   # name -> hex ; names in French and English
    "white":  ("Blanc", "White", "#FFFFFF"), "black": ("Noir", "Black", "#161616"), "grey": ("Gris", "Grey", "#8E9089"),
    "red":    ("Rouge", "Red", "#C12E1F"), "orange": ("Orange", "Orange", "#FF6A13"), "yellow": ("Jaune", "Yellow", "#F4EE2A"),
    "green":  ("Vert", "Green", "#00AE42"), "blue": ("Bleu", "Blue", "#0A2989"), "navy": ("Bleu marine", "Navy blue", "#13294B"),
    "midblue": ("Bleu moyen", "Medium blue", "#4A6FA5"), "skyblue": ("Bleu ciel", "Sky blue", "#56B7E6"),
    "purple": ("Violet", "Purple", "#5E43B7"), "pink": ("Rose", "Pink", "#F55A74"), "skin": ("Beige", "Beige", "#E8C9A8"),
}
DEFAULT_COLOUR = {"PLA": "white", "PETG": "white", "ASA": "white", "TPU 95A": "black", "TPU 85A": "black"}

# slots: filaments the printer can hold for one print. flex_slots: how many of them may be flexible (TPU).
PRINTERS = {
    "x1c_ams": {"fr": "Bambu X1C / P1S + 1 AMS (4 bobines + 1 externe)", "en": "Bambu X1C / P1S + 1 AMS (4 spools + 1 external)",
                "slots": 5, "flex_slots": 1, "bed": (256.0, 256.0),
                "note_fr": "Le TPU ne passe pas par l'AMS : une seule bobine souple possible, sur le support externe.",
                "note_en": "TPU does not go through the AMS: one flexible spool at most, on the external holder."},
    "h3c":     {"fr": "Bambu H3C (9 outils)", "en": "Bambu H3C (9 tools)",
                "slots": 9, "flex_slots": 9, "bed": (330.0, 320.0), "multi_nozzle": True,      # one nozzle diameter per tool (0.2 to 0.8 mm announced)
                "note_fr": "Caractéristiques annoncées par Bambu Lab (sortie le 3/11/2026), NON testées avec CustomLab.",
                "note_en": "Specifications announced by Bambu Lab (released 2026-11-03), NOT tested with CustomLab."},
    "other":   {"fr": "Autre imprimante (pas de vérification)", "en": "Other printer (no check)",
                "slots": None, "flex_slots": None, "bed": (256.0, 256.0), "note_fr": "", "note_en": ""},
}
DEFAULT_PRINTER = "x1c_ams"

_FLEX_NAME = re.compile(r"(?<![a-z])(tpu|flex|flexible|souple)(?![a-z])", re.I)


def suggest_material(name):
    """TPU 95A when the file name says so ("…TPU…", "flex", "souple"), else PLA. A suggestion only: check the device's manual."""
    return "TPU 95A" if _FLEX_NAME.search(re.sub(r"[_\-.]", " ", str(name))) else DEFAULT_MATERIAL


def colour_hex(c):
    """'red' -> '#C12E1F'; '#rrggbb' is returned upper-case."""
    if isinstance(c, str) and re.fullmatch(r"#[0-9a-fA-F]{6}", c): return c.upper()
    return COLOURS[c][2]


def colour_name(c, lang="fr"):
    """Palette name; a motif colour outside the palette gets the nearest one ("≈ Bleu") to help pick a spool."""
    h = colour_hex(c)
    for fr, en, x in COLOURS.values():
        if x == h: return fr if lang == "fr" else en
    rgb = lambda x: tuple(int(x[i:i + 2], 16) for i in (1, 3, 5))
    fr, en, _ = min(COLOURS.values(), key=lambda t: sum((a - b) ** 2 for a, b in zip(rgb(t[2]), rgb(h))))
    return "≈ " + (fr if lang == "fr" else en)


@dataclass
class Plan:
    filaments: list = field(default_factory=list)      # [(material, '#RRGGBB')], filament k+1 = filaments[k]
    errors: list = field(default_factory=list)
    warnings: list = field(default_factory=list)

    def index(self, material, colour):
        """1-based filament (extruder) number of a material + colour."""
        return self.filaments.index((material, colour_hex(colour))) + 1


def plan(items, printer=DEFAULT_PRINTER, lang="fr"):
    """items: [{"label", "material", "colour", "motif_colours": ['#..', ...]}] (motif colours use the part's material).
    Returns a Plan: distinct filaments in order of appearance, errors (the export must not go on) and warnings."""
    fr = lang == "fr"; p = PRINTERS.get(printer, PRINTERS["other"]); out = Plan()
    for it in items:
        mat = it.get("material") or DEFAULT_MATERIAL
        if mat not in MATERIALS: out.errors.append((f"Matière inconnue pour {it['label']} : {mat}" if fr else f"Unknown material for {it['label']}: {mat}")); continue
        for c in [it.get("colour") or DEFAULT_COLOUR[mat]] + list(it.get("motif_colours") or []):
            f = (mat, colour_hex(c))
            if f not in out.filaments: out.filaments.append(f)
    n = len(out.filaments); flex = [f for f in out.filaments if MATERIALS[f[0]]["flexible"]]
    if p["slots"] is not None and n > p["slots"]:
        out.errors.append(f"{n} filaments nécessaires, mais {p['fr']} n'en accepte que {p['slots']} dans une même impression. Réduisez les couleurs ou les matières, ou imprimez en plusieurs fois."
                          if fr else f"{n} filaments needed, but {p['en']} accepts only {p['slots']} in one print. Use fewer colours or materials, or print in several runs.")
    if p["flex_slots"] is not None and len(flex) > p["flex_slots"]:
        out.errors.append(f"{len(flex)} filaments souples (TPU) : {p['fr']} n'en accepte que {p['flex_slots']}. {p['note_fr']}"
                          if fr else f"{len(flex)} flexible filaments (TPU): {p['en']} accepts only {p['flex_slots']}. {p['note_en']}")
    families = {MATERIALS[f[0]]["family"] for f in out.filaments}
    rigid = families - {"TPU"}
    if len(rigid) > 1:
        out.warnings.append(f"Matières rigides différentes dans la même impression ({', '.join(sorted(rigid))}) : températures de plateau et adhérence entre elles à vérifier."
                            if fr else f"Different rigid materials in the same print ({', '.join(sorted(rigid))}): bed temperatures and adhesion between them to be checked.")
    if flex:
        out.warnings.append("Pièces en TPU : choisissez un préréglage de filament TPU dans Bambu Studio (impression lente) ; souplesse et tenue NON vérifiées."
                            if fr else "TPU parts: pick a TPU filament preset in Bambu Studio (slow printing); flexibility and strength NOT verified.")
    if p.get("note_fr") and printer == "h3c": out.warnings.append(p["note_fr"] if fr else p["note_en"])
    return out
