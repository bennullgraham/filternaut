from collections.abc import Iterable, Mapping

_suffixes = ("th", "st", "nd", "rd") + ("th",) * 6


def ordinal_suffix(n):
    """
    1→st, 2→nd, 3→rd, 4→th...
    """
    return _suffixes[n % 10]


def is_listlike(val):
    """
    True if `val` is "like a list".

    This is an arbitrary call. Included are 1-wide data structures you can
    iterate through (list, tuple, deque, generator), but not dicts because you
    only iterate through the keys (though the output of dict.items() *is*
    "listlike"), and not bytes or strings, because while iterating each
    character is handy, you never want to do that in the same context as
    iterating lists. Or that's my claim anyway.
    """
    return isinstance(val, Iterable) and not isinstance(val, (str, bytes, Mapping))
