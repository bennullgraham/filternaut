from collections import defaultdict, deque

from filternaut.util import is_listlike, ordinal_suffix


def test_ordinal_suffixes():
    for base in (0, 10, 20, 50, 100, 200, 500):
        assert ordinal_suffix(base + 0) == "th"
        assert ordinal_suffix(base + 1) == "st"
        assert ordinal_suffix(base + 2) == "nd"
        assert ordinal_suffix(base + 3) == "rd"
        for n in (4, 5, 6, 7, 8, 9):
            assert ordinal_suffix(base + n) == "th"
        assert ordinal_suffix(base + 10) == "th"


def test_is_listlike():
    assert is_listlike([1, 2, 3]) is True
    assert is_listlike((1, 2, 3)) is True
    assert is_listlike({1, 2, 3}) is True
    assert is_listlike(deque((1, 2, 3))) is True
    assert is_listlike(range(1, 4)) is True
    assert is_listlike((n for n in (1, 2, 3))) is True

    # a few intermediary cases for dicts. the dict itself isn't counted as
    # listlike, but its keys, values, or pairs thereof are.
    assert is_listlike({"foo": "bar"}.keys()) is True
    assert is_listlike({"foo": "bar"}.values()) is True
    assert is_listlike({"foo": "bar"}.items()) is True

    assert is_listlike(0) is False
    assert is_listlike(False) is False
    assert is_listlike({"foo": "bar"}) is False
    assert is_listlike(defaultdict(list, foo="bar")) is False
    assert is_listlike("text") is False
    assert is_listlike(b"bytes") is False
