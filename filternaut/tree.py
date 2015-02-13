# -*- coding: utf8 -*-

from __future__ import unicode_literals, print_function, absolute_import
from operator import or_, and_

"""
This module ends up looking similar to django.utils.tree. It has a simpler
design allowed by the simpler use case. In particular there are
only ever two children, `left' and `right', which in turn allows the 'operator'
(what django terms a 'connector') to be literally a function from stdlib's
operator.

Finally, there are separate leaf and tree classes. This increases sanity when
these classes are extended in filternaut.filters.
"""


class Tree(object):

    def __init__(self, left, right, operator):
        assert operator in (or_, and_)
        self.left = left
        self.right = right
        self.operator = operator

    def __iter__(self):
        for l in self.left:
            yield l
        for r in self.right:
            yield r

    def __and__(self, other):
        return self.__class__(left=self, right=other, operator=and_)

    def __or__(self, other):
        return self.__class__(left=self, right=other, operator=or_)


class Leaf(object):

    # subclasses could specify a tree-subclass here. e.g. MyLeaf.tree_class =
    # MyTree.
    tree_class = Tree

    def __iter__(self):
        yield self

    def __and__(self, other):
        return self.tree_class(left=self, right=other, operator=and_)

    def __or__(self, other):
        return self.tree_class(left=self, right=other, operator=or_)
