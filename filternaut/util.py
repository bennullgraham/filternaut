from collections.abc import Iterable


def is_listlike(val):
    """
    True if `val` is an iterable (list, tuple, ...) but not a string
    """
    return isinstance(val, Iterable) and not isinstance(val, str)
