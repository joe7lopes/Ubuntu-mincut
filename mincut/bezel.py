"""The bezel \u2014 the translucent pop-up that shows clipboard history.

It is a frameless, always-on-top window painted by hand: a rounded panel at low
opacity, the current clipping in large type, an optional row naming where the
clipping came from, arrows on either side, and a small counter at the bottom.
The favourites store gets a warm tint so the two are never confused.
"""

from __future__ import annotations

import math
from datetime import datetime
from typing import Optional

from PyQt6.QtCore import (
    QEasingCurve,
    QPoint,
    QPropertyAnimation,
    QRect,
    QRectF,
    Qt,
    QTimer,
    pyqtSignal,
)
from PyQt6.QtGui import QColor, QFont, QFontMetrics, QGuiApplication, QPainter, QPainterPath, QPen
from PyQt6.QtWidgets import QWidget

from . import keys
from .keys import Action, BezelState
from .store import Clip

KEY_NAMES = {
    Qt.Key.Key_Up: "up",
    Qt.Key.Key_Down: "down",
    Qt.Key.Key_Left: "left",
    Qt.Key.Key_Right: "right",
    Qt.Key.Key_Return: "return",
    Qt.Key.Key_Enter: "enter",
    Qt.Key.Key_Escape: "escape",
    Qt.Key.Key_Home: "home",
    Qt.Key.Key_End: "end",
    Qt.Key.Key_PageUp: "pageup",
    Qt.Key.Key_PageDown: "pagedown",
    Qt.Key.Key_Backspace: "backspace",
    Qt.Key.Key_Delete: "delete",
}

MAX_TEXT_CHARS = 2000
RADIUS = 25.0
BASELINE = 16.0


