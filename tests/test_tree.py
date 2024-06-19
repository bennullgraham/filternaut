from functools import reduce
from operator import and_, or_
from unittest import TestCase

import pytest

from filternaut import Filter, FilterTree, Optional
from filternaut.exceptions import InvalidData
from filternaut.tree import Leaf, Tree
from tests.util import NopeFilter, assert_parsed_ok


class OperatorTests(TestCase):
    def test_leaves_OR_into_trees(self):
        tree = Leaf() | Leaf()
        assert isinstance(tree, Tree)

    def test_leaves_AND_into_trees(self):
        tree = Leaf() & Leaf()
        assert isinstance(tree, Tree)

    def test_many_leaves_combine_into_tree(self):
        leaves = [Leaf() for n in range(100)]

        def operators():
            while True:
                yield or_
                yield and_

        # alternate between ORing and ANDing leaves together
        tree = reduce(lambda l, r: next(operators())(l, r), leaves)

        expected = leaves
        actual = [l for l in tree]
        assert isinstance(tree, Tree)
        assert len(expected) == len(actual)


class FilterTreeTests(TestCase):
    """
    Subclasses of Leaf and Tree should exhibit treelike behaviour.
    """

    def test_filters_OR_into_filtersets(self):
        filters = Filter("afield") | Filter("anotherfield")
        assert isinstance(filters, FilterTree)

    def test_filters_AND_into_filtersets(self):
        filters = Filter("afield") & Filter("anotherfield")
        assert isinstance(filters, FilterTree)

    def test_errors_from_filtertree(self):
        """
        FilterTree's errors should be the errors of the filters it contains.
        """
        filters = NopeFilter("one") | NopeFilter("two") | NopeFilter("three")
        with pytest.raises(InvalidData) as exc_info:
            filters.parse(dict(one=1, two=2, three=3))
        assert "one" in exc_info.value.errors
        assert "two" in exc_info.value.errors
        assert "three" in exc_info.value.errors

    def test_validity_from_filtertree(self):
        """
        FilterTree's validity should be a proxy to the validities of the
        filters it contains.
        """
        filters = Filter("one") | Filter("two") | Filter("three")
        query = filters.parse(dict())
        assert_parsed_ok(query)

    def test_Optional_combines_well(self):
        """
        Combine Optional with Filters and FilterTrees in various combinations.
        """
        f1, f2, f3, f4, f5 = map(Filter, ["1", "2", "3", "4", "5"])
        o1 = Optional(f1, f2)
        o2 = Optional(f3, f4)

        left_or = o1 | f3
        left_and = o1 & f3
        right_or = f3 | o1
        right_and = f3 & o1
        both_or = o1 | o2
        both_and = o1 & o2

        filters_list = (left_or, left_and, right_or, right_and, both_or, both_and)
        filters_with_123 = left_or, left_and, right_or, right_and
        filters_with_1234 = both_or, both_and
        for filters in filters_list:
            assert filters.__class__ == FilterTree

        for filters in filters_with_123:
            required = f1, f2, f3
            assert set(required) == set(filters)

        for filters in filters_with_1234:
            required = f1, f2, f3, f4
            assert set(required) == set(filters)
