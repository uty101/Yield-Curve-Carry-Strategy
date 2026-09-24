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
    # two executions of one label: two rows in the audit trail, still one trial
    assert speclog.count_rows(p) == 2
    assert speclog.count_runs(p) == 1
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
    assert speclog.count_rows(p) == 3
    assert speclog.count_runs(p) == 1  # one label, so one trial


# ---- owner's ruling 2026-09-24: a trial is a specification, not an execution


def test_duplicate_label_leaves_n_unchanged(tmp_path) -> None:
    """Re-running a logged variant adds a row and does not add a trial.

    This is what lets the project be rebuilt without moving a reported number:
    ``N`` is the count of distinct labels, so a rebuild that re-runs every
    variant reports the same deflated Sharpe it did before.
    """
    p = tmp_path / "spec.csv"
    cfg = {"a": 1}
    speclog.log_run(cfg, label="carry_hedged", path=p)
    speclog.log_run(cfg, label="carry_unhedged", path=p)
    assert speclog.count_runs(p) == 2
    assert speclog.count_rows(p) == 2

    speclog.log_run(cfg, label="carry_hedged", path=p)  # the same trial, run again
    assert speclog.count_runs(p) == 2, "a repeat run is not a new trial"
    assert speclog.count_rows(p) == 3, "but it is still a row in the audit trail"

    speclog.log_run(cfg, label="carry_hedged_ddstop", path=p)
    assert speclog.count_runs(p) == 3
    assert speclog.count_rows(p) == 4


def test_a_whole_rebuild_does_not_move_n(tmp_path) -> None:
    """Logging every label a second time leaves N exactly where it was."""
    p = tmp_path / "spec.csv"
    labels = [f"variant_{i}" for i in range(19)]
    for label in labels:
        speclog.log_run({"a": 1}, label=label, path=p)
    before = speclog.count_runs(p)
    assert before == 19

    for label in labels:  # the rebuild
        speclog.log_run({"a": 1}, label=label, path=p)
    assert speclog.count_runs(p) == before
    assert speclog.count_rows(p) == 2 * len(labels)


def test_count_rows_is_the_append_only_audit_trail(tmp_path) -> None:
    """The row count still only ever grows, and every row keeps its own run_id."""
    p = tmp_path / "spec.csv"
    ids = [speclog.log_run({"a": 1}, label="same", path=p) for _ in range(4)]
    assert speclog.count_rows(p) == 4
    assert speclog.count_runs(p) == 1
    assert len(set(ids)) == 4, "each execution is still individually identifiable"
