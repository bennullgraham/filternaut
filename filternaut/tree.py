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
these classes are extended to become filters.
"""


class Tree(object):

    # subclasses could specify a tree-subclass here. For example,
    # MyLeaf.tree_class = MyTree. A value of None will default to the current
    # class at the time of construction.
    tree_class = None

    def __init__(self, operator, left, right):
        assert operator in (or_, and_)
        self.operator = operator
        self.left = left
        self.right = right

    def __iter__(self):
        for l in self.left:
            yield l
        for r in self.right:
            yield r

    def __and__(self, other):
        klass = getattr(self, 'tree_class') or self.__class__
        return klass(operator=and_, left=self, right=other)

    def __or__(self, other):
        klass = getattr(self, 'tree_class') or self.__class__
        return klass(operator=or_, left=self, right=other)


class Leaf(object):

    # subclasses could specify a tree-subclass here. For example,
    # MyLeaf.tree_class = MyTree.
    tree_class = Tree

    def __iter__(self):
        yield self

    def __and__(self, other):
        return self.tree_class(operator=and_, left=self, right=other)

    def __or__(self, other):
        return self.tree_class(operator=or_, left=self, right=other)
