"""Clipboard access across X11 and Wayland.

Three situations, in order of how much freedom the platform gives us:

* **X11** — anything may read the selection, so ``xclip``/``xsel`` plus a
  short poll is enough.
* **Wayland on a wlroots compositor** (Sway, Hyprland, ...) — ``wl-clipboard``
  speaks the data-control protocol, so the same poll works through
  ``wl-paste``/``wl-copy``.
* **Wayland on GNOME** — neither protocol is exposed, and no unprivileged
  client may read or write another client's selection.  The history is fed by
  the companion Shell extension over D-Bus instead.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from typing import Callable, Optional


def _has(cmd: str) -> bool:
    return shutil.which(cmd) is not None


def _run(args, timeout=5) -> Optional[str]:
    try:
        out = subprocess.run(args, capture_output=True, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired):
        return None
    if out.returncode != 0:
        return None
    return out.stdout.decode("utf-8", "replace")


class ClipboardBackend:
    """Read and write the system clipboard."""

    name = "none"

    def read(self) -> Optional[str]:
        return None

    def write(self, text: str) -> bool:
        return False

    def paste_unavailable_hint(self) -> str:
        return "Copied \u2014 press Ctrl+V to paste"


class X11Clipboard(ClipboardBackend):
    name = "x11"

    def _reader(self):
        if _has("xclip"):
            return ["xclip", "-o", "-selection", "clipboard"]
        if _has("xsel"):
            return ["xsel", "--clipboard", "--output"]
        return None

    def available(self) -> bool:
        return self._reader() is not None

    def read(self) -> Optional[str]:
        reader = self._reader()
        return _run(reader) if reader else None

    def write(self, text: str) -> bool:
        if _has("xclip"):
            args = ["xclip", "-selection", "clipboard", "-i"]
        elif _has("xsel"):
            args = ["xsel", "--clipboard", "--input"]
        else:
            return False
        try:
            subprocess.run(args, input=text.encode("utf-8"), check=True, timeout=5)
            return True
        except (OSError, subprocess.SubprocessError):
            return False


class WaylandClipboard(ClipboardBackend):
    name = "wayland"

    def available(self) -> bool:
        if not (_has("wl-paste") and _has("wl-copy")):
            return False
        # Reading requires a compositor that exposes data-control.
        return self.read() is not None

    def read(self) -> Optional[str]:
        return _run(["wl-paste", "--no-newline", "--type", "text"])

    def write(self, text: str) -> bool:
        try:
            subprocess.run(["wl-copy"], input=text.encode("utf-8"), check=True, timeout=5)
            return True
        except (OSError, subprocess.SubprocessError):
            return False


class ShellBridgeClipboard(ClipboardBackend):
    """Clipboard mediated by the shell extension (GNOME Wayland)."""

    name = "gnome-shell"

    def __init__(self, set_clipboard: Callable[[str], bool], get_clipboard: Callable[[], Optional[str]]):
        self._set = set_clipboard
        self._get = get_clipboard

    def read(self) -> Optional[str]:
        return self._get()

    def write(self, text: str) -> bool:
        return self._set(text)


class QtClipboard(ClipboardBackend):
    """The Qt clipboard.

    Writing always works: the bezel holds focus when a clipping is chosen, and
    a focused client may set the selection on every desktop.  Reading is only
    reliable where the platform allows it (X11), which is why GNOME Wayland
    feeds changes in from the shell extension instead.
    """

    name = "qt"

    def __init__(self) -> None:
        self._clipboard = None

    def _cb(self):
        if self._clipboard is None:
            from PyQt6.QtWidgets import QApplication

            app = QApplication.instance()
            self._clipboard = app.clipboard() if app is not None else None
        return self._clipboard

    def read(self) -> Optional[str]:
        clipboard = self._cb()
        if clipboard is None:
            return None
        text = clipboard.text()
        return text if text else None

    def write(self, text: str) -> bool:
        clipboard = self._cb()
        if clipboard is None:
            return False
        clipboard.setText(text)
        return True


def detect(is_wayland: Optional[bool] = None, gnome_bridge: Optional[ClipboardBackend] = None) -> ClipboardBackend:
    if is_wayland is None:
        is_wayland = bool(os.environ.get("WAYLAND_DISPLAY"))
    if is_wayland:
        wl = WaylandClipboard()
        if wl.available():
            return wl
        if gnome_bridge is not None:
            return gnome_bridge
        return wl
    x11 = X11Clipboard()
    if x11.available():
        return x11
    return QtClipboard()


class ClipboardWatcher:
    """Poll the clipboard and report genuinely new, non-empty text."""

    def __init__(self, backend: ClipboardBackend, interval_ms: int = 400) -> None:
        self.backend = backend
        self.interval_ms = interval_ms
        self.last: Optional[str] = None
        self.paused = False

    def poll(self) -> Optional[str]:
        """Return new clipboard text, or None when nothing changed."""
        if self.paused:
            return None
        text = self.backend.read()
        if text is None or text == "":
            return None
        if text == self.last:
            return None
        self.last = text
        return text

    def set_current(self, text: str) -> None:
        """Remember text we put on the clipboard ourselves, so we ignore it."""
        self.last = text


def simulate_paste(wayland: Optional[bool] = None) -> bool:
    """Ask the desktop to send Ctrl+V to whatever window has focus."""
    if wayland is None:
        wayland = bool(os.environ.get("WAYLAND_DISPLAY"))
    if not wayland:
        if _has("xdotool"):
            try:
                subprocess.run(
                    ["xdotool", "key", "--clearmodifiers", "ctrl+v"],
                    check=True,
                    timeout=5,
                )
                return True
            except (OSError, subprocess.SubprocessError):
                return False
        return False
    if _has("ydotool"):
        try:
            subprocess.run(["ydotool", "key", "29:1", "47:1", "47:0", "29:0"], check=True, timeout=5)
            return True
        except (OSError, subprocess.SubprocessError):
            return False
    return False
