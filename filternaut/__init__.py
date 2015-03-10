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
        errors = self.left.errors
        errors.update(self.right.errors)
        return errors

    @property
    def Q(self):
        """
        A Django "Q" object, built by combining input data with the filter
        definitions. Cannot be read before ``parse()`` has been called.
        """
        q = self.operator(self.left.Q, self.right.Q)
        return ~q if self.negate else q

    def parse(self, data):
        """
        Ask all filters to look through ``data`` and thereby configure
        themselves.
        """
        for fltr in self:
            fltr.parse(data)


class Optional(FilterTree):
    """
    Filters included underneath Optional have their required=True configuration
    ignored as long as all those filters are missing. If some but not all are
    present, then required=True is observed, and those filters that are missing
    become invalid. If all filters under Optional have valid source data, they
    are valid as a whole.

    This is useful for situations where you want to require one field if
    another is present. For example, requiring ``last_name`` if ``first_name``
    is present, but also allowing neither. In this case, you would mark both
    with required=True, and wrap them in Optional:

        Optional(
            Filter('first_name', required=True),
            Filter('last_name', required=True))

    Generally, filters underneath Optional will have required=True, however it
    isn't necessary; consider adding 'middle name' to the above example.
    """

    tree_class = FilterTree

    def __init__(self, left, *rest):
        operator = and_  # OR does not make sense with group-require
        if not rest:
            # TODO if left is a tree, walk it instead of complaining
            raise ValueError("Optional has no effect on a single filter")
        right = six.moves.reduce(and_, rest)
        super(Optional, self).__init__(False, operator, left, right)

    @property
    def errors(self):
        errors = super(Optional, self).errors
        filters = list(self)
        missing = [f.missing for f in filters if f.required]
        present = [f.dict for f in filters]

        # some filters have values, but not all required filters have values.
        if any(missing) and any(present) and not all(present):
            # insert an additional error
            sources = sorted([f.source for f in filters])
            if '__all__' not in errors:
                errors['__all__'] = []
            errors['__all__'].append(
                'If any of {} are provided, all must be '
                'provided'.format(', '.join(sources)))
        else:
            for f in filters:
                if f.required and f.missing:
                    del errors[f.source]

        return errors


class Filter(Leaf):
    """
    A Filter instance builds a django.db.models.Q object by pulling a value
    from arbitrary native data, e.g. a set of query params.

    It can be ORed or ANDed together with other Filter instances in the same
    way Q objects can.
    """

    #: Filters combine into FilterTree instances
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
        self.missing = False

        # accept lookups as a comma-separated string.
        if isinstance(self.lookups, six.string_types):
            self.lookups = self.lookups.split(',')

    def __invert__(self):
        """
        Invert the sense of this filter.
        """
        inverted = deepcopy(self)
        inverted.negate = not self.negate
        return inverted

    def parse(self, data):
        """
        Look through the provided dict-like data for keys which match this
        Filter's source.  This includes keys containg lookup affixes such as
        'contains' or 'lte'.

        Once this method has been called, the ``errors``, ``valid`` and ``Q``
        attributes become usable.
        """
        source_pairs = self.source_value_pairs(data)
        dest_pairs, errors = self.dest_value_pairs(source_pairs)

        # handle default value
        if not source_pairs and hasattr(self, 'default'):
            dest_pairs = (self.default_dest_value_pair(), )

        # if required, check if satisfied
        if not source_pairs and self.required:
            self.missing = True
            if self.source not in errors:
                errors[self.source] = []
            errors[self.source].append('This field is required')
        else:
            # this allows a later parse() to undo an earlier missing=True
            self.missing = False

        self.parsed = True
        self._filters = dict(dest_pairs)
        self._errors = errors

    def clean(self, value):
        """
        Validate and normalise ``value`` for use in filtering. This
        implementation is a no-op; subclasses may do more work here.
        """
        return value

    def source_dest_pairs(self):
        """
        For each lookup in self.lookups, such as 'contains' or 'lte', combine
        it with this field's source and dest, returning e.g.
        (username__contains, account_name__contains)

        If any lookup is None, that pair becomes (source, dest)

        If there is only one lookup, two pairs are listed containing the source
        both with and without the lookup. This allows source data to omit the
        lookup from the key, e.g. providing 'email' to the filter
        Filter('email', lookups=['iexact']).
        """
        pairs = []
        for lookup in self.lookups:
            if lookup in (None, 'exact'):
                source = self.source
                dest = self.dest
            else:
                source = '{}__{}'.format(self.source, lookup)
                dest = '{}__{}'.format(self.dest, lookup)
            pairs.append((source, dest))

        # allow source data to omit the lookup if only one lookup listed.
        if len(pairs) == 1:
            lookup = self.lookups[0]
            if lookup not in (None, 'exact'):
                dest = '{}__{}'.format(self.dest, self.lookups[0])
                pairs.append((self.source, dest))

        return pairs

    def source_value_pairs(self, data):
        """
        Return a list of two-tuples containing valid sources for this filter --
        made by combining this filter's source and the various lookups -- and
        their values, as pulled from the data handed to parse.

        Sources with no found value are excluded.
        """
        pairs = []
        for source, dest in self.source_dest_pairs():
            try:
                many = dest.endswith('__in')
                value = self.get_source_value(source, data, many)
                pairs.append((source, value))
            except KeyError:
                pass
        return pairs

    def dest_value_pairs(self, sourcevalue_pairs):
        """
        Return two values:
            - A list of two-tuples containing dests (ORM relation/field names)
              and their values.
            - A dictionary of errors, keyed by the source which they originated
              from.
        """
        sourcedest_map = dict(self.source_dest_pairs())
        pairs = []
        errors = {}
        for source, value in sourcevalue_pairs:
            try:
                value = self.clean(value)
                dest = sourcedest_map[source]
                pairs.append((dest, value))
            except ValidationError as ex:
                errors[source] = ex.messages
        return pairs, errors

    def default_dest_value_pair(self):
        """
        Construct a default dest/value pair to be used if no source data was
        found during parsing (and if this filter has default=True).
        """
        dest = '{}__{}'.format(self.dest, self.default_lookup)
        return (dest, self.default)

    def get_source_value(self, key, data, many=False):
        """
        Pull ``key`` from ``data``.

        When ``many`` is True, a list of values is returned. Otherwise, a
        single value is returned.
        """
        if many is False:
            return data[key]
        elif hasattr(data, 'getlist'):  # Django querydict, multivaluedict
            if key not in data:
                raise KeyError(repr(key))
            return data.getlist(key)
        else:
            # only a single value, but many=True, so return as list.
            return [data[key]]

    @property
    def dict(self):
        """
        A dictionary representation of this Filter's filter configuration.
        Cannot be read before ``parse()`` has been called.
        """
        if not self.parsed:
            raise ValueError(
                "Must call parse() on this filter before "
                "accessing this attribute")
        return self._filters

    @property
    def valid(self):
        """
        A boolean indicating whether this Filter registered any errors during
        parsing. Raises a ValueError if ``parse()`` has not been called.
        """
        if not self.parsed:
            raise ValueError(
                "Must call parse() on this filter before checking validity")
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
                "Must call parse() on this filter before reading errors")
        return self._errors

    @property
    def Q(self):
        """
        A Django "Q" object, built by combining input data with this filter's
        definition. Cannot be read before ``parse()`` has been called.
        """
        if not self.parsed:
            raise ValueError(
                "Must call parse() on this filter before using Q")
        q = Q(**self.dict)
        return ~q if self.negate else q
