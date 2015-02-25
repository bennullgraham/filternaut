# -*- coding: utf8 -*-

from __future__ import unicode_literals
from copy import deepcopy
from operator import and_

from django.core.exceptions import ValidationError
from django.db.models import Q
import six

from filternaut.tree import Tree, Leaf


class FilterTree(Tree):
    """
    FilterTrees instances are the result of ORing or ANDing Filter instances,
    or other FilterTree instances, together.

    FilterTree provides a simple API for dealing with a set of filters. They
    may also be iterated over to gain access to the Filter instances directly.
    """

    def __init__(self, negate=False, *args, **kwargs):
        self.negate = negate
        super(FilterTree, self).__init__(*args, **kwargs)

    def __invert__(self):
        inverted = deepcopy(self)
        inverted.negate = not self.negate
        return inverted

    @property
    def valid(self):
        """
        A boolean indicating whether all filters parsed successfully. Cannot be
        read before ``parse()`` has been called.
        """
        return not self.errors

    @property
    def errors(self):
        """
        A dictionary of errors met while parsing. The errors are keyed by their
        field's source value. Each key's value is a list of errors.

        ``errors`` cannot be read before ``parse()`` has been called.
        """
        errors = {}
        for filter in self:
            errors.update(filter.errors or {})
        return errors

    @property
    def Q(self):
        """
        A Django "Q" object, built by combining input data with the filter
        definitions. Cannot be read before ``parse()`` has been called.
        """
        qs = self.left.Q, self.right.Q

        # 'empty' Filters generate empty Q objects. These don't falsify other Q
        # objects to which they are ANDed, so we simulate that behaviour here.
        # In other words, Q(<real query>) & Q() == Q(<real query>), whereas we
        # want it to == Q().
        if self.operator == and_ and not all(qs):
            q = Q()
        else:
            q = self.operator(*qs)

        return ~q if self.negate else q

    def parse(self, data):
        for filter in self:
            filter.parse(data)


class Filter(Leaf):
    """
    A Filter instance builds a django.db.models.Q object by pulling a value
    from arbitrary native data, e.g. a set of query params.

    It can be ORed or ANDed together with other Filter instances in the same
    way Q objects can.
    """

    tree_class = FilterTree

    def __init__(self, dest, **kwargs):
        self.dest = dest
        self.source = kwargs.get('source', dest)
        self.lookups = kwargs.get('lookups', ['exact'])
        self.required = kwargs.get('required', False)
        self.negate = kwargs.get('negate', False)

        # None is a valid default -- consider exclude(groups=None) -- so use
        # the absence or presence of self.default to indicate whether a default
        # should be used.
        if 'default' in kwargs:
            self.default = kwargs['default']
            self.default_lookup = kwargs.get('default_lookup', 'exact')

        self._filters = {}
        self._errors = {}
        self.parsed = False

        # lazy folk can provide a single lookup as a string.
        if isinstance(self.lookups, six.string_types):
            self.lookups = [self.lookups, ]

    def __invert__(self):
        """
        Invert the sense of this filter.
        """
        inverted = deepcopy(self)
        inverted.negate = not self.negate
        return inverted

    def make_source_dest_pair(self, lookup):
        """
        Take a 'lookup' value, such as 'contains' or 'lte', and combine it with
        this field's source, returning e.g. username__contains.

        If lookup is None, the raw 'source' is returned.
        """
        if lookup in (None, 'exact'):
            source = self.source
            dest = self.dest
        else:
            source = '{}__{}'.format(self.source, lookup)
            dest = '{}__{}'.format(self.dest, lookup)
        return source, dest

    def parse(self, data):
        """
        Look through the provided dict-like data for keys which match this
        Filter's source.  This includes keys containg lookup affixes such as
        'contains' or 'lte'.

        Once this method has been called, the ``errors``, ``valid`` and ``Q``
        attributes become usable.
        """
        self._filters, self._errors = self.get_q_kwargs(data)
        self.parsed = True

    def clean(self, value):
        """
        Validate and normalise ``value`` for use in filtering. This
        implementation is a no-op; subclasses may do more work here.
        """
        return value

    def get_q_kwargs(self, data):
        """
        Look through ``data`` for keys which match any of the source /
        source__lookup values for this Filter. Any present are cleaned and kept
        for filtering. Errors are likewise kept.

        Returns a dictionary of filters keyed by dest (suitable for unpacking
        into a Q constructor) and a dictionary of errors, keyed by source.
        """
        filters, errors = {}, {}
        for lookup in self.lookups:
            source, dest = self.make_source_dest_pair(lookup)
            try:
                value = self.get_source_value(source, data)
                filters[dest] = self.clean(value)
            except KeyError:
                pass
            except ValidationError as ex:
                errors[source] = ex.messages

        # Use a default if there were no filters.
        if not filters and hasattr(self, 'default'):
            filters = self.make_default_filter()

        # If there are still no filters but this filter is required, that's an
        # error.
        if not filters and self.required:
            errors[self.source] = ['This field is required']

        return filters, errors

    def make_default_filter(self):
        """
        Construct a default filter dictionary to be used if no source data was
        found during parsing.
        """
        dest = '{}__{}'.format(self.dest, self.default_lookup)
        return {dest: self.default}

    def get_source_value(self, key, data):
        """
        Pull ``key`` from ``data``. This implementation is trivial, but
        subclasses may want to perform non-trivial inspections of ``data`` and
        can subclass here to do so.
        """
        return data[key]

    @property
    def valid(self):
        """
        A boolean indicating whether this Filter registered any errors during
        parsing. Raises a ValueError if ``parse()`` has not been called.
        """
        if not self.parsed:
            raise ValueError(
                "Must call parse() on filters before checking validity")
        return not self._errors

    @property
    def errors(self):
        """
        A dictionary of errors (keyed by source) listing any problems
        encountered during parsing. Typical entries include validation errors
        and failures to provide values where required.  Raises a ValueError if
        ``parse()`` has not been called.
        """
        if not self.parsed:
            raise ValueError(
                "Must call parse() on filters before reading errors")
        if not self._errors:
            return None
        else:
            return self._errors

    @property
    def Q(self):
        """
        A Django "Q" object, built by combining input data with this filter's
        definition. Cannot be read before ``parse()`` has been called.
        """
        if not self.parsed:
            raise ValueError(
                "Must call parse() on filters before using Q")
        q = Q(**self._filters)
        return ~q if self.negate else q
