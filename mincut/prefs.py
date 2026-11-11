"""Preferences dialog: general, appearance and shortcut settings."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QKeySequence
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QLabel,
    QLineEdit,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from .settings import Settings


class PreferencesDialog(QDialog):
    def __init__(self, settings: Settings, bezel=None, parent=None) -> None:
        super().__init__(parent)
        self.settings = settings
        self.bezel = bezel
        self.setWindowTitle("Mincut Preferences")
        self.setMinimumWidth(560)

        tabs = QTabWidget()

        # -- general -----------------------------------------------------
        general = QWidget()
        form = QFormLayout(general)

        self.remember = QSpinBox()
        self.remember.setRange(10, 999)
        self.remember.setValue(int(settings["remember_num"]))
        form.addRow("Remember the last", self.remember)

        self.favorites_remember = QSpinBox()
        self.favorites_remember.setRange(10, 999)
        self.favorites_remember.setValue(int(settings["favorites_remember_num"]))
        form.addRow("Remember the last favourites", self.favorites_remember)

        self.display_num = QSpinBox()
        self.display_num.setRange(5, 99)
        self.display_num.setValue(int(settings["display_num"]))
        form.addRow("Show in menu", self.display_num)

        self.display_len = QSpinBox()
        self.display_len.setRange(10, 200)
        self.display_len.setValue(int(settings["display_len"]))
        form.addRow("Characters in a menu item", self.display_len)

        self.dedupe = QCheckBox("Remove duplicate clippings")
        self.dedupe.setChecked(bool(settings["remove_duplicates"]))
        form.addRow("", self.dedupe)

        self.sticky = QCheckBox("Sticky bezel")
        self.sticky.setToolTip("The bezel stays visible after the hotkey is released.")
        self.sticky.setChecked(bool(settings["sticky_bezel"]))
        form.addRow("", self.sticky)

        self.wrap = QCheckBox("Wraparound bezel")
        self.wrap.setToolTip("Moving past the last item returns to the first.")
        self.wrap.setChecked(bool(settings["wraparound_bezel"]))
        form.addRow("", self.wrap)

        self.menu_pastes = QCheckBox("Menu selection pastes")
        self.menu_pastes.setChecked(bool(settings["menu_selection_pastes"]))
        form.addRow("", self.menu_pastes)

        self.save_pref = QComboBox()
        self.save_pref.addItems(["Never", "Ask", "Always"])
        self.save_pref.setCurrentIndex(int(settings["save_preference"]))
        form.addRow("Save history on exit", self.save_pref)

        # -- appearance --------------------------------------------------
        appearance = QWidget()
        app_form = QFormLayout(appearance)

        self.width = QSpinBox()
        self.width.setRange(240, 2000)
        self.width.setValue(int(settings["bezel_width"]))
        app_form.addRow("Bezel width", self.width)

        self.height = QSpinBox()
        self.height.setRange(120, 1200)
        self.height.setValue(int(settings["bezel_height"]))
        app_form.addRow("Bezel height", self.height)

        self.alpha = QDoubleSpinBox()
        self.alpha.setRange(0.15, 1.0)
        self.alpha.setSingleStep(0.05)
        self.alpha.setValue(float(settings["bezel_alpha"]))
        app_form.addRow("Bezel opacity", self.alpha)

        self.font_size = QSpinBox()
        self.font_size.setRange(8, 72)
        self.font_size.setValue(int(settings["font_size"]))
        app_form.addRow("Text size", self.font_size)

        self.show_source = QCheckBox("Show which application a clipping came from")
        self.show_source.setChecked(bool(settings["show_source"]))
        app_form.addRow("", self.show_source)

        # -- hotkeys -----------------------------------------------------
        hotkeys = QWidget()
        key_form = QFormLayout(hotkeys)
        self.main_shortcut = QLineEdit(str(settings["main_shortcut"]))
        key_form.addRow("Main hotkey", self.main_shortcut)
        self.favorites_shortcut = QLineEdit(str(settings["favorites_shortcut"]))
        key_form.addRow("Favourites hotkey", self.favorites_shortcut)
        note = QLabel(
            "On Wayland the shortcut is registered with the desktop as a custom "
            "keyboard shortcut pointing at <b>mincut toggle</b>."
        )
        note.setWordWrap(True)
        note.setTextFormat(Qt.TextFormat.RichText)
        key_form.addRow("", note)
        self.paste_simulation = QCheckBox("Press Ctrl+V after choosing a clipping")
        self.paste_simulation.setChecked(bool(settings["paste_simulation"]))
        key_form.addRow("", self.paste_simulation)

        tabs.addTab(general, "General")
        tabs.addTab(appearance, "Appearance")
        tabs.addTab(hotkeys, "Hotkey")

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(tabs)
        layout.addWidget(buttons)

    def accept(self) -> None:
        s = self.settings
        s["remember_num"] = self.remember.value()
        s["favorites_remember_num"] = self.favorites_remember.value()
        s["display_num"] = self.display_num.value()
        s["display_len"] = self.display_len.value()
        s["remove_duplicates"] = self.dedupe.isChecked()
        s["sticky_bezel"] = self.sticky.isChecked()
        s["wraparound_bezel"] = self.wrap.isChecked()
        s["menu_selection_pastes"] = self.menu_pastes.isChecked()
        s["save_preference"] = self.save_pref.currentIndex()
        s["bezel_width"] = self.width.value()
        s["bezel_height"] = self.height.value()
        s["bezel_alpha"] = round(self.alpha.value(), 2)
        s["font_size"] = self.font_size.value()
        s["show_source"] = self.show_source.isChecked()
        s["main_shortcut"] = self.main_shortcut.text().strip() or "Ctrl+Shift+V"
        s["favorites_shortcut"] = self.favorites_shortcut.text().strip() or "Ctrl+Shift+F"
        s["paste_simulation"] = self.paste_simulation.isChecked()
        super().accept()
