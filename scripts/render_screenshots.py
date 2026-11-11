"""Write the screenshots used by the README (no display needed).

    QT_QPA_PLATFORM=offscreen python3 scripts/render_screenshots.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PIL import Image
from PyQt6.QtWidgets import QApplication

from mincut.bezel import Bezel
from mincut.keys import BezelState
from mincut.prefs import PreferencesDialog
from mincut.settings import Settings
from mincut.store import Store

DOCS = Path(__file__).resolve().parent.parent / "docs"

SAMPLES = [
    ("select id, name from users where created_at > now() - interval '7 days';", "Terminal"),
    ("https://docs.ubuntu.com/release-notes/26.04/", "Firefox"),
    ("git rebase --interactive origin/main", "Terminal"),
    ("The bezel shows your history in the middle of the screen.", "Notes"),
]


def desktop(width: int, height: int) -> Image.Image:
    top = (232, 235, 240)
    bottom = (64, 70, 88)
    img = Image.new("RGB", (width, height))
    px = img.load()
    for y in range(height):
        for x in range(width):
            t = (x / width + y / height) / 2
            px[x, y] = tuple(int(top[i] + (bottom[i] - top[i]) * t) for i in range(3))
    return img


def state_for(settings: Settings, favorites: bool) -> BezelState:
    store = Store()
    for text, app_name in reversed(SAMPLES):
        store.add(text, timestamp=1762000000, app=app_name)
    fav = Store()
    if favorites:
        fav.add("https://github.com/joe7lopes", timestamp=1762000000, app="Firefox")
        fav.add("docker compose up --build", timestamp=1762000000, app="Terminal")
    state = BezelState(store, fav)
    state.favorites_mode = favorites
    state.position = 0 if favorites else 1
    return state


def render_bezel(settings: Settings, favorites: bool, out: Path) -> None:
    bezel = Bezel(state_for(settings, favorites), settings)
    bezel.refresh()
    bezel.resize(settings["bezel_width"], settings["bezel_height"])
    raw = Path("/tmp") / f"_shot_{favorites}.png"
    bezel.grab().save(str(raw))
    fg = Image.open(raw).convert("RGBA")
    canvas = desktop(fg.width + 260, fg.height + 180)
    canvas.paste(fg, (130, 90), fg)
    canvas.save(out)


def main() -> int:
    DOCS.mkdir(exist_ok=True)
    app = QApplication(sys.argv[:1])
    settings = Settings()
    render_bezel(settings, False, DOCS / "bezel.png")
    render_bezel(settings, True, DOCS / "bezel-favorites.png")

    dialog = PreferencesDialog(Settings())
    dialog.resize(580, 430)
    dialog.show()
    app.processEvents()
    dialog.grab().save(str(DOCS / "preferences.png"))
    dialog.close()
    print("wrote", ", ".join(p.name for p in sorted(DOCS.glob("*.png"))))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
