"""Render the bezel to a PNG without a display.

Used for design review and for the screenshots in the README:

    QT_QPA_PLATFORM=offscreen python3 scripts/render_bezel.py out.png [favorites]
"""

from __future__ import annotations

import sys

from PIL import Image
from PyQt6.QtWidgets import QApplication

from mincut.bezel import Bezel
from mincut.keys import BezelState
from mincut.settings import Settings
from mincut.store import Store

SAMPLES = [
    ("select id, name from users where created_at > now() - interval '7 days';", "Terminal"),
    ("https://docs.ubuntu.com/release-notes/26.04/", "Firefox"),
    ("git rebase --interactive origin/main", "Terminal"),
    ("The bezel shows your history in the middle of the screen.", "Notes"),
]


def build_state(favorites: bool) -> BezelState:
    store = Store()
    for text, app_name in reversed(SAMPLES):
        store.add(text, timestamp=1762000000, app=app_name)
    fav = Store()
    if favorites:
        fav.add("favourite clipping", timestamp=1762000000, app="Notes")
    state = BezelState(store, fav)
    state.favorites_mode = favorites
    return state


def backdrop(width: int, height: int) -> Image.Image:
    """A stand-in desktop: soft diagonal gradient."""
    top = (236, 238, 242)
    bottom = (72, 78, 96)
    img = Image.new("RGB", (width, height))
    px = img.load()
    for y in range(height):
        for x in range(width):
            t = (x / width + y / height) / 2
            px[x, y] = tuple(int(top[i] + (bottom[i] - top[i]) * t) for i in range(3))
    return img


def main() -> int:
    out = sys.argv[1] if len(sys.argv) > 1 else "bezel.png"
    favorites = len(sys.argv) > 2 and sys.argv[2] == "favorites"
    app = QApplication(sys.argv[:1])
    settings = Settings()
    state = build_state(favorites)
    state.position = 0 if favorites else 1
    bezel = Bezel(state, settings)
    bezel.refresh()
    bezel.resize(settings["bezel_width"], settings["bezel_height"])
    raw = "/tmp/_bezel_raw.png"
    bezel.grab().save(raw)

    fg = Image.open(raw).convert("RGBA")
    canvas = backdrop(fg.width + 260, fg.height + 180)
    canvas.paste(fg, (130, 90), fg)
    canvas.save(out)
    print(f"wrote {out} {canvas.width}x{canvas.height}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
