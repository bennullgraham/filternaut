from collections import defaultdict, namedtuple
from copy import deepcopy
from functools import reduce
from operator import and_, or_

from django.core.exceptions import ValidationError
from django.db.models import Q

from filternaut.exceptions import InvalidData
from filternaut.tree import Leaf, Tree
from filternaut.util import is_listlike


class FilterTree(Tree):
    """
    FilterTrees instances are the result of ORing or ANDing Filter instances,
    or other FilterTree instances, together.

    FilterTree provides a simple API for dealing with a set of filters. They
    may also be iterated over to gain access to the Filter instances directly.
    """

    def __init__(self, negate=False, *args, **kwargs):
        self.negate = negate
        super().__init__(*args, **kwargs)

    def __invert__(self):
        inverted = deepcopy(self)
        inverted.negate = not self.negate
        return inverted

    def __repr__(self):
        children = ", ".join(f.source for f in self)
        return f"<{type(self).__name__} {children}>"

    def parse(self, data):
        """
        Ask all filters to look through ``data`` and thereby configure
        themselves.
        """
        errors = {}
        # do this with two try/except so we can collect errors from both
        # branches
        try:
            left_q = self.left.parse(data)
        except InvalidData as ex:
            errors.update(ex.errors)

        try:
            right_q = self.right.parse(data)
        except InvalidData as ex:
            errors.update(ex.errors)

        if errors:
            raise InvalidData(errors=errors)

        return self.operator(left_q, right_q)


class Constraint(FilterTree):
    """
    Base class for making collective rules over several filters.

    For example, at least two of the filters must be used, or only one of the
    filters may be used, etc.

    This class book-keeps which filters were used as it parses the incoming
    data. Subclasses can use this to decide whether to add or remove errors.
    """

    tree_class = FilterTree

    FilterUse = namedtuple("FilterUse", "filter,valid,missing")

    def __init__(self, left, *rest):
        operator = and_  # OR does not make sense with group-require
        if not rest:
            # TODO if left is a tree, walk it instead of complaining
            raise ValueError("Optional has no effect on a single filter")
        right = reduce(and_, rest)
        super().__init__(False, operator, left, right)

    def parse(self, data):
        """
        Return Q-object for ``data``
        """
        filters = list(self)
        errors = defaultdict(list)
        query = Q()
        report = []

        # this is the same as the regular parse(), but with book-keeping to
        # populate `report`.
        for filter in filters:
            try:
                this_query = filter.parse(data)
                if this_query:
                    report.append(self.FilterUse(filter, valid=True, missing=False))
                else:
                    report.append(self.FilterUse(filter, valid=None, missing=True))
                query = self.operator(query, this_query)

            except InvalidData as ex:
                relevant_errors = ex.errors.get(filter.source, {})
                # TODO find a less terrible way of determining this
                is_missing = "This field is required" in relevant_errors
                report.append(self.FilterUse(filter, valid=False, missing=is_missing))
                errors.update(ex.errors)

        self.apply_constraint(report, errors)
        if errors:
            raise InvalidData(errors)

        return query

    def apply_constraint(self, report, errors):
        """
        Subclasses should examine how filters were used in ``report`` and
        mutate ``errors`` as necessary.
        """
        raise NotImplementedError()


