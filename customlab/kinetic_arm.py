"""Kinetic Arm sizing — Free 3D Hands "Kinetic Arm Assembly Manual" (NIH 3D 3DPX-022894 v8, CC BY-NC-SA).
Source file downloaded from the entry by the user's request; NOT redistributed (sources/kinetic_arm/manual/).

Method (manual "Scaling Steps", pages 28-33, charts in Appendix B1-B4; chart values read from the page images):
  3. hand length (middle fingertip -> wrist)  -> Lower Components scale: row of the chart, round DOWN to the nearest chart value;
  4. residual-limb elbow width, same row     -> Forearm Type A-F: round UP to the nearest value of the row;
  5. (Lower scale, Type)                     -> Upper Components scale (chart B2, 1 decimal);
  6. residual-limb length, same row          -> Forearm Insert A-Q: round UP to the nearest value of the row;
  7. (Insert, Type)                          -> Tongue 1-4;   8. (Insert, Type) -> Neoprene Liner Set 1-12.
Pre-scaled parts (never scaled in the slicer): Palm and Locking Mechanism (Lower scale), Tensioners (Upper scale, "closest value").
Other Lower parts use the Lower scale, other Upper parts the Upper scale. All files are right-hand; a left arm mirrors some parts.
Documented limits: tested 50-100 % (50 % recommended minimum); residual limb 15-70 % of the unaffected forearm.
A TEST ARM (upper arm + elbow hinges + forearm) must be printed and evaluated before the real arm (manual, Scaling Validation).
Values outside the charts are refused, never clamped.
"""
from dataclasses import dataclass, field

TESTED_SCALE = (50.0, 100.0)
RESIDUAL_RATIO = (0.15, 0.70)
TYPES = "ABCDEF"
INSERTS = "ABCDEFGHIJKLMNOPQ"

# Appendix B1: scale %, palm length (wrist -> fingertip) mm, elbow width mm of Types A..F
_B1 = """100 237 98 102 107 112 117 122
97.5 231 95 99 104 109 114 119
95 225 93 97 102 107 111 116
92.5 219 91 94 99 104 109 113
90 213 88 92 96 101 106 110
87.5 207 86 89 94 98 103 107
85 201 83 87 91 95 100 104
82.5 196 81 84 88 93 97 101
80 190 78 82 86 90 94 98
77.5 184 76 79 83 87 91 95
75 178 73 77 80 84 88 92
72.5 172 71 74 78 81 85 89
70 166 69 71 75 79 82 86
67.5 160 66 69 72 76 79 83
65 154 64 66 70 73 76 80
62.5 148 61 64 67 70 73 77
60 142 59 61 64 67 70 73
57.5 136 56 59 62 65 67 70
55 130 54 56 59 62 65 67
52.5 124 51 54 56 59 62 64
50 119 49 51 54 56 59 61"""
# Appendix B2: Upper Components scale % for Types A..F, same row order (lower scale 100 -> 50)
_B2 = """95.0 100.0 105.0 110.0 115.0 120.0
92.6 97.5 102.4 107.3 112.1 117.0
90.3 95.0 99.8 104.5 109.3 114.0
87.9 92.5 97.1 101.8 106.4 111.0
85.5 90.0 94.5 99.0 103.5 108.0
83.1 87.5 91.9 96.3 100.6 105.0
80.8 85.0 89.3 93.5 97.8 102.0
78.4 82.5 86.6 90.8 94.9 99.0
76.0 80.0 84.0 88.0 92.0 96.0
73.6 77.5 81.4 85.3 89.1 93.0
71.3 75.0 78.8 82.5 86.3 90.0
68.9 72.5 76.1 79.8 83.4 87.0
66.5 70.0 73.5 77.0 80.5 84.0
64.1 67.5 70.9 74.3 77.6 81.0
61.8 65.0 68.3 71.5 74.8 78.0
59.4 62.5 65.6 68.8 71.9 75.0
57.0 60.0 63.0 66.0 69.0 72.0
54.6 57.5 60.4 63.3 66.1 69.0
52.3 55.0 57.8 60.5 63.3 66.0
49.9 52.5 55.1 57.8 60.4 63.0
47.5 50.0 52.5 55.0 57.5 60.0"""
# Appendix B3: residual-limb length (mm) of Inserts A..Q, same row order
_B3 = """90 100 110 120 130 140 150 160 170 180 190 200 210 220 230 240 250
88 98 107 117 127 137 146 156 166 176 185 195 205 215 224 234 244
86 95 105 114 124 133 143 152 162 171 181 190 200 209 219 228 238
83 93 102 111 120 130 139 148 157 167 176 185 194 204 213 222 231
81 90 99 108 117 126 135 144 153 162 171 180 189 198 207 216 225
79 88 96 105 114 123 131 140 149 158 166 175 184 193 201 210 219
77 85 94 102 111 119 128 136 145 153 162 170 179 187 196 204 213
74 83 91 99 107 116 124 132 140 149 157 165 173 182 190 198 206
72 80 88 96 104 112 120 128 136 144 152 160 168 176 184 192 200
70 78 85 93 101 109 116 124 132 140 147 155 163 171 178 186 194
68 75 83 90 98 105 113 120 128 135 143 150 158 165 173 180 188
65 73 80 87 94 102 109 116 123 131 138 145 152 160 167 174 181
63 70 77 84 91 98 105 112 119 126 133 140 147 154 161 168 175
61 68 74 81 88 95 101 108 115 122 128 135 142 149 155 162 169
59 65 72 78 85 91 98 104 111 117 124 130 137 143 150 156 163
56 63 69 75 81 88 94 100 106 113 119 125 131 138 144 150 156
54 60 66 72 78 84 90 96 102 108 114 120 126 132 138 144 150
52 58 63 69 75 81 86 92 98 104 109 115 121 127 132 138 144
50 55 61 66 72 77 83 88 94 99 105 110 116 121 127 132 138
47 53 58 63 68 74 79 84 89 95 100 105 110 116 121 126 131
45 50 55 60 65 70 75 80 85 90 95 100 105 110 115 120 125"""
# Appendix B4
TONGUE = {"short": {"ABC": 2, "DEF": 4}, "long": {"ABC": 1, "DEF": 3}}          # short = Insert A-H, long = Insert I-Q
LINER = {"short": {t: 2 * (i + 1) for i, t in enumerate(TYPES)}, "long": {t: 2 * i + 1 for i, t in enumerate(TYPES)}}

