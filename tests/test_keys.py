from mincut.keys import Action, BezelState, apply_result, handle_key
from mincut.store import Store


def state(n=5, favorites=None, wraparound=False):
    s = Store()
    for i in range(n):
        s.add(f"item {i}")
    return BezelState(s, favorites or Store(), wraparound=wraparound)


def test_down_moves_to_older_and_up_back():
    st = state()
    assert handle_key(st, "down").position == 1
    assert handle_key(st, "right").position == 2
    assert handle_key(st, "up").position == 1
    assert handle_key(st, "left").position == 0


def test_navigation_clamps_without_wraparound():
    st = state(3)
    for _ in range(10):
        handle_key(st, "down")
    assert st.position == 2
    for _ in range(10):
        handle_key(st, "up")
    assert st.position == 0


def test_wraparound():
    st = state(3, wraparound=True)
    handle_key(st, "up")
    assert st.position == 2
    handle_key(st, "down")
    assert st.position == 0


def test_home_end_and_page_keys():
    st = BezelState(Store(remember_num=25), Store())
    for i in range(25):
        st.store.add(f"item {i}")
    handle_key(st, "end")
    assert st.position == 24
    handle_key(st, "home")
    assert st.position == 0
    handle_key(st, "pagedown")
    assert st.position == 10
    handle_key(st, "pageup")
    assert st.position == 0


def test_number_jump_and_zero_is_ten():
    st = state(12)
    handle_key(st, "", text="3")
    assert st.position == 2
    handle_key(st, "", text="0")
    assert st.position == 9


def test_number_jump_past_end_stops_at_last():
    st = state(2)
    handle_key(st, "", text="7")
    assert st.position == 1


def test_return_pastes_and_closes():
    st = state()
    r = handle_key(st, "return")
    assert r.action is Action.PASTE and r.close


def test_enter_moves_to_top():
    st = state()
    r = handle_key(st, "enter")
    apply_result(st, r)
    assert st.store.contents_at(0) == "item 4"


def test_escape_closes_keeping_position():
    st = state()
    handle_key(st, "down")
    r = handle_key(st, "escape")
    assert r.close and st.position == 1


def test_delete_removes_current_and_closes():
    st = state(3)
    handle_key(st, "down")
    apply_result(st, handle_key(st, "backspace"))
    assert [c.contents for c in st.store] == ["item 2", "item 0"]


def test_f_toggles_favorites_store():
    st = state()
    r = handle_key(st, "", text="f")
    assert r.action is Action.TOGGLE_FAVORITES
    assert st.favorites_mode is True
    handle_key(st, "", text="f")
    assert st.favorites_mode is False


def test_shift_f_moves_current_into_favorites():
    st = state()
    handle_key(st, "down")
    apply_result(st, handle_key(st, "", text="F"))
    assert st.favorites.contents_at(0) == "item 3"
    assert st.store.contents_at(1) == "item 2"


def test_s_is_save_shift_s_also_save():
    st = state()
    assert handle_key(st, "", text="s").action is Action.SAVE
    assert handle_key(st, "", text="S").action is Action.SAVE


def test_counter_text():
    st = state(4)
    handle_key(st, "down")
    assert st.counter() == "2 of 4"
    st.store.clear()
    assert st.counter() == "Empty"


def test_empty_store_is_harmless():
    st = BezelState(Store())
    for k in ("down", "up", "end", "home", "pagedown"):
        handle_key(st, k)
    assert st.position == 0
    assert st.current_contents() is None
