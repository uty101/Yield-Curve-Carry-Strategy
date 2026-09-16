import pytest

from curvecarry import config, speclog

HEADER = "run_id,timestamp_utc,git_commit,config_hash,label,note"


def test_log_run_appends_row(tmp_path) -> None:
    cfg = config.load()
    p = tmp_path / "specifications.csv"
    a = speclog.log_run(cfg, "carry_hedged", "first", path=p)
    b = speclog.log_run(cfg, "carry_hedged", "second", path=p)
    lines = p.read_text(encoding="utf-8").splitlines()
    assert lines[0] == HEADER
    assert len(lines) == 3
    assert a != b
    assert speclog.count_runs(p) == 2
    assert lines[1].startswith(a) and lines[2].startswith(b)


def test_run_without_row_fails(tmp_path) -> None:
    p = tmp_path / "specifications.csv"
    with pytest.raises(RuntimeError):
        speclog.require_logged("nope", p)
    run_id = speclog.log_run(config.load(), "carry_hedged", path=p)
    speclog.require_logged(run_id, p)
    with pytest.raises(RuntimeError):
        speclog.require_logged("nope", p)


def test_speclog_is_append_only(tmp_path) -> None:
    p = tmp_path / "specifications.csv"
    speclog.log_run(config.load(), "a", path=p)
    before = p.read_bytes()
    speclog.log_run(config.load(), "b", path=p)
    after = p.read_bytes()
    assert after[: len(before)] == before
    assert speclog.count_runs(p) == 2


def test_run_id_carries_config_hash() -> None:
    cfg = config.load()
    h = config.config_hash(cfg)
    import tempfile
    from pathlib import Path

    with tempfile.TemporaryDirectory() as d:
        run_id = speclog.log_run(cfg, "x", path=Path(d) / "s.csv")
    assert run_id.endswith("-" + h)
    assert len(run_id) == 15 + 1 + 12


def test_same_second_same_config_gets_distinct_ids(tmp_path) -> None:
    cfg = config.load()
    p = tmp_path / "s.csv"
    ids = [speclog.log_run(cfg, "x", path=p) for _ in range(3)]
    assert len(set(ids)) == 3
    assert speclog.count_runs(p) == 3
