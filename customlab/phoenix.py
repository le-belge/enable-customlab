"""Phoenix / Raptor scaling — official e-NABLE France method.

Source: https://e-nable.fr/fr/fabrications/matching/mettre-a-lechelle/
    Coeff (%) = ((wrist_width + margin) / 43) * 100,  margin = 5 mm (recommended)
43 = space available for the wrist in the Phoenix hand at 100 %.
Documented range of the OpenSCAD scale parameter: 100-160 %.
Out-of-range values are NEVER clamped: they raise OutOfRange with an explanation.
"""
from dataclasses import dataclass

REFERENCE_MM = 43.0
DEFAULT_MARGIN_MM = 5.0
SCALE_MIN, SCALE_MAX = 100.0, 160.0


class OutOfRange(ValueError):
    pass


def scale_percent(wrist_mm: float, margin_mm: float = DEFAULT_MARGIN_MM) -> float:
    for n, v in (("wrist_mm", wrist_mm), ("margin_mm", margin_mm)):
        if isinstance(v, bool) or not isinstance(v, (int, float)) or v != v:
            raise ValueError(f"{n}: numeric value required")
    if wrist_mm <= 0 or margin_mm < 0:
        raise ValueError("wrist must be > 0 and margin >= 0")
    return (wrist_mm + margin_mm) / REFERENCE_MM * 100.0


def wrist_range_mm(margin_mm: float = DEFAULT_MARGIN_MM):
    """Wrist widths for which the formula lands inside the documented 100-160 % range."""
    return (SCALE_MIN / 100 * REFERENCE_MM - margin_mm, SCALE_MAX / 100 * REFERENCE_MM - margin_mm)


@dataclass
class PhoenixScale:
    wrist_mm: float
    margin_mm: float
    percent: float          # exact, unrounded
    percent_used: float     # rounded to 0.01 for OpenSCAD / slicer
    warnings: list


def compute(wrist_mm: float, margin_mm: float = DEFAULT_MARGIN_MM) -> PhoenixScale:
    pct = scale_percent(wrist_mm, margin_mm)
    lo, hi = wrist_range_mm(margin_mm)
    if not SCALE_MIN <= pct <= SCALE_MAX:
        side = "below 100 %: the Phoenix cannot be reduced" if pct < SCALE_MIN else "above 160 %: outside the documented range"
        raise OutOfRange(
            f"Scale {pct:.2f} % is {side}. With a {margin_mm:g} mm margin the usable wrist width is "
            f"{lo:.1f}-{hi:.1f} mm. Check the measurement, margin, or choose another device; nothing was adjusted.")
    w = []
    if pct - SCALE_MIN < 2 or SCALE_MAX - pct < 2:
        w.append("Scale close to the limit of the documented range.")
    if margin_mm != DEFAULT_MARGIN_MM:
        w.append(f"Margin {margin_mm:g} mm differs from the recommended 5 mm.")
    w.append("Print the verification jig (gabarit Phoenix) first and compare the scaled palm with the recipient's sound palm.")
    return PhoenixScale(wrist_mm, margin_mm, pct, round(pct, 2), w)
