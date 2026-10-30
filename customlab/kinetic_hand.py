"""Kinetic Hand sizing — Free 3D Hands "Assembly Manual - Kinetic Hand", Appendix 1 "Measurement and Scaling Guide" (M1-M25)
and Appendix 2 "3D Printing Guide" (P1-P20). Source file supplied locally by the user; NOT redistributed.

Method (basic scaling, "recommended" by the manual):
  1. affected-hand wrist width + 3 mm of padding -> pick the CLOSEST wrist-width value of the Hand Scaling Chart -> uniform scale (%).
  2. at that scale: free space in the palm = design palm length - measured palm length of the affected hand
     -> pick the closest soft Insert (A-E) for that scale.
Advanced scaling (per-axis, XY from the wrist, Z from the sound hand length) is only COMPUTED for information: it needs the parts in CAD
orientation (workshop .fpp file), warns that it "may affect Kinetic Hand function", and is never applied by CustomLab.
Documented limits: parts are supplied at 100 %; chart 50-100 % in steps of 2.5 %; printing guide: "can be scaled down to 55 %".
A test palm must be printed before giving a hand to a recipient (manual P20).
"""
from dataclasses import dataclass, field

PADDING_MM = 3.0
SCALE_MIN_CHART, SCALE_MAX, SCALE_MIN_RECOMMENDED = 50.0, 100.0, 55.0
TOLERANCE_MM = 1.0           # a measurement further than this outside the chart extremes is refused (the chart cannot represent it)
COLUMNS = ("palm_length", "wrist_width", "forearm_width", "max_palm_width", "overall_hand_length", "dist_max_palm_width")

# Hand Scaling Chart (manual page M17): scale % -> design dimensions (mm) of the Kinetic Hand at that scale
_ROWS = """50 50 35 37 46 108 22
52.5 52 37 39 48 114 24
55 55 39 41 50 119 25
57.5 57 41 43 53 125 26
60 60 42 45 55 130 27
62.5 62 44 47 57 135 28
65 65 46 49 60 141 29
67.5 67 48 51 62 146 30
70 70 50 52 64 152 31
72.5 72 51 54 66 157 33
75 75 53 56 69 162 34
77.5 77 55 58 71 168 35
80 80 57 60 73 173 36
82.5 82 58 62 76 179 37
85 85 60 64 78 184 38
87.5 87 62 66 80 190 39
90 90 64 67 82 195 40
92.5 92 66 69 85 200 42
95 95 67 71 87 206 43
97.5 97 69 73 89 211 44
100 100 71 75 92 217 45"""
# Soft Inserts A-E, thickness (mm) at each scale (manual page M17, second table), same row order
_INSERTS = """8 12 17 21 25
9 13 17 22 26
9 14 18 23 27
10 14 19 24 29
10 15 20 25 30
10 16 21 26 31
11 16 22 27 32
11 17 22 28 34
12 17 23 29 35
12 18 24 30 36
12 19 25 31 37
13 19 26 32 39
13 20 27 33 40
14 21 27 34 41
14 21 28 35 42
15 22 29 36 44
15 22 30 37 45
15 23 31 39 46
16 24 32 40 47
16 24 32 41 49
17 25 33 42 50"""
CHART = {}
for r, i in zip(_ROWS.splitlines(), _INSERTS.splitlines()):
    v = [float(x) for x in r.split()]
    CHART[v[0]] = {**dict(zip(COLUMNS, v[1:])), "inserts": dict(zip("ABCDE", [int(x) for x in i.split()]))}
SCALES = sorted(CHART)


class OutOfRange(ValueError):
    pass


def closest_scale(column, value_mm):
    """Chart row whose `column` is closest to value_mm (ties -> the larger scale, i.e. more room)."""
    return min(SCALES, key=lambda s: (abs(CHART[s][column] - value_mm), -s))


def closest_insert(scale, space_mm):
    ins = CHART[scale]["inserts"]; return min(ins, key=lambda k: (abs(ins[k] - space_mm), ins[k]))


@dataclass
class KineticResult:
    scale_percent: float
    padded_wrist_mm: float
    insert: str
    insert_mm: int
    space_mm: float
    design: dict                          # chart row at the chosen scale
    warnings: list = field(default_factory=list)
    advanced: dict = field(default_factory=dict)    # information only (never applied)


def compute(wrist_mm, palm_length_mm, max_palm_width_mm=0.0, sound_hand_length_mm=0.0, padding_mm=PADDING_MM) -> KineticResult:
    for n, v in (("wrist_mm", wrist_mm), ("palm_length_mm", palm_length_mm)):
        if isinstance(v, bool) or not isinstance(v, (int, float)) or v != v or v <= 0: raise ValueError(f"{n}: a positive number (mm) is required")
    padded = wrist_mm + padding_mm
    lo, hi = CHART[SCALES[0]]["wrist_width"], CHART[SCALES[-1]]["wrist_width"]
    if padded < lo - TOLERANCE_MM or padded > hi + TOLERANCE_MM:
        raise OutOfRange(f"Wrist width {wrist_mm:g} mm + {padding_mm:g} mm of padding = {padded:g} mm is outside the Hand Scaling Chart "
                         f"({lo:g}-{hi:g} mm, scales {SCALES[0]:g}-{SCALES[-1]:g} %). Check the measurement; nothing was adjusted.")
    s = closest_scale("wrist_width", padded); row = CHART[s]; w = []
    if s < SCALE_MIN_RECOMMENDED:
        w.append(f"Scale {s:g} % is below the 55 % that the printing guide gives as the minimum for a small child's hand (the chart goes down to 50 %).")
    space = row["palm_length"] - palm_length_mm
    ins = closest_insert(s, space); ins_mm = row["inserts"][ins]
    if space < 0: w.append(f"The measured palm length ({palm_length_mm:g} mm) is longer than the design palm at {s:g} % ({row['palm_length']:g} mm): the chosen insert cannot fill a negative space; print a test palm and consider a palm variant.")
    elif abs(ins_mm - space) > 4: w.append(f"No insert fits the {space:g} mm of free palm space well (closest: insert {ins} = {ins_mm} mm).")
    if max_palm_width_mm and max_palm_width_mm + padding_mm > row["max_palm_width"] + 1:
        w.append(f"The measured maximum palm width + padding ({max_palm_width_mm + padding_mm:g} mm) exceeds the design at {s:g} % ({row['max_palm_width']:g} mm).")
    w.append("Print a test palm and check the fit before assembling a hand for a recipient (manual, test palm page).")
    adv = {}
    if sound_hand_length_mm and sound_hand_length_mm > 0:
        sz = closest_scale("overall_hand_length", sound_hand_length_mm); rz = CHART[sz]
        adv = {"scale_xy": s, "scale_z": sz, "overall_hand_length_basic_mm": row["overall_hand_length"], "overall_hand_length_advanced_mm": rz["overall_hand_length"],
               "insert": closest_insert(sz, rz["palm_length"] - palm_length_mm), "applied": False,
               "note": "Per-axis scaling matches the sound hand length but 'may affect Kinetic Hand function' (manual) and needs the parts in CAD orientation: shown for information, not applied."}
        w.append(f"Basic scaling gives an overall hand length of {row['overall_hand_length']:g} mm, {row['overall_hand_length'] - sound_hand_length_mm:+g} mm from the sound hand ({sound_hand_length_mm:g} mm).")
    return KineticResult(s, padded, ins, ins_mm, space, dict(row), w, adv)
