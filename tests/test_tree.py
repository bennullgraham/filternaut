# -*- coding: utf8 -*-

from __future__ import unicode_literals, print_function, absolute_import
from unittest import TestCase
from operator import or_, and_

from django.core.exceptions import ValidationError
from six.moves import reduce

from filternaut.tree import Leaf, Tree
from filternaut import Filter, FilterTree
from tests import flatten_qobj


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
        filters = Filter('afield') | Filter('anotherfield')
        assert isinstance(filters, FilterTree)

    def test_filters_AND_into_filtersets(self):
        filters = Filter('afield') & Filter('anotherfield')
        assert isinstance(filters, FilterTree)

    def test_ANDed_filters_must_all_be_present(self):
        """
        If one of several ANDed sibling-filters parsed no value, none of those
        filters should partake in the final Q.
        """
        filters = Filter('one') & Filter('two') & Filter('three')
        filters.parse(dict(one=1))
        assert bool(filters.Q) == False  # two and three missing

        filters.parse(dict(one=1, two=2))
        assert bool(filters.Q) == False  # three missing

        filters.parse(dict(two=2, three=3))
        assert bool(filters.Q) == False  # one missing

        filters.parse(dict(one=1, two=2, three=3))
        assert bool(filters.Q) == True  # all present

    def test_ANDed_filters_must_all_be_present_while_OR_is_unaffected(self):
        """
        If one of several ANDed sibling-filters parsed no value, none of those
        filters should partake in the final Q. ORed filters are unaffected.
        """
        filters = (Filter('one') & Filter('two')) | Filter('three')

        filters.parse(dict(one=1, three=3))
        actual = dict(flatten_qobj(filters.Q))
        assert 'one' not in actual
        assert 'two' not in actual
        assert 'three' in actual

        filters.parse(dict(two=2))
        actual = dict(flatten_qobj(filters.Q))
        assert 'one' not in actual
        assert 'two' not in actual
        assert 'three' not in actual

        filters.parse(dict(one=1, two=2, three=3))
        actual = dict(flatten_qobj(filters.Q))
        assert 'one' in actual
        assert 'two' in actual
        assert 'three' in actual

    def test_errors_from_filtertree(self):
        class NopeFilter(Filter):
            def clean(self, value):
                raise ValidationError("Nope")
        filters = NopeFilter('one') | NopeFilter('two') | NopeFilter('three')
        filters.parse(dict(one=1, two=2, three=3))
        assert 'one' in filters.errors
        assert 'two' in filters.errors
        assert 'three' in filters.errors
        assert not filters.valid

    def test_validity_from_filtertree(self):
        filters = Filter('one') | Filter('two') | Filter('three')
        filters.parse(dict())
        assert filters.valid
