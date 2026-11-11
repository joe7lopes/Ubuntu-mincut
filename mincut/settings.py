"""Application settings, stored as JSON under XDG config."""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict


APP_ID = "mincut"
APP_DIR = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / APP_ID
STATE_DIR = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share")) / APP_ID
CONFIG_PATH = APP_DIR / "config.json"
CLIPS_PATH = STATE_DIR / "clips.json"

# Shortcut strings use Qt/GNOME notation: "Ctrl+Shift+V", "Super+Shift+V".
DEFAULTS: Dict[str, Any] = {
    "remember_num": 20,
    "favorites_remember_num": 20,
    "display_num": 10,
    "display_len": 40,
    "remove_duplicates": True,
    "sticky_bezel": False,
    "wraparound_bezel": False,
    "menu_selection_pastes": True,
    "save_preference": 0,          # 0 = never, 1 = ask, 2 = always
    "bezel_width": 500,
    "bezel_height": 200,
    "bezel_alpha": 0.75,
    "show_source": True,
    "font_family": "Sans Serif",
    "font_size": 20,
    "main_shortcut": "Ctrl+Shift+V",
    "favorites_shortcut": "Ctrl+Shift+F",
    "paste_simulation": True,
    "tracking": True,
}


@dataclass
class Settings:
    values: Dict[str, Any] = field(default_factory=lambda: dict(DEFAULTS))

    def __getitem__(self, key: str) -> Any:
        return self.values.get(key, DEFAULTS.get(key))

    def __setitem__(self, key: str, value: Any) -> None:
        self.values[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        return self.values.get(key, DEFAULTS.get(key, default))

    def as_dict(self) -> Dict[str, Any]:
        return dict(self.values)

    # -- persistence -----------------------------------------------------
    @classmethod
    def load(cls, path: Path = CONFIG_PATH) -> "Settings":
        settings = cls()
        try:
            data = json.loads(Path(path).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return settings
        merged = dict(DEFAULTS)
        merged.update({k: v for k, v in data.items() if k in DEFAULTS})
        settings.values = merged
        return settings

    def save(self, path: Path = CONFIG_PATH) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.values, indent=2, sort_keys=True), encoding="utf-8")
        tmp.replace(path)
