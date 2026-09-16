"""Raw downloads and their manifest.

Raw files are never overwritten (global rule 5): ``write_raw`` refuses an
existing path, and a re-fetch gets a new filename carrying the fetch date
(``raw_path``). Every write appends an entry to ``data/raw/manifest.json``.
``fetch_bytes`` is the only place in the package that calls ``requests``.

Rulings from issue #4: ``latest_raw`` globs ``name_*.*`` and refuses a mix
of extensions; "newest" is the ``YYYYMMDD`` in the filename, not mtime; the
manifest ``name`` is the path stem with its ``_YYYYMMDD`` suffix removed,
the inverse of ``raw_path``.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import re
from pathlib import Path

import requests

RAW_ROOT = Path("data/raw")
MANIFEST = RAW_ROOT / "manifest.json"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) curvecarry"
_DATED = re.compile(r"^(?P<name>.+)_(?P<date>\d{8})$")


def raw_path(source: str, name: str, ext: str, fetched: dt.date, root: Path = RAW_ROOT) -> Path:
    """``root/source/<name>_<YYYYMMDD>.<ext>``."""
    return Path(root) / source / f"{name}_{fetched:%Y%m%d}.{ext}"


def _split_stem(path: Path) -> tuple[str, str]:
    m = _DATED.match(path.stem)
    if m is None:
        raise ValueError(f"{path.name!r} is not a dated raw filename (<name>_<YYYYMMDD>.<ext>)")
    return m["name"], m["date"]


def _load_manifest(manifest: Path) -> list[dict]:
    if not manifest.exists() or manifest.stat().st_size == 0:
        return []
    with open(manifest, encoding="utf-8") as fh:
        return json.load(fh)


def write_raw(content: bytes, path: Path, url: str, source: str, manifest: Path = MANIFEST) -> dict:
    """Write ``content`` to ``path`` (never overwriting) and append a manifest entry."""
    path = Path(path)
    if path.exists():
        raise FileExistsError(f"{path} exists; raw files are never overwritten (rule 5)")
    name, _ = _split_stem(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    entry = {
        "source": source,
        "name": name,
        "path": path.as_posix(),
        "url": url,
        "sha256": hashlib.sha256(content).hexdigest(),
        "bytes": len(content),
        "fetched_at": dt.datetime.now(dt.UTC).replace(microsecond=0).isoformat(),
    }
    entries = _load_manifest(Path(manifest))
    entries.append(entry)
    Path(manifest).parent.mkdir(parents=True, exist_ok=True)
    with open(manifest, "w", encoding="utf-8") as fh:
        json.dump(entries, fh, indent=2)
        fh.write("\n")
    return entry


def fetch_bytes(
    url: str, *, params: dict | None = None, headers: dict | None = None, timeout: int = 180
) -> bytes:
    """One GET. Raises on an HTTP error and on an empty body."""
    h = {"User-Agent": USER_AGENT}
    if headers:
        h.update(headers)
    r = requests.get(url, params=params, headers=h, timeout=timeout)
    r.raise_for_status()
    if len(r.content) == 0:
        raise RuntimeError(f"empty body from {r.url}")
    return r.content


def latest_raw(source: str, name: str, root: Path = RAW_ROOT) -> Path:
    """The raw file for ``name`` with the newest date in its filename."""
    folder = Path(root) / source
    matches = [p for p in folder.glob(f"{name}_*.*") if _DATED.match(p.stem)]
    matches = [p for p in matches if _split_stem(p)[0] == name]
    if not matches:
        raise FileNotFoundError(
            f"no raw file {name}_<YYYYMMDD>.* under {folder}; run: "
            f"uv run curvecarry fetch --source {source}"
        )
    exts = sorted({p.suffix for p in matches})
    if len(exts) > 1:
        raise ValueError(f"{name!r} under {folder} has more than one extension: {exts}")
    return max(matches, key=lambda p: _split_stem(p)[1])