class Optional(Constraint):
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
            Filter('last_name', required=True),
        )

    Generally, filters underneath Optional will have required=True, however it
    isn't necessary; consider adding 'middle name' to the above example.
    """

    def apply_constraint(self, report, errors):
        valid = [r.filter for r in report if r.valid]
        triggers = [r.filter for r in report if r.filter.required and r.missing]

        # some filters have values, but not all required filters have values.
        if any(valid) and any(triggers):
            sources = ", ".join(sorted(r.filter.source for r in report))
            errors["__all__"].append(
                f"If any of {sources} are provided, all must be provided"
            )

        else:
            for filter in triggers:
                del errors[filter.source]


class OneOf(Constraint):
    """
    Only one of the child filters can be used at a time.
    """

    def apply_constraint(self, report, errors):
        sources = ", ".join(sorted(r.filter.source for r in report))
        valid_count = sum(r.valid for r in report)
        extra_error = None

        if valid_count == 0:
            errors["__all__"].append(f"One of {sources} must be provided")
        elif valid_count > 1:
            errors["__all__"].append(f"Only one of {sources} can be provided")
        elif valid_count == 1:
            for r in report:
                if r.filter.required and r.missing:
                    del errors[r.filter.source]


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
        self.source = kwargs.get("source", dest)
        self.lookups = kwargs.get("lookups", ["exact"])
        self.multivalue_lookups = kwargs.get("multivalue_lookups", ["in"])
        self.required = kwargs.get("required", False)
        self.negate = kwargs.get("negate", False)
        self.none_to_isnull = kwargs.get("none_to_isnull", False)

        # None is a valid default -- consider exclude(groups=None) -- so use
        # the absence or presence of self.default to indicate whether a default
        # should be used.
        if "default" in kwargs:
            self.default = kwargs["default"]
            self.default_lookup = kwargs.get("default_lookup", "exact")

        # accept lookups as a comma-separated string.
        if isinstance(self.lookups, str):
            self.lookups = self.lookups.split(",")

    def __invert__(self):
        """
        Invert the sense of this filter.
        """
        inverted = self.copy()
        inverted.negate = not self.negate
        return inverted

    def __repr__(self):
        cls = type(self)
        desc = self.source
        if self.lookups != ["exact"]:
            desc = desc + "__" + "/".join(self.lookups)
        return f"<{cls.__name__} {desc}>"

    def parse_to_dict(self, data):
        """
        Look through the provided dict-like data for keys which match this
        Filter's source. This includes keys containing lookup affixes such as
        'contains' or 'lte'.

        A dictionary of values ready to be queried is returned. For example,

            {"created_date__gte": "2020-01-01..."}

        These can be used with Django's ORM by unpacking into filter(), or you
        can get a Q object representing the same query by calling parse(data)
        rather than parse_to_dict(data).
        """
        source_pairs = self.source_value_pairs(data)
        dest_pairs, errors = self.dest_value_pairs(source_pairs)

        # handle default value
        if not source_pairs and hasattr(self, "default"):
            dest_pairs = (self.default_dest_value_pair(),)

        # if required, check if satisfied
        if not source_pairs and self.required:
            if self.source not in errors:
                errors[self.source] = []
            errors[self.source].append("This field is required")

        if errors:
            raise InvalidData(errors=errors)

        return dict(dest_pairs)

    def parse(self, data):
        dicts = [self.parse_to_dict(data)]

        # Django, via SQL, does not do what you might expect with
        # .filter(rank__in=[1, 2, None]). This doesn't give you things with
        # rank 1, 2 or null -- you just get things with rank 1 and 2. Instead
        # SQL wants you to make an explicit "in or is null" check. For
        # consistency with Django and SQL, filternaut also behaves this way by
        # default. If you don't want this behaviour, argue none_to_isnull=True
        # when making a filter.
        if self.none_to_isnull:
            for key, val in list(dicts[0].items()):
                is_many = key.endswith("__in")
                has_null = is_many and None in val
                if is_many and has_null:
                    lookup = f"{key[:-4]}__isnull"
                    dicts.append({lookup: True})
                    val.remove(None)
                    # if the only value was None, we don't need the "__in" any
                    # more.
                    if not val:
                        dicts[0].pop(key)

        q = reduce(or_, (Q(**d) for d in dicts))
        return ~q if self.negate else q

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
            if lookup in (None, "exact"):
                source = self.source
                dest = self.dest
            else:
                source = f"{self.source}__{lookup}"
                dest = f"{self.dest}__{lookup}"
            pairs.append((source, dest))

        # allow source data to omit the lookup if only one lookup listed.
        if len(pairs) == 1:
            lookup = self.lookups[0]
            if lookup not in (None, "exact"):
                dest = f"{self.dest}__{self.lookups[0]}"
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
                many = any(dest.endswith(f"__{x}") for x in self.multivalue_lookups)
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
        dest = f"{self.dest}__{self.default_lookup}"
        default = self.default() if callable(self.default) else self.default
        return (dest, default)

    def get_source_value(self, key, data, many=False):
        """
        Pull ``key`` from ``data``.

        When ``many`` is True, a list of values is returned. Otherwise, a
        single value is returned.
        """
        if many is False:
            return data[key]
        elif hasattr(data, "getlist"):  # Django querydict, multivaluedict
            if key not in data:
                raise KeyError(repr(key))
            return data.getlist(key)
        else:
            # only a single value, but many=True, so return as list.
            return [data[key]]