CHART = {}
for _a, _b, _c in zip(_B1.splitlines(), _B2.splitlines(), _B3.splitlines()):
    _v = [float(x) for x in _a.split()]
    CHART[_v[0]] = {"hand_length": _v[1], "elbow": dict(zip(TYPES, _v[2:])), "upper": dict(zip(TYPES, [float(x) for x in _b.split()])),
                    "insert_len": dict(zip(INSERTS, [float(x) for x in _c.split()]))}
SCALES = sorted(CHART, reverse=True)                           # 100 -> 50
PRESCALED = tuple(50 + 2.5 * i for i in range(21))              # Palm / LockMech files: 50 ... 100
TENSIONERS = tuple(47.5 + 2.5 * i for i in range(30))           # Tensioner files: 47.5 ... 120


class OutOfRange(ValueError):
    pass


def _pos(n, v):
    if isinstance(v, bool) or not isinstance(v, (int, float)) or v != v or v <= 0:
        raise ValueError(f"{n}: a positive number (mm) is required")


def nearest_file_scale(available, value):
    """Closest provided pre-scaled file (tie -> the larger)."""
    return min(available, key=lambda s: (abs(s - value), -s))


@dataclass
class ArmResult:
    lower_scale: float
    forearm_type: str
    upper_scale: float
    insert: str
    tongue: int
    liner_set: int
    palm_scale: float
    lockmech_scale: float
    tensioner_scale: float
    design: dict
    warnings: list = field(default_factory=list)


