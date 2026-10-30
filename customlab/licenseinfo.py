"""Detect the licence/provenance that ships next to a user-provided STL (LICENSE.txt / README.txt).

The licence is a property of each source file set, never of the device: it is read per file and
copied into the export sidecar. Unknown provenance is reported as unknown, not guessed.
"""
import re
from pathlib import Path

_TITLE = re.compile(r"^(?P<title>.+?) by (?P<author>.+?) is licensed under the (?P<lic>.+?) license\.?\s*$", re.I)
_URL = re.compile(r"https?://creativecommons\.org/licenses/[\w\-./]+", re.I)
_ORIG = re.compile(r"Customized version of (https?://\S+)", re.I)
_TV_LIC = re.compile(r"created by Thingiverse user (?P<author>.+?), and is licensed under (?P<lic>.+?)\s*$", re.I)
_TV_TITLE = re.compile(r"^(?P<title>.+?) by (?P<author>.+?) on Thingiverse", re.I)


def read_license_info(stl_path):
    p = Path(stl_path).resolve()
    for d in [p.parent, *list(p.parents)[:6]]:        # archives nest parts in sub-folders (e.g. Individual stls/Palm variants)
        readme = d / "README.txt"
        if readme.is_file() and (d / "LICENSE.txt").is_file():
            text = readme.read_text(encoding="utf-8", errors="replace")
            info = {"known": True, "folder": str(d), "title": None, "author": None, "license": None,
                    "license_url": None, "derived_from": None, "non_commercial": False, "share_alike": False}
            for line in text.splitlines():
                m = _TITLE.match(line.strip())
                if m and not info["title"]:
                    info.update(title=m["title"], author=m["author"], license=m["lic"])
                u = _URL.search(line)
                if u and not info["license_url"]:
                    info["license_url"] = u.group(0)
                o = _ORIG.search(line)
                if o: info["derived_from"] = o.group(1)
            if not info["license"]:                                   # Thingiverse archive: LICENSE.txt gives author + licence, README the title
                m = _TV_LIC.search((d / "LICENSE.txt").read_text(encoding="utf-8", errors="replace"))
                if m:
                    info.update(author=m["author"], license=m["lic"].rstrip("."))
                    for line in text.splitlines():
                        t = _TV_TITLE.match(line.strip())
                        if t: info["title"] = t["title"]; break
            if not info["license"]:
                break
            info["non_commercial"] = bool(re.search(r"non-?commercial", info["license"] + (info["license_url"] or ""), re.I)
                                          or "/by-nc" in (info["license_url"] or ""))
            info["share_alike"] = bool(re.search(r"share.?alike", info["license"], re.I) or "-sa/" in (info["license_url"] or ""))
            return info
    return {"known": False, "non_commercial": None, "share_alike": None}
