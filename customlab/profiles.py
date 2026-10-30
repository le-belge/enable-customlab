"""Device profiles and the sizing engine.

Rule: never invent a parameter. Only inputs declared in a profile are accepted;
ranges are enforced only when the profile marks them as documented.
"""
import json
import math
from dataclasses import dataclass, field
from pathlib import Path

PROFILE_DIR = Path(__file__).parent / "profiles"


class SizingError(ValueError):
    pass


def load_profile(device_id: str) -> dict:
    p = PROFILE_DIR / f"{device_id}.json"
    if not p.is_file():
        raise SizingError(f"Unknown device: {device_id}")
    return json.loads(p.read_text(encoding="utf-8"))


def list_profiles() -> list:
    return [json.loads(p.read_text(encoding="utf-8")) for p in sorted(PROFILE_DIR.glob("*.json"))]


@dataclass
class SizingResult:
    device_id: str
    side: str
    part: str
    measurements: dict
    scad_defines: dict
    status: str
    warnings: list = field(default_factory=list)
    profile_version: str = ""
    derived: dict = field(default_factory=dict)   # values the official SCAD computes itself (e.g. HandPerc), shown for transparency


def compute_phoenix_sizing(side: str, part: str, wrist_mm: float, margin_mm: float = 5.0) -> SizingResult:
    """Official e-NABLE France wrist formula -> scale %, then the regular validated path."""
    from . import phoenix
    ps = phoenix.compute(wrist_mm, margin_mm)      # raises OutOfRange, never clamps
    r = compute_sizing("phoenix_hand", side, part, {"scale_percent": ps.percent_used})
    r.measurements = {"wrist_mm": wrist_mm, "margin_mm": margin_mm, "scale_percent": ps.percent_used}
    r.warnings = ps.warnings + r.warnings
    return r


def compute_kinetic_sizing(side: str, part: str, wrist_mm: float, palm_mm: float, max_palm_mm: float = 0.0, sound_len_mm: float = 0.0) -> SizingResult:
    """Kinetic Hand: Free 3D Hands Hand Scaling Chart (manual Appendix 1). Uniform scale + soft insert; advanced scaling is information only."""
    from . import kinetic_hand as K
    prof = load_profile("kinetic_hand")
    if side not in prof["sides"]: raise SizingError(f"Invalid side '{side}'")
    try: k = K.compute(wrist_mm, palm_mm, max_palm_mm or 0.0, sound_len_mm or 0.0)
    except (K.OutOfRange, ValueError) as e: raise SizingError(str(e))
    warnings = list(k.warnings)
    if prof["status"] != "verified": warnings.insert(0, "EXPERIMENTAL: dimensional compatibility not validated; no conformity claim")
    derived = {"scale_percent": k.scale_percent, "padded_wrist_mm": k.padded_wrist_mm, "insert": k.insert, "insert_mm": k.insert_mm, "space_mm": k.space_mm, "design": k.design, "advanced": k.advanced}
    meas = {"wrist_mm": wrist_mm, "palm_mm": palm_mm, "max_palm_mm": max_palm_mm or 0.0, "sound_len_mm": sound_len_mm or 0.0}
    return SizingResult("kinetic_hand", side, part or "", meas, {"scale_percent": k.scale_percent, "mirror_x": side == "left", "insert": k.insert}, prof["status"], warnings, prof["source"]["version"], derived)


