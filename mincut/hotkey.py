"""Global shortcut registration.

X11 lets an application swallow a key combination, so the shortcuts are
grabbed directly.  Wayland does not: the compositor owns the keyboard, and the
only supported routes are the GlobalShortcuts portal or the desktop's own
keybinding store.  GNOME is handled through GSettings, which is what a user
would do by hand in Settings \u2192 Keyboard \u2192 Custom Shortcuts.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from typing import Callable, List, Optional

CUSTOM_KEYBINDING_SCHEMA = "org.gnome.settings-daemon.plugins.media-keys"
CUSTOM_PATH_ROOT = "/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/"

MODIFIER_ALIASES = {
    "ctrl": "ctrl",
    "control": "ctrl",
    "alt": "alt",
    "shift": "shift",
    "super": "super",
    "meta": "super",
    "win": "super",
    "cmd": "super",
}


def parse_shortcut(text: str) -> List[str]:
    """'Ctrl+Shift+V' -> ['ctrl', 'shift', 'v'] (modifiers first, lower-cased)."""
    parts = [p.strip() for p in (text or "").split("+") if p.strip()]
    mods, key = [], ""
    for part in parts:
        low = part.lower()
        if low in MODIFIER_ALIASES:
            mods.append(MODIFIER_ALIASES[low])
        else:
            key = low
    return mods + ([key] if key else [])


def to_gnome_accelerator(text: str) -> str:
    """'Ctrl+Shift+V' -> '<Primary><Shift>v' (the canonical GTK form)."""
    tags = {"ctrl": "<Primary>", "alt": "<Alt>", "shift": "<Shift>", "super": "<Super>"}
    parsed = parse_shortcut(text)
    if not parsed:
        return ""
    mods = "".join(tags[m] for m in parsed[:-1] if m in tags)
    return mods + parsed[-1]


def _has(cmd: str) -> bool:
    return shutil.which(cmd) is not None


def toggle_command() -> str:
    """The command GNOME should run, with the binary's absolute path.

    ``~/.local/bin`` is not always on the PATH of the graphical session, and a
    custom shortcut that calls the bare ``mincut`` then fails silently.  The
    path is left unquoted: GSettings parses the value as a GVariant string and
    rejects an embedded pair of quotes.
    """
    exe = shutil.which("mincut")
    if not exe and sys.argv and os.path.isfile(sys.argv[0]):
        exe = sys.argv[0]
    return f"{os.path.abspath(exe)} toggle" if exe else "mincut toggle"


class ShortcutError(RuntimeError):
    pass


class X11Shortcut:
    """Grab key combinations on the root window via python-xlib."""

    def __init__(self) -> None:
        self._grabs: List[tuple] = []
        self._display = None
        self._root = None

    def available(self) -> bool:
        try:
            import Xlib  # noqa: F401
        except ImportError:
            return False
        return bool(os.environ.get("DISPLAY"))

    def grab(self, shortcut: str, callback: Callable[[], None]) -> bool:
        try:
            from Xlib import X, XK, display as xdisplay
        except ImportError:
            return False
        try:
            self._display = self._display or xdisplay.Display()
        except Exception:
            return False
        root = self._display.screen().root

        mods = 0
        key_name = None
        for part in parse_shortcut(shortcut):
            if part == "ctrl":
                mods |= X.ControlMask
            elif part == "shift":
                mods |= X.ShiftMask
            elif part == "alt":
                mods |= X.Mod1Mask
            elif part == "super":
                mods |= X.Mod4Mask
            else:
                key_name = part
        if not key_name:
            return False
        keysym = XK.string_to_keysym(key_name)
        if keysym == 0 and len(key_name) == 1:
            keysym = ord(key_name)
        code = self._display.keysym_to_keycode(keysym)
        if not code:
            return False
        # NumLock and CapsLock must not defeat the grab.
        for extra in (0, X.LockMask, X.Mod2Mask, X.LockMask | X.Mod2Mask):
            root.grab_key(code, mods | extra, True, X.GrabModeAsync, X.GrabModeAsync)
        self._display.sync()
        self._grabs.append((code, mods, callback))
        return True

    def poll(self) -> None:
        """Dispatch pending key events; call this from a timer."""
        if self._display is None or not self._grabs:
            return
        from Xlib import X
        while self._display.pending_events():
            event = self._display.next_event()
            if event.type != X.KeyPress:
                continue
            for code, mods, callback in self._grabs:
                if event.detail == code and (event.state & ~(X.LockMask | X.Mod2Mask)) == mods:
                    callback()
                    break


class GnomeShortcut:
    """Register a custom keybinding through GSettings."""

    def __init__(self, command: str = "mincut toggle") -> None:
        self.command = command

    def available(self) -> bool:
        return _has("gsettings") and self._schema_present()

    @staticmethod
    def _schema_present() -> bool:
        try:
            out = subprocess.run(
                ["gsettings", "list-schemas"], capture_output=True, timeout=5
            )
        except (OSError, subprocess.SubprocessError):
            return False
        return CUSTOM_KEYBINDING_SCHEMA.encode() in out.stdout

    def _path(self, name: str) -> str:
        return f"{CUSTOM_PATH_ROOT}{name}/"

    def _current_list(self) -> List[str]:
        out = subprocess.run(
            ["gsettings", "get", CUSTOM_KEYBINDING_SCHEMA, "custom-keybindings"],
            capture_output=True,
            timeout=5,
        ).stdout.decode()
        import re

        return re.findall(r"/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/[^'\"]+/", out)

    def register(self, shortcut: str, name: str = "mincut") -> bool:
        if not self.available():
            return False
        path = self._path(name)
        entries = self._current_list()
        if path not in entries:
            entries.append(path)
            value = "[" + ", ".join(f"'{e}'" for e in entries) + "]"
            subprocess.run(
                ["gsettings", "set", CUSTOM_KEYBINDING_SCHEMA, "custom-keybindings", value],
                check=False,
            )
        for key, value in (
            ("name", "Mincut clipboard history"),
            ("command", self.command),
            ("binding", to_gnome_accelerator(shortcut)),
        ):
            subprocess.run(
                ["gsettings", "set", f"{CUSTOM_KEYBINDING_SCHEMA}.custom-keybinding:{path}", key, value],
                check=False,
            )
        return True

    def unregister(self, name: str = "mincut") -> None:
        path = self._path(name)
        entries = [e for e in self._current_list() if e != path]
        value = "[" + ", ".join(f"'{e}'" for e in entries) + "]"
        subprocess.run(
            ["gsettings", "set", CUSTOM_KEYBINDING_SCHEMA, "custom-keybindings", value], check=False
        )


def is_wayland() -> bool:
    return bool(os.environ.get("WAYLAND_DISPLAY")) or os.environ.get("XDG_SESSION_TYPE") == "wayland"
