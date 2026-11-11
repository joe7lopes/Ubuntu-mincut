"""Key handling for the bezel.

The bezel is keyboard-only: every keystroke maps to one action against the
active store.  All of that logic lives here, free of any GUI dependency, so it
can be tested without a display.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional

from .store import Store


class Action(str, Enum):
    NONE = "none"
    NAVIGATE = "navigate"
    PASTE = "paste"
    CLOSE = "close"
    MOVE_TO_TOP = "move_to_top"
    PREFERENCES = "preferences"
    DELETE = "delete"
    SAVE = "save"
    TOGGLE_FAVORITES = "toggle_favorites"
    FAVORITE = "favorite"


@dataclass
class KeyResult:
    action: Action
    position: int
    close: bool = False

    @property
    def position_changed(self) -> bool:
        return self.action is Action.NAVIGATE


class BezelState:
    """Position inside one store, with the two stores at hand."""

    def __init__(
        self,
        store: Store,
        favorites: Optional[Store] = None,
        display_num: int = 10,
        wraparound: bool = False,
    ) -> None:
        self.store = store
        self.favorites = favorites if favorites is not None else Store()
        self.display_num = display_num
        self.wraparound = wraparound
        self.favorites_mode = False
        self.position = 0

    # -- active store ----------------------------------------------------
    @property
    def active(self) -> Store:
        return self.favorites if self.favorites_mode else self.store

    def sync_display_len(self, display_len: int) -> None:
        self.store.set_display_len(display_len)
        self.favorites.set_display_len(display_len)

    def clamp(self) -> None:
        count = len(self.active)
        if count == 0:
            self.position = 0
        else:
            self.position = min(self.position, count - 1)

    def current_contents(self) -> Optional[str]:
        return self.active.contents_at(self.position)

    def counter(self) -> str:
        count = len(self.active)
        if count == 0:
            return "Empty"
        return f"{self.position + 1} of {count}"

    def toggle_favorites(self) -> None:
        self.favorites_mode = not self.favorites_mode
        self.position = 0

    # -- navigation ------------------------------------------------------
    def move(self, delta: int) -> None:
        count = len(self.active)
        if count == 0:
            return
        target = self.position + delta
        if self.wraparound:
            self.position = target % count
        else:
            self.position = max(0, min(count - 1, target))


def _nav(state: BezelState, delta: int) -> KeyResult:
    state.move(delta)
    return KeyResult(Action.NAVIGATE, state.position)


def handle_key(state: BezelState, key: str, text: str = "") -> KeyResult:
    """Translate one key event into an action.

    ``key`` is a normalised key name: "up", "down", "left", "right", "return",
    "enter", "escape", "home", "end", "pageup", "pagedown", "backspace",
    "delete", "prefs", or a single printable character in ``text``.
    """
    pos = state.position

    if key in ("down", "right"):
        return _nav(state, +1)
    if key in ("up", "left"):
        return _nav(state, -1)
    if key == "home":
        state.position = 0
        return KeyResult(Action.NAVIGATE, 0)
    if key == "end":
        state.position = max(len(state.active) - 1, 0)
        return KeyResult(Action.NAVIGATE, state.position)
    if key == "pagedown":
        return _nav(state, +10)
    if key == "pageup":
        return _nav(state, -10)
    if key == "return":
        return KeyResult(Action.PASTE, pos, close=True)
    if key in ("enter", "kp_enter"):
        return KeyResult(Action.MOVE_TO_TOP, pos, close=True)
    if key == "escape":
        return KeyResult(Action.CLOSE, pos, close=True)
    if key == "prefs":
        return KeyResult(Action.PREFERENCES, pos, close=True)
    if key in ("backspace", "delete"):
        return KeyResult(Action.DELETE, pos, close=True)

    if len(text) == 1:
        if text in "123456789":
            state.position = min(int(text) - 1, max(len(state.active) - 1, 0))
            return KeyResult(Action.NAVIGATE, state.position)
        if text == "0":
            state.position = min(9, max(len(state.active) - 1, 0))
            return KeyResult(Action.NAVIGATE, state.position)
        if text == "s":
            return KeyResult(Action.SAVE, pos, close=True)
        if text == "S":
            return KeyResult(Action.SAVE, pos, close=True)
        if text == "f":
            state.toggle_favorites()
            return KeyResult(Action.TOGGLE_FAVORITES, state.position)
        if text == "F":
            return KeyResult(Action.FAVORITE, pos, close=True)

    return KeyResult(Action.NONE, pos)


def apply_result(state: BezelState, result: KeyResult, save_and_delete: bool = False) -> Optional[str]:
    """Mutate the stores for the actions that change them; return a message.

    PASTE is deliberately left to the caller: it needs the clipboard and the
    focus of whatever window was active before the bezel opened.
    """
    if result.action is Action.MOVE_TO_TOP:
        state.active.move_to_top(result.position)
        state.position = 0
        return None
    if result.action is Action.DELETE:
        state.active.clear_item(result.position)
        state.clamp()
        return None
    if result.action is Action.FAVORITE:
        contents = state.active.contents_at(result.position)
        if contents is None:
            return None
        state.favorites.add(contents, app=state.active.app_at(result.position) or "")
        state.active.clear_item(result.position)
        state.clamp()
        return None
    if result.action is Action.TOGGLE_FAVORITES:
        state.clamp()
        return None
    return None