def compute(hand_length_mm, elbow_width_mm, residual_length_mm, sound_forearm_mm=0.0) -> ArmResult:
    for n, v in (("hand_length_mm", hand_length_mm), ("elbow_width_mm", elbow_width_mm), ("residual_length_mm", residual_length_mm)):
        _pos(n, v)
    lo, hi = CHART[SCALES[-1]]["hand_length"], CHART[SCALES[0]]["hand_length"]
    if not lo <= hand_length_mm <= hi:
        raise OutOfRange(f"Hand length {hand_length_mm:g} mm is outside the Lower Components chart ({lo:g}-{hi:g} mm, scales 50-100 %). Nothing was adjusted.")
    lower = next(s for s in SCALES if CHART[s]["hand_length"] <= hand_length_mm)               # step 3: round DOWN
    row = CHART[lower]
    ftype = next((t for t in TYPES if row["elbow"][t] >= elbow_width_mm), None)                 # step 4: round UP
    if ftype is None:
        raise OutOfRange(f"Elbow width {elbow_width_mm:g} mm exceeds Type F ({row['elbow']['F']:g} mm) at {lower:g} %: no forearm variant fits. Nothing was adjusted.")
    upper = row["upper"][ftype]                                                                 # step 5
    ins = next((k for k in INSERTS if row["insert_len"][k] >= residual_length_mm), None)        # step 6: round UP
    if ins is None:
        raise OutOfRange(f"Residual limb length {residual_length_mm:g} mm exceeds Insert Q ({row['insert_len']['Q']:g} mm) at {lower:g} %. Nothing was adjusted.")
    kind = "short" if ins <= "H" else "long"
    tongue = next(v for k, v in TONGUE[kind].items() if ftype in k)                             # step 7
    liner = LINER[kind][ftype]                                                                  # step 8
    w = []
    if lower < 55: w.append(f"Lower scale {lower:g} %: the manual recommends 50 % as the absolute minimum (tested 50-100 %).")
    if sound_forearm_mm:
        r = residual_length_mm / sound_forearm_mm
        if not RESIDUAL_RATIO[0] <= r <= RESIDUAL_RATIO[1]:
            w.append(f"Residual limb = {r*100:.1f} % of the unaffected forearm, outside the documented functional range 15-70 %: the arm may not be operable.")
    tens = nearest_file_scale(TENSIONERS, upper)
    if abs(tens - upper) > 1e-9:
        w.append(f"Upper scale {upper:g} %: use the pre-scaled Tensioners file {tens:g} % (closest provided; never scale them in the slicer). "
                 "The manual's own example (81.4 % -> 'Tensioners 80') predates the 2.5 % file steps: check.")
    palm = nearest_file_scale(PRESCALED, lower)
    w.append("Palm, Locking Mechanism and Tensioners are chosen as pre-scaled files, not scaled in the slicer. Print a TEST ARM (upper arm, elbow hinges, forearm) and evaluate the fit before the real arm; "
             "a change of scale must be reviewed by an allied-health practitioner (manual).")
    return ArmResult(lower, ftype, upper, ins, tongue, liner, palm, palm, tens,
                     {"hand_length": row["hand_length"], "elbow_width": row["elbow"][ftype], "insert_length": row["insert_len"][ins]}, w)


def residual_limb_check(residual_mm: float, sound_forearm_mm: float) -> dict:
    if residual_mm <= 0 or sound_forearm_mm <= 0:
        raise ValueError("lengths must be > 0")
    r = residual_mm / sound_forearm_mm
    lo, hi = RESIDUAL_RATIO
    return {"ratio": r, "ok": lo <= r <= hi,
            "message": f"Residual limb = {r*100:.1f} % of sound forearm (documented suitable range {lo*100:.0f}-{hi*100:.0f} %)."}


def scale_check(percent: float) -> dict:
    lo, hi = TESTED_SCALE
    ok = lo <= percent <= hi
    return {"ok": ok, "message": f"{percent:g} % is " + ("inside" if ok else "OUTSIDE") +
            f" the tested range {lo:g}-{hi:g} % (50 % is the recommended minimum)."}


# --- per-file rules (manual pages 21-23: Upper / Lower components, pre-scaled parts, parts mirrored for a left arm) -----------------
_UPPER = ("elbowhinges", "uparm")                       # ElbowHinges, UpArm, UpArmCov
_PRESCALED = {"palm": "lower", "lockmech": "lower", "tensioners": "upper"}


def part_info(filename, derived):
    """Rules for one STL of the entry. `derived` = ArmResult-like dict ('lower_scale', 'upper_scale', 'palm_scale', 'tensioner_scale').
    Returns dict(group, prescaled, scale_percent, note, mirror_left). Files named '...100' are the scalable masters (scale_percent
    to apply at export); pre-scaled files (Palm*, LockMech*, Tensioners*) are never scaled: the right file is a choice."""
    n = filename.lower().rsplit(".", 1)[0]
    for key, grp in _PRESCALED.items():
        if n.startswith(key):
            want = derived["palm_scale"] if grp == "lower" else derived["tensioner_scale"]
            digits = n[len(key):].replace("rh", "").strip("_")
            try: have = float(digits.replace("-", "."))
            except ValueError: have = None
            note = (f"Pre-scaled file ({have:g} %): matches the chosen scale." if have == want else
                    f"Pre-scaled file ({have:g} %) but the chart gives {want:g} %: choose the {key} file at {want:g} %.") if have is not None else "Pre-scaled file."
            return {"group": grp, "prescaled": True, "scale_percent": 100.0, "note": note, "mirror_left": "rh" in n}
    grp = "upper" if n.startswith(_UPPER) else "lower"
    return {"group": grp, "prescaled": False, "scale_percent": derived["upper_scale"] if grp == "upper" else derived["lower_scale"],
            "note": f"Scalable master (100 %): scaled to the {grp} components scale.", "mirror_left": "rh" in n}
