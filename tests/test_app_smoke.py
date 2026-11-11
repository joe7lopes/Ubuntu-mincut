"""End-to-end smoke test of the controller, with no display attached."""

import json
import os
import sys
from pathlib import Path

import pytest

pytest.importorskip("PyQt6")


def _fresh(monkeypatch, tmp_path):
    """Reload the settings module against a throwaway config home."""
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
    for name in [m for m in list(sys.modules) if m.startswith("mincut")]:
        del sys.modules[name]
    from mincut import settings as settings_mod

    settings_mod.CONFIG_PATH = tmp_path / "config" / "mincut" / "config.json"
    settings_mod.CLIPS_PATH = tmp_path / "data" / "mincut" / "clips.json"
    return settings_mod


def test_app_lifecycle(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path)
    from PyQt6.QtWidgets import QApplication

    from mincut.app import MincutApp

    qapp = QApplication.instance() or QApplication([])
    controller = MincutApp(qapp)
    try:
        controller.ingest("first")
        controller.ingest("second")
        assert controller.store.contents_at(0) == "second"

        controller.toggle_bezel()
        assert controller.bezel.isVisible() is True
        controller.toggle_bezel()
        assert controller.bezel.isVisible() is False

        controller.paste("first")
        assert qapp.clipboard().text() == "first"
        assert controller.watcher.last == "first"
        # Our own write must not come back as a new clipping.
        assert controller.watcher.poll() is None

        controller._save_clips()
        clips_file = tmp_path / "data" / "mincut" / "clips.json"
        saved = json.loads(clips_file.read_text())
        assert saved["main"]["clips"][0]["contents"] == "second"
    finally:
        controller.timer.stop()
        controller.tray.hide()


def test_merging_from_menu(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path)
    from PyQt6.QtWidgets import QApplication

    from mincut.app import MincutApp

    qapp = QApplication.instance() or QApplication([])
    controller = MincutApp(qapp)
    try:
        controller.ingest("a")
        controller.ingest("b")
        controller._merge_all()
        assert controller.store.contents_at(0) == "a\nb"
    finally:
        controller.timer.stop()
        controller.tray.hide()
