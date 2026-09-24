import datetime as dt
import hashlib
import json

import pytest

from curvecarry import manifest

D1 = dt.date(2026, 9, 16)
D2 = dt.date(2026, 9, 17)


def test_second_fetch_to_existing_path_raises(tmp_path) -> None:
    m = tmp_path / "manifest.json"
    p = manifest.raw_path("fred", "DGS10", "csv", D1, root=tmp_path)
    manifest.write_raw(b"a,b\n1,2\n", p, "https://x/1", "fred", manifest=m)
    with pytest.raises(FileExistsError):
        manifest.write_raw(b"different", p, "https://x/2", "fred", manifest=m)
    assert p.read_bytes() == b"a,b\n1,2\n"
    assert len(json.loads(m.read_text())) == 1


def test_manifest_entry_has_sha256_and_bytes(tmp_path) -> None:
    m = tmp_path / "manifest.json"
    content = b"observation_date,DGS10\n2026-09-14,4.97\n"
    p = manifest.raw_path("fred", "DGS10", "csv", D1, root=tmp_path)
    entry = manifest.write_raw(content, p, "https://x/DGS10", "fred", manifest=m)
    assert entry["sha256"] == hashlib.sha256(content).hexdigest()
    assert entry["bytes"] == len(content)
    assert entry["source"] == "fred" and entry["url"] == "https://x/DGS10"
    assert set(entry) == {"source", "name", "path", "url", "sha256", "bytes", "fetched_at"}
    assert json.loads(m.read_text())[0] == entry


def test_refetch_gets_dated_filename(tmp_path) -> None:
    a = manifest.raw_path("boe", "glcnominalmonthedata", "zip", D1, root=tmp_path)
    b = manifest.raw_path("boe", "glcnominalmonthedata", "zip", D2, root=tmp_path)
    assert a != b
    assert a.name == "glcnominalmonthedata_20260916.zip"
    assert b.name == "glcnominalmonthedata_20260917.zip"
    assert a.parent == tmp_path / "boe"


def test_latest_raw_picks_newest(tmp_path) -> None:
    m = tmp_path / "manifest.json"
    a = manifest.raw_path("fred", "DGS10", "csv", D1, root=tmp_path)
    b = manifest.raw_path("fred", "DGS10", "csv", D2, root=tmp_path)
    manifest.write_raw(b"old", b, "u", "fred", manifest=m)  # newer date written first
    manifest.write_raw(b"new", a, "u", "fred", manifest=m)  # older date has the later mtime
    assert manifest.latest_raw("fred", "DGS10", root=tmp_path) == b
    # a different name with the same prefix is not matched
    c = manifest.raw_path("fred", "DGS10_extra", "csv", dt.date(2027, 1, 1), root=tmp_path)
    manifest.write_raw(b"x", c, "u", "fred", manifest=m)
    assert manifest.latest_raw("fred", "DGS10", root=tmp_path) == b
    # the hint must name the LOADER, not the raw folder: "--source fred" is not
    # a valid choice and telling a reader to type it wasted three retries
    with pytest.raises(FileNotFoundError, match="fetch --source us, fx or short_rates"):
        manifest.latest_raw("fred", "DGS1", root=tmp_path)


def test_latest_raw_refuses_mixed_extensions(tmp_path) -> None:
    m = tmp_path / "manifest.json"
    a = manifest.raw_path("boc", "zero_curve", "csv", D1, root=tmp_path)
    b = manifest.raw_path("boc", "zero_curve", "zip", D2, root=tmp_path)
    manifest.write_raw(b"1", a, "u", "boc", manifest=m)
    manifest.write_raw(b"2", b, "u", "boc", manifest=m)
    with pytest.raises(ValueError, match=r"\.csv.*\.zip"):
        manifest.latest_raw("boc", "zero_curve", root=tmp_path)


def test_manifest_name_round_trips_raw_path(tmp_path) -> None:
    m = tmp_path / "manifest.json"
    for source, name, ext in [
        ("fred", "DGS10", "csv"),
        ("bundesbank", "B0", "csv"),
        ("boe", "glcnominalmonthedata", "zip"),
        ("bdf", "tec10", "csv"),
        ("bis", "CBPOL_XM", "csv"),
    ]:
        p = manifest.raw_path(source, name, ext, D1, root=tmp_path)
        entry = manifest.write_raw(b"x", p, "u", source, manifest=m)
        assert entry["name"] == name
        assert entry["path"] == p.as_posix()
    with pytest.raises(ValueError):
        manifest.write_raw(b"x", tmp_path / "undated.csv", "u", "s", manifest=m)


def test_fetch_bytes_is_the_only_requests_call() -> None:
    import pathlib

    src = pathlib.Path("src/curvecarry")
    users = [p.name for p in src.rglob("*.py") if "import requests" in p.read_text("utf-8")]
    assert users == ["manifest.py"]


def test_fetch_bytes_rejects_empty_body(monkeypatch) -> None:
    class R:
        content = b""
        url = "https://x"

        def raise_for_status(self) -> None:
            pass

    monkeypatch.setattr(manifest.requests, "get", lambda *a, **k: R())
    with pytest.raises(RuntimeError, match="empty body"):
        manifest.fetch_bytes("https://x")
