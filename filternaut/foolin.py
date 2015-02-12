from django.core.exceptions import ValidationError
from django.db.models import Q
from django.forms import DateTimeField
from operator import or_, and_, invert


# -----------
import django
from django.conf import settings
settings.configure()
django.setup
# -----------

def indent(o):
    indented_lines = ['  {}'.format(l) for l in str(o).split('\n')]
    return '\n'.join(indented_lines)


class Filter(object):
    def __and__(self, other):
        return FilterNode(left=self, right=other, operator=and_)

    def __or__(self, other):
        return FilterNode(left=self, right=other, operator=or_)

    def __invert__(self):
        raise NotImplementedError()

    def parse(self, data):
        raise NotImplementedError()

    @property
    def Q(self):
        raise NotImplementedError()


class FilterNode(Filter):
    def __init__(self, operator, left, right, negate=False):
        assert operator in (or_, and_)
        self.operator = operator
        self.left = left
        self.right = right
        self.negate = negate

    def __str__(self):
        friendly = 'or' if self.operator == or_ else 'and'
        left = indent(self.left)
        right = indent(self.right)
        return '{op}:\n{left}\n{right}'.format(
            op=friendly, left=left, right=right)

    def __invert__(self):
        return FilterNegate(child=self)

    def parse(self, data):
        self.left.parse(data)
        self.right.parse(data)

    def errors(self, data):
        return self.left + self.right

    @property
    def Q(self):
        Q = self.operator(self.left.Q, self.right.Q)
        if self.negate:
            return invert(Q)
        else:
            return Q


class FilterLeaf(Filter):
    def __init__(self, field, dest, source=None, lookups=None, negate=False):
        self.field = field
        self.dest = dest
        self.source = source or dest
        self.lookups = lookups or []
        self.negate = negate

        self._filters = {}
        self._errors = {}
        self.parsed = False

    def __str__(self):
        source = self.source
        if self.lookups:
            source += '__%s' % ','.join(self.lookups)
        return '[' + source + ']'

    def __invert__(self):
        new_negate = not self.negate
        return FilterLeaf(
            field=self.field,
            dest=self.dest,
            source=self.source,
            lookups=self.lookups,
            negate=new_negate)

    def source_keys(self):
        keys = [self.source]
        for lookup in self.lookups:
            keys.append('{}__{}'.format(self.source, lookup))
        return keys

    def parse(self, data):
        self._filters, self._errors = self.get_q_kwargs(data)
        self.parsed = True

    def get_q_kwargs(self, data):
        filters, errors = {}, {}
        for k in self.source_keys():
            if k in data:
                try:
                    value = self.field.clean(data[k])
                    filters[k] = value
                except ValidationError as ex:
                    errors[k] = ex.message
        return filters, errors

    @property
    def errors(self):
        return self._errors

    @property
    def Q(self):
        if not self.parsed:
            raise ValueError(
                "Must call parse() on filternaut chain before using Q")
        return Q(**self._filters)


N = FilterLeaf

f = N(DateTimeField(), source='begin', dest='appt__begin', lookups=['gte', 'lte']) | \
    N(DateTimeField(), source='end', dest='appt__end', lookups=['gte']) & \
    N(DateTimeField(), dest='pk')


request_DATA = {'begin__gte': '2015-01-01', 'end__gte': '2016-01-01', 'pk': 3}
f.parse(request_DATA)
print f.Q
# Model.objects.filter(**f.as_Q()())
