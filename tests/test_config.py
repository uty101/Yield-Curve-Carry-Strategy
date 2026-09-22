import copy
import re

from curvecarry import config


def test_config_loads_every_named_key() -> None:
    cfg = config.load()
    for key in config.REQUIRED_KEYS:
        config._get(cfg, key)  # raises KeyError if absent
    # blank until step 1.9 wrote them (Session 1 part B);
    # now dated, ordered, and before strategy_end
    start, full = cfg["sample"]["strategy_start"], cfg["sample"]["sample_full_start"]
    assert start == "1997-08-31" and full == "2004-11-30"
    assert start <= full <= str(cfg["sample"]["strategy_end"].date())
    assert str(cfg["sample"]["strategy_end"].date()) == "2026-08-31"


def test_config_hash_stable_and_sensitive() -> None:
    a = config.load()
    b = config.load()
    assert config.config_hash(a) == config.config_hash(b)
    assert re.fullmatch(r"[0-9a-f]{12}", config.config_hash(a))
    c = copy.deepcopy(a)
    c["overlay"]["z_entry"] = 2.0
    assert config.config_hash(c) != config.config_hash(a)


def test_missing_key_is_named(tmp_path) -> None:
    src = open("config.toml", encoding="utf-8").read().replace("z_entry = 1.5", "z_entryx = 1.5")
    p = tmp_path / "config.toml"
    p.write_text(src, encoding="utf-8")
    try:
        config.load(p)
    except KeyError as e:
        assert e.args[0] == "overlay.z_entry"
    else:
        raise AssertionError("missing key did not raise")
