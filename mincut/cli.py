"""Command line entry point.

    mincut              start the tray app (no-op if already running)
    mincut toggle       show or hide the bezel
    mincut prefs        open the preferences dialog
    mincut quit         stop the running instance
    mincut setup        register the GlobalShortcuts keybinding / report status
"""

from __future__ import annotations

import argparse
import json
import os
import sys

from PyQt6.QtCore import QCoreApplication
from PyQt6.QtNetwork import QLocalServer, QLocalSocket
from PyQt6.QtWidgets import QApplication

from .settings import CONFIG_PATH, Settings

SOCKET_NAME = "mincut-single-instance"


def _send(command: str, timeout_ms: int = 800) -> bool:
    socket = QLocalSocket()
    socket.connectToServer(SOCKET_NAME)
    if not socket.waitForConnected(timeout_ms):
        return False
    socket.write(command.encode("utf-8"))
    socket.flush()
    socket.waitForBytesWritten(timeout_ms)
    socket.disconnectFromServer()
    return True


def _listen(app) -> QLocalServer:
    QLocalServer.removeServer(SOCKET_NAME)
    server = QLocalServer()
    server.listen(SOCKET_NAME)

    def handle() -> None:
        conn = server.nextPendingConnection()
        if conn is None:
            return
        conn.waitForReadyRead(300)
        command = bytes(conn.readAll()).decode("utf-8", "ignore").strip()

        if command == "ping":
            pass
        elif command == "toggle":
            app.toggle_bezel()
        elif command == "prefs":
            app.show_preferences()
        elif command == "quit":
            app.quit()
        elif command.startswith("clip:"):
            app.ingest(command[5:])
        conn.disconnectFromServer()

    server.newConnection.connect(handle)
    return server


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="mincut", description="Clipboard history with a bezel.")
    parser.add_argument(
        "command",
        nargs="?",
        default="start",
        choices=["start", "toggle", "prefs", "quit", "status", "setup", "clip"],
    )
    parser.add_argument("argument", nargs="?", default="")
    args = parser.parse_args(argv)

    QCoreApplication.setApplicationName("mincut")
    QCoreApplication.setOrganizationName("mincut")

    if args.command in ("toggle", "prefs", "quit"):
        app = QApplication(sys.argv[:1])
        if _send(args.command):
            return 0
        print("Mincut is not running.", file=sys.stderr)
        return 1

    if args.command == "clip":
        app = QApplication(sys.argv[:1])
        if not _send("clip:" + args.argument):
            print("Mincut is not running.", file=sys.stderr)
            return 1
        return 0

    if args.command == "status":
        print(json.dumps(Settings.load().as_dict(), indent=2))
        print(f"config: {CONFIG_PATH}")
        return 0

    if args.command == "setup":
        from .hotkey import GnomeShortcut, is_wayland

        if is_wayland():
            shortcut = GnomeShortcut("mincut toggle")
            ok = shortcut.register(str(Settings.load()["main_shortcut"]))
            print("registered the desktop shortcut" if ok else "could not register a shortcut")
            return 0 if ok else 1
        print("X11: the shortcut is grabbed by the running instance.")
        return 0

    # start
    app = QApplication(sys.argv[:1])
    app.setQuitOnLastWindowClosed(False)
    if _send("ping"):
        print("Mincut is already running.")
        return 0

    from .app import MincutApp

    controller = MincutApp(app)
    _listen(controller)
    if not os.environ.get("DISPLAY") and not os.environ.get("WAYLAND_DISPLAY"):
        print("No display detected; running with the clipboard watcher only.")
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
