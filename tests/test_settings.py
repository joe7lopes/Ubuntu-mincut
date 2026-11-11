import json
import os

from mincut.settings import DEFAULTS, Settings


def test_defaults_roundtrip(tmp_path):
    path = tmp_path / "config.json"
    s = Settings()
    s["display_len"] = 60
    s["sticky_bezel"] = True
    s.save(path)
    loaded = Settings.load(path)
    assert loaded["display_len"] == 60
    assert loaded["sticky_bezel"] is True
    assert loaded["bezel_width"] == DEFAULTS["bezel_width"]


def test_unknown_keys_ignored(tmp_path):
    path = tmp_path / "config.json"
    path.write_text(json.dumps({"display_len": 33, "bogus": 1}))
    loaded = Settings.load(path)
    assert loaded["display_len"] == 33
    assert "bogus" not in loaded.as_dict()


def test_missing_file_falls_back_to_defaults(tmp_path):
    loaded = Settings.load(tmp_path / "nope.json")
    assert loaded["remember_num"] == DEFAULTS["remember_num"]


def test_corrupt_file_falls_back_to_defaults(tmp_path):
    path = tmp_path / "config.json"
    path.write_text("{not json")
    loaded = Settings.load(path)
    assert loaded["remember_num"] == DEFAULTS["remember_num"]


def test_shortcut_parsing():
    from mincut.hotkey import parse_shortcut, to_gnome_accelerator

    assert parse_shortcut("Ctrl+Shift+V") == ["ctrl", "shift", "v"]
    assert parse_shortcut("super + alt + f1") == ["super", "alt", "f1"]
    assert to_gnome_accelerator("Ctrl+Shift+V") == "<Primary><Shift>v"
    assert to_gnome_accelerator("super+space") == "<Super>space"
