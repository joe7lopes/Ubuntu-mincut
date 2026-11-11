import pytest

from mincut.store import Clip, Store


def make(n=5, store=None):
    store = store or Store()
    for i in range(n):
        store.add(f"item {i}", timestamp=i)
    return store


def test_newest_first():
    s = make(3)
    assert s.contents_at(0) == "item 2"
    assert s.contents_at(2) == "item 0"


def test_empty_ignored():
    s = Store()
    assert s.add("") is False
    assert len(s) == 0


def test_duplicates_move_to_top():
    s = make(3)
    s.add("item 0")
    assert len(s) == 3
    assert s.contents_at(0) == "item 0"


def test_duplicates_kept_when_disabled():
    s = Store(remove_duplicates=False)
    s.add("a")
    s.add("a")
    assert len(s) == 2


def test_trim_to_remember_num():
    s = Store(remember_num=4)
    for i in range(10):
        s.add(str(i))
    assert len(s) == 4
    assert s.contents_at(0) == "9"
    assert s.contents_at(3) == "6"


def test_shrinking_remember_num_trims():
    s = make(10)
    s.set_remember_num(3)
    assert len(s) == 3


def test_clear_item_and_move_to_top():
    s = make(3)
    assert s.clear_item(1) is True
    assert s.contents_at(1) == "item 0"
    s.add("new")
    assert s.move_to_top(2) is True
    assert s.contents_at(0) == "item 0"


def test_clear():
    s = make(3)
    s.clear()
    assert len(s) == 0
    assert s.contents_at(0) is None


def test_merge_oldest_to_newest():
    s = make(3)
    s.merge()
    assert s.contents_at(0) == "item 0\nitem 1\nitem 2"


def test_display_string_first_line_and_truncation():
    c = Clip("  hello world\nsecond line  ")
    assert c.display(40) == "hello world"
    assert c.display(5) == "hello\u2026"


def test_display_strings_and_indexes_with_search():
    s = Store()
    s.add("alpha one")
    s.add("beta two")
    s.add("ALPHA three")
    assert s.display_strings(10) == ["ALPHA three", "beta two", "alpha one"]
    assert s.display_strings(10, "alpha") == ["ALPHA three", "alpha one"]
    assert s.indexes(10, "alpha") == [0, 2]
    assert s.indexes(2) == [0, 1]


def test_roundtrip_persistence():
    s = make(3)
    s.add("dup", timestamp=9, app="Terminal")
    clone = Store.from_dict(s.to_dict())
    assert [c.contents for c in clone] == [c.contents for c in s]
    assert clone.contents_at(0) == "dup"
    assert clone.app_at(0) == "Terminal"