def compute_kinetic_arm_sizing(side: str, hand_mm: float, elbow_mm: float, resid_mm: float, sound_mm: float = 0.0) -> SizingResult:
    """Kinetic Arm: Free 3D Hands manual, scaling steps 3-8 (Appendix B charts). Selects scales and pieces; never clamps."""
    from . import kinetic_arm as K
    prof = load_profile("kinetic_arm")
    if side not in prof["sides"]: raise SizingError(f"Invalid side '{side}'")
    try: k = K.compute(hand_mm, elbow_mm, resid_mm, sound_mm or 0.0)
    except (K.OutOfRange, ValueError) as e: raise SizingError(str(e))
    warnings = list(k.warnings)
    if prof["status"] != "verified": warnings.insert(0, "EXPERIMENTAL: dimensional compatibility not validated; no conformity claim")
    derived = {"lower_scale": k.lower_scale, "forearm_type": k.forearm_type, "upper_scale": k.upper_scale, "insert": k.insert, "tongue": k.tongue, "liner_set": k.liner_set,
               "palm_scale": k.palm_scale, "lockmech_scale": k.lockmech_scale, "tensioner_scale": k.tensioner_scale, "design": k.design}
    meas = {"hand_mm": hand_mm, "elbow_mm": elbow_mm, "resid_mm": resid_mm, "sound_mm": sound_mm or 0.0}
    return SizingResult("kinetic_arm", side, "", meas, {"lower_scale": k.lower_scale, "upper_scale": k.upper_scale, "mirror_x": side == "left"}, prof["status"], warnings, prof["source"]["version"], derived)


def compute_sizing(device_id: str, side: str, part: str, measurements: dict) -> SizingResult:
    prof = load_profile(device_id)
    if prof.get("method") == "kinetic_chart": raise SizingError("Kinetic Hand: use compute_kinetic_sizing (chart method)")
    if prof.get("method") == "kinetic_arm_chart": raise SizingError("Kinetic Arm: use compute_kinetic_arm_sizing (chart method)")
    if prof["status"] == "unavailable":
        raise SizingError(f"{prof['name']}: sizing unavailable ({prof['notes']})")
    if side not in prof["sides"]:
        raise SizingError(f"Invalid side '{side}'")
    if part not in prof["parts"]:
        raise SizingError(f"Invalid part '{part}' (allowed: {', '.join(prof['parts'])})")
    declared = {i["id"]: i for i in prof["inputs"]}
    unknown = set(measurements) - set(declared)
    if unknown:
        raise SizingError(f"Undeclared parameters: {sorted(unknown)}")
    missing = set(declared) - set(measurements)
    if missing:
        raise SizingError(f"Missing measurements: {sorted(missing)}")

    warnings = []
    defines = {}
    for pid, spec in declared.items():
        v = measurements[pid]
        if isinstance(v, bool) or not isinstance(v, (int, float)) or v != v:
            raise SizingError(f"{pid}: numeric value required")
        if v <= 0:
            raise SizingError(f"{pid}: must be > 0")
        if spec["documented_range"]:
            if not spec["min"] <= v <= spec["max"]:
                raise SizingError(f"{pid}={v}{spec['unit']} outside documented range {spec['min']}-{spec['max']}")
        else:
            warnings.append(f"{pid}: no documented valid range; value not validated")
        defines[spec["scad_param"]] = v
    sp = prof["scad_params_side"]
    defines[sp["param"]] = sp["values"][side]
    defines[prof["part_param"]] = part
    if not prof["label_mapping_confirmed"]:
        warnings.append("Measurement label mapping not confirmed by sources (see docs/AUDIT.md)")
    if prof["status"] != "verified":
        warnings.append("EXPERIMENTAL: dimensional compatibility not validated; no conformity claim")
    if prof.get("variants"):
        warnings.append("Licence depends on the file variant used (see profile variants / export sidecar)")
    elif not prof["license"]["verified"]:
        warnings.append("Licence not verified on the original source")
    derived = {}
    if device_id == "unlimbited_arm":                       # HandPerc = round(HandLen / 135 * 100) in the official SCAD (OpenSCAD round: half away from zero)
        derived["HandPerc"] = int(math.floor(measurements["HandLen"] / 135.0 * 100.0 + 0.5))
    return SizingResult(device_id, side, part, dict(measurements), defines, prof["status"],
                        warnings, prof["source"]["version"], derived)
