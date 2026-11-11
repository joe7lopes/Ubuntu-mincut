"""Clipboard history storage for Mincut.

The store keeps a newest-first list of clips plus a separate favourites list.
A clip is plain text plus a timestamp; the *display string* is the first line,
trimmed, truncated to the configured display length.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, List, Optional


ELLIPSIS = "\u2026"


@dataclass
class Clip:
    contents: str
    timestamp: int = 0
    app: str = ""

    def first_line(self) -> str:
        return self.contents.strip().splitlines()[0] if self.contents.strip() else ""

    def display(self, display_len: int) -> str:
        line = self.first_line()
        if display_len > 0 and len(line) > display_len:
            return line[:display_len] + ELLIPSIS
        return line

    def to_dict(self) -> dict:
        return {"contents": self.contents, "timestamp": self.timestamp, "app": self.app}

    @classmethod
    def from_dict(cls, data: dict) -> "Clip":
        return cls(
            contents=str(data.get("contents", "")),
            timestamp=int(data.get("timestamp", 0)),
            app=str(data.get("app", "")),
        )


@dataclass
class Store:
    remember_num: int = 20
    display_len: int = 40
    remove_duplicates: bool = True
    _clips: List[Clip] = field(default_factory=list)

    # -- queries ---------------------------------------------------------
    def __len__(self) -> int:
        return len(self._clips)

    def __iter__(self) -> Iterable[Clip]:
        return iter(self._clips)

    def clips(self) -> List[Clip]:
        return list(self._clips)

    def contents_at(self, index: int) -> Optional[str]:
        if 0 <= index < len(self._clips):
            return self._clips[index].contents
        return None

    def display_at(self, index: int) -> Optional[str]:
        if 0 <= index < len(self._clips):
            return self._clips[index].display(self.display_len)
        return None

    def app_at(self, index: int) -> Optional[str]:
        if 0 <= index < len(self._clips):
            return self._clips[index].app
        return None

    def index_of(self, contents: str) -> int:
        for i, clip in enumerate(self._clips):
            if clip.contents == contents:
                return i
        return -1

    def display_strings(self, count: int, search: str = "") -> List[str]:
        """Newest-first list of display strings, optionally filtered."""
        if search:
            needle = search.lower()
            out = [c.display(self.display_len) for c in self._clips if needle in c.contents.lower()]
            return out[:count]
        return [c.display(self.display_len) for c in self._clips[:count]]

    def indexes(self, count: int, search: str = "") -> List[int]:
        """Newest-first indexes of items matching an optional search."""
        if search:
            needle = search.lower()
            out = [i for i, c in enumerate(self._clips) if needle in c.contents.lower()]
            return out[:count]
        return list(range(min(count, len(self._clips))))

    # -- mutation --------------------------------------------------------
    def add(self, contents: str, timestamp: int = 0, app: str = "", at_index: int = 0) -> bool:
        if not contents:
            return False
        clip = Clip(contents=contents, timestamp=timestamp, app=app)
        existing = self.index_of(contents)
        if existing >= 0 and self.remove_duplicates:
            self._clips.pop(existing)
            if existing < at_index:
                at_index -= 1
        if at_index >= len(self._clips):
            self._clips.append(clip)
        else:
            self._clips.insert(max(at_index, 0), clip)
        self._trim()
        return True

    def clear(self) -> None:
        self._clips.clear()

    def clear_item(self, index: int) -> bool:
        if 0 <= index < len(self._clips):
            self._clips.pop(index)
            return True
        return False

    def move_to_top(self, index: int) -> bool:
        if 0 <= index < len(self._clips) and index != 0:
            self._clips.insert(0, self._clips.pop(index))
            return True
        return False

    def merge(self, timestamp: int = 0) -> bool:
        """Join every clip oldest-to-newest into a single new clip."""
        if not self._clips:
            return False
        merged = "\n".join(c.contents for c in reversed(self._clips))
        return self.add(merged, timestamp=timestamp, app="Merge")

    def set_remember_num(self, value: int) -> None:
        if value > 0:
            self.remember_num = value
            self._trim()

    def set_display_len(self, value: int) -> None:
        if value > 0:
            self.display_len = value

    def _trim(self) -> None:
        while len(self._clips) > self.remember_num:
            self._clips.pop()

    # -- persistence -----------------------------------------------------
    def to_dict(self) -> dict:
        return {
            "remember_num": self.remember_num,
            "display_len": self.display_len,
            "remove_duplicates": self.remove_duplicates,
            "clips": [c.to_dict() for c in self._clips],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Store":
        store = cls(
            remember_num=int(data.get("remember_num", 20)),
            display_len=int(data.get("display_len", 40)),
            remove_duplicates=bool(data.get("remove_duplicates", True)),
        )
        store._clips = [Clip.from_dict(c) for c in data.get("clips", []) if c.get("contents")]
        store._trim()
        return store
