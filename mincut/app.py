"""Application controller: clipboard watching, bezel, tray and persistence."""

from __future__ import annotations

import os
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import QObject, QTimer, Qt
from PyQt6.QtGui import QAction, QColor, QIcon, QPainter, QPixmap
from PyQt6.QtWidgets import QApplication, QMenu, QSystemTrayIcon

from . import clipboard as clip_backend
from . import hotkey
from .bezel import Bezel
from .keys import BezelState
from .settings import CLIPS_PATH, Settings
from .store import Store

MAX_FILE_CHARS = 2000


def tray_icon(active: bool = True) -> QIcon:
    """A small scissors glyph drawn in code, so no image files are needed."""
    size = 32
    pix = QPixmap(size, size)
    pix.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pix)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    color = QColor(230, 70, 60) if active else QColor(140, 140, 140)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(color)
    painter.drawRoundedRect(2, 2, 28, 28, 7, 7)
    painter.setPen(QColor(255, 255, 255, 235))
    painter.drawText(pix.rect(), int(Qt.AlignmentFlag.AlignCenter), "\u2702")
    painter.end()
    return QIcon(pix)


class MincutApp(QObject):
    def __init__(self, app: QApplication) -> None:
        super().__init__()
        self.app = app
        self.settings = Settings.load()
        self.store = Store(remember_num=int(self.settings["remember_num"]))
        self.favorites = Store(remember_num=int(self.settings["favorites_remember_num"]))
        self._load_clips()

        self.state = BezelState(
            self.store,
            self.favorites,
            display_num=int(self.settings["display_num"]),
            wraparound=bool(self.settings["wraparound_bezel"]),
        )
        self.state.display_len = int(self.settings["display_len"])
        self.state.sync_display_len(int(self.settings["display_len"]))

        self.bezel = Bezel(self.state, self.settings)
        self.bezel.pasteRequested.connect(self.paste)
        self.bezel.saveRequested.connect(self.save_clipboard_item)
        self.bezel.preferencesRequested.connect(self.show_preferences)

        self.backend = self._clipboard_backend()
        self.watcher = clip_backend.ClipboardWatcher(self.backend)
        self.watcher.paused = not bool(self.settings["tracking"])

        self.timer = QTimer(self)
        self.timer.setInterval(self.watcher.interval_ms)
        self.timer.timeout.connect(self._poll)
        self.timer.start()

        self._setup_tray()
        self._setup_shortcuts()
        self._save_timer = QTimer(self)
        self._save_timer.setSingleShot(True)
        self._save_timer.setInterval(1500)
        self._save_timer.timeout.connect(self._save_clips)
        self._setup_dbus()

    # -- clipboard backends ----------------------------------------------
    def _clipboard_backend(self) -> clip_backend.ClipboardBackend:
        """Pick the best backend for the session; GNOME Wayland uses the bridge."""
        try:
            return clip_backend.detect(gnome_bridge=self._shell_bridge())
        except Exception:
            return clip_backend.QtClipboard()

    def _shell_bridge(self) -> clip_backend.ClipboardBackend:
        """Reads arrive as D-Bus signals from the extension; writes go back out
        through it, falling back to Qt while the bezel holds the focus."""
        fallback = clip_backend.QtClipboard()

        def write(text: str) -> bool:
            try:
                from PyQt6.QtDBus import QDBusConnection, QDBusInterface, QDBusMessage
            except ImportError:
                return fallback.write(text)
            bus = QDBusConnection.sessionBus()
            if not bus.isConnected():
                return fallback.write(text)
            shell = QDBusInterface(
                "org.mincut.Shell", "/org/mincut/Shell", "org.mincut.Shell", bus
            )
            shell.setTimeout(2000)
            reply = shell.call("SetClipboard", text)
            if reply.type() == QDBusMessage.MessageType.ErrorMessage:
                return fallback.write(text)
            return True

        # History is pushed to us, so polling has nothing to read.
        return clip_backend.ShellBridgeClipboard(write, lambda: None)

    # -- D-Bus (the shell extension talks to us here) --------------------
    def _setup_dbus(self) -> None:
        try:
            from PyQt6.QtDBus import QDBusConnection
        except ImportError:
            return
        from PyQt6.QtCore import QObject, pyqtClassInfo, pyqtSlot

        controller = self

        # The interface name is what the extension calls.  PyQt exports
        # nothing unless slots are requested, and names an undecorated class
        # after its Python module, so both pieces are needed here.
        @pyqtClassInfo("D-Bus Interface", "org.mincut.App")
        class Service(QObject):
            @pyqtSlot()
            def Toggle(self) -> None:
                controller.toggle_bezel()

            @pyqtSlot()
            def Preferences(self) -> None:
                controller.show_preferences()

            @pyqtSlot()
            def Quit(self) -> None:
                controller.quit()

            @pyqtSlot(str)
            def ClipboardChanged(self, text: str) -> None:
                controller.ingest(text)

            @pyqtSlot(str)
            def SetClipboard(self, text: str) -> None:
                # Set through Qt: calling the Shell bridge here would ask the
                # extension to set the same text again.
                clip_backend.QtClipboard().write(text)
                controller.watcher.set_current(text)

        bus = QDBusConnection.sessionBus()
        if not bus.isConnected():
            self.dbus_service = None
            return
        bus.registerService("org.mincut.App")
        self.dbus_service = Service()
        bus.registerObject(
            "/org/mincut/App",
            self.dbus_service,
            QDBusConnection.RegisterOption.ExportAllSlots,
        )

    # -- tray ------------------------------------------------------------
    def _setup_tray(self) -> None:
        self.tray = QSystemTrayIcon(tray_icon(True), self)
        self.tray.setToolTip("Mincut \u2014 clipboard history")
        self.menu = QMenu()
        self.tray.setContextMenu(self.menu)
        self.tray.activated.connect(self._on_tray_activated)
        self.tray.show()
        self._rebuild_menu()

    def _on_tray_activated(self, reason) -> None:
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self.toggle_bezel()

    def _rebuild_menu(self) -> None:
        self.menu.clear()
        visible = self.store.display_strings(int(self.settings["display_num"]))
        if visible:
            for index, text in enumerate(visible):
                label = text if text else "(empty)"
                if len(label) > 60:
                    label = label[:60] + "\u2026"
                action = QAction(f"{index + 1}. {label.replace('&', '&&')}", self.menu)
                action.triggered.connect(lambda _=False, i=index: self._pick_from_menu(i))
                self.menu.addAction(action)
            self.menu.addSeparator()
        merge = QAction("Merge All", self.menu)
        merge.triggered.connect(self._merge_all)
        clear = QAction("Clear All", self.menu)
        clear.triggered.connect(self._clear_all)
        prefs = QAction("Preferences\u2026", self.menu)
        prefs.triggered.connect(self.show_preferences)
        self.menu.addAction(merge)
        self.menu.addAction(clear)
        self.untrack = QAction("Pause tracking", self.menu)
        self.untrack.setCheckable(True)
        self.untrack.setChecked(not bool(self.settings["tracking"]))
        self.untrack.toggled.connect(self._toggle_tracking)
        self.menu.addAction(self.untrack)
        self.menu.addSeparator()
        self.menu.addAction(prefs)
        quit_action = QAction("Quit Mincut", self.menu)
        quit_action.triggered.connect(self.quit)
        self.menu.addAction(quit_action)

    def _pick_from_menu(self, index: int) -> None:
        contents = self.store.contents_at(index)
        if contents is None:
            return
        if self.settings["menu_selection_pastes"]:
            self.paste(contents)
        else:
            self.backend.write(contents)
            self.watcher.set_current(contents)

    def _merge_all(self) -> None:
        if self.store.merge(timestamp=int(time.time())):
            self._changed()
            self.tray.showMessage("Mincut", "History merged into one clipping.")

    def _clear_all(self) -> None:
        self.store.clear()
        self._changed()

    def _toggle_tracking(self, paused: bool) -> None:
        self.settings["tracking"] = not paused
        self.watcher.paused = paused
        self.settings.save()
        self.tray.setIcon(tray_icon(not paused))

    # -- clipboard -------------------------------------------------------
    def _poll(self) -> None:
        text = self.watcher.poll()
        if text:
            self.ingest(text)

    def ingest(self, text: str) -> None:
        if not self.settings["tracking"]:
            return
        if self.store.add(text, timestamp=int(time.time()), app=self._source_app()):
            self._changed()

    def _source_app(self) -> str:
        return os.environ.get("MINCUT_SOURCE", "")

    def paste(self, contents: str) -> None:
        self.backend.write(contents)
        self.watcher.set_current(contents)
        self.bezel.dismiss()
        if self.settings["paste_simulation"]:
            QTimer.singleShot(60, lambda: self._simulate_paste(contents))

    def _simulate_paste(self, contents: str) -> None:
        if not clip_backend.simulate_paste():
            self.tray.showMessage("Mincut", "Copied \u2014 press Ctrl+V to paste.", QSystemTrayIcon.MessageIcon.Information, 1500)

    def save_clipboard_item(self, contents: str, delete_after: bool = False) -> None:
        target_dir = Path.home() / "Desktop"
        if not target_dir.is_dir():
            target_dir = Path.home()
        stamp = datetime.now().strftime("%Y-%m-%d at %H.%M.%S")
        path = target_dir / f"Clipping {stamp}.txt"
        try:
            path.write_text(contents[:MAX_FILE_CHARS], encoding="utf-8")
        except OSError as exc:
            self.tray.showMessage("Mincut", f"Could not save clipping: {exc}")
            return
        if delete_after:
            index = self.store.index_of(contents)
            if index >= 0:
                self.store.clear_item(index)
                self._changed()
        self.tray.showMessage("Mincut", f"Saved to {path.name}")

    # -- bezel -----------------------------------------------------------
    def toggle_bezel(self) -> None:
        if self.bezel.isVisible():
            self.bezel.dismiss()
            return
        self.state.display_len = int(self.settings["display_len"])
        self.state.sync_display_len(int(self.settings["display_len"]))
        self.state.wraparound = bool(self.settings["wraparound_bezel"])
        self.bezel.open_bezel()

    def show_preferences(self) -> None:
        from .prefs import PreferencesDialog

        dialog = PreferencesDialog(self.settings, self.bezel)
        if dialog.exec():
            self.apply_settings()
        dialog.deleteLater()

    def apply_settings(self) -> None:
        self.store.set_remember_num(int(self.settings["remember_num"]))
        self.favorites.set_remember_num(int(self.settings["favorites_remember_num"]))
        self.store.remove_duplicates = bool(self.settings["remove_duplicates"])
        self.state.display_len = int(self.settings["display_len"])
        self.state.sync_display_len(int(self.settings["display_len"]))
        self.state.display_num = int(self.settings["display_num"])
        self.state.wraparound = bool(self.settings["wraparound_bezel"])
        self.watcher.paused = not bool(self.settings["tracking"])
        self.settings.save()
        self.bezel.resize(int(self.settings["bezel_width"]), int(self.settings["bezel_height"]))
        self.bezel.refresh()
        self._rebuild_menu()
        self._setup_shortcuts(force=True)
        self._save_clips()

    # -- shortcuts -------------------------------------------------------
    def _setup_shortcuts(self, force: bool = False) -> None:
        if getattr(self, "_shortcuts_done", False) and not force:
            return
        self._shortcuts_done = True
        shortcut = str(self.settings["main_shortcut"])
        if hotkey.is_wayland():
            self._gnome = hotkey.GnomeShortcut(hotkey.toggle_command())
            if self._gnome.available():
                self._gnome.register(shortcut)
        else:
            self._x11 = hotkey.X11Shortcut()
            if self._x11.available():
                self._x11.grab(shortcut, self.toggle_bezel)
                self._x11_timer = QTimer(self)
                self._x11_timer.setInterval(50)
                self._x11_timer.timeout.connect(self._x11.poll)
                self._x11_timer.start()

    # -- state -----------------------------------------------------------
    def _changed(self) -> None:
        self._rebuild_menu()
        self.bezel.refresh()
        self._save_timer.start()

    def _load_clips(self) -> None:
        import json

        path = Path(CLIPS_PATH)
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return
        self.store = Store.from_dict(data.get("main", {}))
        self.favorites = Store.from_dict(data.get("favorites", {}))
        self.store.remember_num = int(self.settings["remember_num"])
        self.favorites.remember_num = int(self.settings["favorites_remember_num"])

    def _save_clips(self) -> None:
        import json

        path = Path(CLIPS_PATH)
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"main": self.store.to_dict(), "favorites": self.favorites.to_dict()}
        tmp = path.with_suffix(".tmp")
        try:
            tmp.write_text(json.dumps(payload, indent=1), encoding="utf-8")
            tmp.replace(path)
        except OSError:
            pass

    def quit(self) -> None:
        self._save_clips()
        self.settings.save()
        self.tray.hide()
        self.app.quit()