class Bezel(QWidget):
    """Keyboard-driven history panel."""

    keyHandled = pyqtSignal(object)          # keys.KeyResult
    pasteRequested = pyqtSignal(str)         # contents
    saveRequested = pyqtSignal(str, bool)    # contents, delete_after
    preferencesRequested = pyqtSignal()

    def __init__(self, state: BezelState, settings) -> None:
        super().__init__(None)
        self.state = state
        self.settings = settings
        self._clip: Optional[Clip] = None
        self._animate = QPropertyAnimation(self, b"windowOpacity", self)

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, False)
        self.setCursor(Qt.CursorShape.ArrowCursor)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.resize(self.settings["bezel_width"], self.settings["bezel_height"])

    # -- geometry --------------------------------------------------------
    def panel_rect(self) -> QRectF:
        return QRectF(0, 0, self.width(), self.height())

    def text_rect(self) -> QRectF:
        pad_top = 16.0
        if self.settings["show_source"] and self._clip is not None and self._clip.app:
            pad_top += 1.8 * BASELINE
        return QRectF(30, pad_top, self.width() - 60, self.height() - pad_top - 52)

    def counter_rect(self) -> QRectF:
        width = 4 * BASELINE
        return QRectF((self.width() - width) / 2, self.height() - (7 + 1.2 * BASELINE) - 7, width, 1.2 * BASELINE)

    # -- content ---------------------------------------------------------
    def refresh(self) -> None:
        self.state.clamp()
        self._clip = self.state.active.clips()[self.state.position] if self.state.current_contents() else None
        self.update()

    def open_bezel(self, position: Optional[int] = None) -> None:
        if position is not None:
            self.state.position = position
        self.state.clamp()
        self.resize(self.settings["bezel_width"], self.settings["bezel_height"])
        self._center()
        self.refresh()
        self.setWindowOpacity(0.0)
        self.show()
        self.raise_()
        self.activateWindow()
        self.setFocus(Qt.FocusReason.OtherFocusReason)
        self._animate.stop()
        self._animate.setDuration(90)
        self._animate.setStartValue(0.0)
        self._animate.setEndValue(1.0)
        self._animate.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._animate.start()

    def _center(self) -> None:
        screen = QGuiApplication.screenAt(self.cursor().pos()) or QGuiApplication.primaryScreen()
        if screen is None:
            return
        area = screen.availableGeometry()
        x = area.x() + (area.width() - self.width()) // 2
        y = area.y() + (area.height() - self.height()) // 2
        self.move(QPoint(x, y))

    def dismiss(self) -> None:
        self.hide()

    # -- painting --------------------------------------------------------
    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)

        alpha = float(self.settings["bezel_alpha"])
        if self.state.favorites_mode:
            base = QColor(153, 153, 0)
        else:
            base = QColor(26, 26, 26)
        base.setAlphaF(max(0.0, min(1.0, alpha)))

        panel = QPainterPath()
        panel.addRoundedRect(self.panel_rect(), RADIUS, RADIUS)
        painter.fillPath(panel, base)

        self._paint_arrows(painter)
        if self.state.current_contents() is None:
            self._paint_empty(painter)
        else:
            self._paint_source(painter)
            self._paint_text(painter)
        self._paint_counter(painter)

    def _paint_arrows(self, painter: QPainter) -> None:
        count = len(self.state.active)
        if count <= 1:
            return
        y = self.height() / 2
        painter.setPen(QPen(QColor(255, 255, 255, 110), 3.0, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        size = 9.0
        left_x = 16.0
        right_x = self.width() - 16.0
        painter.drawLine(QPoint(int(left_x + size), int(y - size)), QPoint(int(left_x), int(y)))
        painter.drawLine(QPoint(int(left_x), int(y)), QPoint(int(left_x + size), int(y + size)))
        painter.drawLine(QPoint(int(right_x - size), int(y - size)), QPoint(int(right_x), int(y)))
        painter.drawLine(QPoint(int(right_x), int(y)), QPoint(int(right_x - size), int(y + size)))

    def _paint_empty(self, painter: QPainter) -> None:
        painter.setPen(QColor(255, 255, 255, 170))
        font = QFont(self.settings["font_family"], int(self.settings["font_size"]))
        painter.setFont(font)
        rect = self.text_rect()
        painter.drawText(rect, int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop), "Nothing copied yet")

    def _paint_source(self, painter: QPainter) -> None:
        if not self.settings["show_source"] or self._clip is None or not self._clip.app:
            return
        row = QRectF(30, 16, self.width() - 60, 1.8 * BASELINE)
        painter.setPen(QColor(255, 255, 255, 150))
        small = QFont(self.settings["font_family"], max(int(self.settings["font_size"]) - 8, 8))
        painter.setFont(small)
        painter.drawText(
            row, int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter), self._clip.app
        )
        if self._clip.timestamp:
            stamp = datetime.fromtimestamp(self._clip.timestamp).strftime("%Y-%m-%d %H:%M")
            painter.drawText(
                row, int(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter), stamp
            )

    def _paint_text(self, painter: QPainter) -> None:
        contents = (self.state.current_contents() or "")[:MAX_TEXT_CHARS]
        font = QFont(self.settings["font_family"], int(self.settings["font_size"]))
        painter.setFont(font)
        painter.setPen(QColor(255, 255, 255, 235))
        rect = self.text_rect()
        flags = int(
            Qt.AlignmentFlag.AlignLeft
            | Qt.AlignmentFlag.AlignTop
            | Qt.TextFlag.TextWordWrap
        )
        painter.save()
        painter.setClipRect(rect)
        painter.drawText(rect, flags, contents)
        painter.restore()

    def _paint_counter(self, painter: QPainter) -> None:
        rect = self.counter_rect()
        pill = QPainterPath()
        pill.addRoundedRect(rect, 6, 6)
        shade = QColor(0, 0, 0, 70)
        painter.fillPath(pill, shade)
        painter.setPen(QColor(255, 255, 255, 200))
        font = QFont(self.settings["font_family"], max(int(self.settings["font_size"]) - 10, 7))
        painter.setFont(font)
        painter.drawText(rect, int(Qt.AlignmentFlag.AlignCenter), self.state.counter())

    # -- input -----------------------------------------------------------
    def keyPressEvent(self, event) -> None:  # noqa: N802
        key = KEY_NAMES.get(event.key())
        text = event.text()
        if key is None and (event.modifiers() & Qt.KeyboardModifier.ControlModifier) and event.key() == Qt.Key.Key_Comma:
            key = "prefs"
        if not key and not text:
            super().keyPressEvent(event)
            return
        result = keys.handle_key(self.state, key or "", text)
        if result.action is Action.NONE:
            super().keyPressEvent(event)
            return
        self._dispatch(result)

    def _dispatch(self, result) -> None:
        contents = self.state.current_contents()
        if result.action is Action.PASTE and contents is not None:
            self.pasteRequested.emit(contents)
        elif result.action is Action.SAVE and contents is not None:
            self.saveRequested.emit(contents, True)
        elif result.action is Action.PREFERENCES:
            self.preferencesRequested.emit()
        keys.apply_result(self.state, result)
        if result.close:
            self.dismiss()
        else:
            self.refresh()

    def wheelEvent(self, event) -> None:  # noqa: N802
        delta = -1 if event.angleDelta().y() < 0 else 1
        self._dispatch(keys.handle_key(self.state, "down" if delta > 0 else "up"))

    def mousePressEvent(self, event) -> None:  # noqa: N802
        pos = event.position()
        if pos.x() < 40:
            self._dispatch(keys.handle_key(self.state, "up"))
            return
        if pos.x() > self.width() - 40:
            self._dispatch(keys.handle_key(self.state, "down"))
            return
        contents = self.state.current_contents()
        if contents is not None and self.settings["menu_selection_pastes"]:
            self.pasteRequested.emit(contents)
            self.dismiss()

    def showEvent(self, event) -> None:  # noqa: N802
        super().showEvent(event)
        self.setFocus(Qt.FocusReason.OtherFocusReason)
