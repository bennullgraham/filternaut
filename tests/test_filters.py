# -*- coding: utf8 -*-

from __future__ import unicode_literals, print_function, absolute_import
from unittest import TestCase
import tempfile

from django import VERSION as DJANGO_VERSION

from filternaut import Filter
from filternaut.filters import ChoiceFilter, RegexFilter, FilePathFilter
from tests import flatten_qobj
import filternaut


class FilterTests(TestCase):

    def test_kwargless_simple_instantiation(self):
        f = Filter('fieldname')
        assert f.source == 'fieldname'
        assert f.dest == 'fieldname'

    def test_kwarg_instantiation(self):
        f = Filter(dest='fieldname')
        assert f.source == 'fieldname'
        assert f.dest == 'fieldname'

        f = Filter(source='sourcename', dest='fieldname')
        assert f.source == 'sourcename'
        assert f.dest == 'fieldname'

    def test_getsourcevalue_does_what_it_says_on_the_tin(self):
        f = Filter('fieldname')
        bar = f.get_source_value('foo', {'foo': 'bar'})
        assert bar == 'bar'

    def test_getsourcevalue_raises_keyerrors(self):
        f = Filter('fieldname')
        with self.assertRaises(KeyError):
            f.get_source_value('legume', {'foo': 'bar'})

    def test_required_filter_is_satisfied_by_one_key_being_present(self):
        f = Filter('fieldname', required=True, lookups=['gte'])
        data = {
            'fieldname__gte': 'foo',
            'fieldname__lte': 'bar'}
        f.parse(data)
        assert f.errors is None

    def test_required_filter_requires_at_least_one_key(self):
        """
        One filter can have many possible sources due to the different lookup
        affixes. One of them being present should be enough to satisfy a
        'required' field.
        """
        f = Filter('fieldname', required=True, lookups=['contains'])
        data = {
            'fieldname__gte': 'foo',
            'fieldname__lte': 'bar'}
        f.parse(data)
        assert f.errors is not None
        assert 'fieldname' in f.errors

    def test_lookups_can_be_provided_as_a_string(self):
        f = Filter('fieldname', lookups='contains')
        assert f.lookups == ['contains']

    def test_negating_filters(self):
        f = Filter('fieldname')
        assert f.negate is False
        f = ~f
        assert f.negate is True
        f = ~f
        assert f.negate is False

    def test_one_source_to_many_dests(self):
        filters = (
            Filter(source='search', dest='username') |
            Filter(source='search', dest='email') |
            Filter(source='search', dest='name'))
        filters.parse(dict(search='mynbaev-scheiner'))
        expected = dict(
            username='mynbaev-scheiner',
            email='mynbaev-scheiner',
            name='mynbaev-scheiner')
        actual = dict(flatten_qobj(filters.Q))
        assert expected == actual

    def test_many_sources_one_dest(self):
        filters = (
            Filter(source='nominee_1', dest='field') |
            Filter(source='nominee_2', dest='field') |
            Filter(source='nominee_3', dest='field'))
        filters.parse(dict(
            nominee_1='one',
            nominee_2='two',
            nominee_3='three'))
        expected = dict(field='three')  # last one wins
        actual = dict(flatten_qobj(filters.Q))
        assert expected == actual


class TestSourceDestPairCreation(TestCase):

    def test_no_lookup_same_source_and_dest(self):
        filter = Filter('field')
        expected = ('field', 'field')
        actual = filter.make_source_dest_pair(None)
        assert expected == actual

    def test_gte_lookup_same_source_and_dest(self):
        filter = Filter('field')
        expected = ('field__gte', 'field__gte')
        actual = filter.make_source_dest_pair('gte')
        assert expected == actual

    def test_no_lookup_differing_source_and_dest(self):
        filter = Filter(source='something', dest='field')
        expected = ('something', 'field')
        actual = filter.make_source_dest_pair(None)
        assert expected == actual

    def test_lte_lookup_differing_source_and_dest(self):
        filter = Filter(source='something', dest='field')
        expected = ('something__lte', 'field__lte')
        actual = filter.make_source_dest_pair('lte')
        assert expected == actual


class ParsingTests(TestCase):

    def test_parse_simple_source(self):
        filter = Filter('word')
        data = {
            'word': 'a_value',
            'unrelated_key': ''}
        filter.parse(data)

        assert not filter.errors
        assert 'word' in filter._filters
        assert filter._filters['word'] == 'a_value'

    def test_parse_source_with_lookups(self):
        filter = Filter('word', lookups=['gte', 'gt', 'lte', 'lt'])
        data = {
            'word__gte': 1,
            'word__gt': 2,
            'word__lte': 3,
            'word__lt': 4}

        filter.parse(data)

        assert not filter.errors
        for key in data:
            assert key in filter._filters
        for key, value in data.items():
            assert filter._filters[key] == value
        assert filter.valid

    def test_more_extensive_parsing(self):
        filters = (
            Filter('field_1', lookups=['contains', 'icontains']) |
            Filter(source='field_2', dest='field_2a') |
            Filter(source='field_3', dest='f3', lookups=['lt', 'gt']) |
            Filter(source='id', dest='relationship__spanning__id'))
        data = {
            'field_1__contains': 'first',
            'field_2': 'second',
            'field_3__lt': 'third',
            'field_3__gt': 'fourth',
            'id': 'fifth'}
        expected = {
            'field_1__contains': 'first',
            'field_2a': 'second',
            'f3__lt': 'third',
            'f3__gt': 'fourth',
            'relationship__spanning__id': 'fifth'}
        filters.parse(data)
        actual = dict(flatten_qobj(filters.Q))
        assert expected == actual
        assert filters.valid


class FieldFilterTests(TestCase):

    def test_choicefilter_choices(self):
        choices = (
            ('alai', 'Alai'),
            ('petra', 'Petra'))

        filter = ChoiceFilter(choices=choices, dest='name')
        filter.parse({'name': 'bean'})
        assert filter.errors is not None

        filter = ChoiceFilter(choices=choices, dest='name')
        filter.parse({'name': 'alai'})
        assert filter.errors is None

    def test_choicefilter_instantiation_styles(self):
        fieldname = 'fieldname'
        choices = ['choice1', 'choice2']

        filters = [
            # no kwargs
            ChoiceFilter(fieldname, choices),
            # arg fieldname, kwarg choices
            ChoiceFilter(fieldname, choices=choices),
            # all kwargs
            ChoiceFilter(source=fieldname, dest=fieldname, choices=choices)]

        for filter in filters:
            assert filter.source == fieldname
            assert filter.field.choices == choices

    def test_regexfilter(self):
        filter = RegexFilter('fieldname', r'\d+')
        filter.parse({'fieldname': 'alpha'})
        assert filter.errors is not None
        assert 'fieldname' in filter.errors

        filter = RegexFilter('fieldname', r'\d+')
        filter.parse({'fieldname': '1008346'})
        assert filter.errors is None
        assert filter.valid

    def test_filepathfilter(self):
        # this isn't a great test, since we just instantiate the filter.
        # however, proper testing requires monkeying about changing the test
        # system's filesystem; and, being a subclass of choicefilter, that
        # class' tests should cover us.
        path = tempfile.gettempdir()
        FilePathFilter('fieldname', path)

    def test_instantiate_all_filterfields_without_special_args(self):
        # ChoiceFilter, FilePathFilter, and RegexFilter have their own specific
        # tests, because their fields' constructors, and therefore their own
        # constructors, require additional arguments
        filterfields = (
            'BooleanFilter', 'CharFilter', 'ComboFilter', 'DateFilter',
            'DateTimeFilter', 'DecimalFilter', 'EmailFilter', 'FloatFilter',
            'IPAddressFilter', 'ImageFilter', 'IntegerFilter',
            'MultiValueFilter', 'MultipleChoiceFilter', 'NullBooleanFilter',
            'SlugFilter', 'SplitDateTimeFilter', 'TimeFilter',
            'TypedChoiceFilter', 'URLFilter')
        filterfields_dj14_plus = (
            'GenericIPAddressFilter', 'TypedMultipleChoiceFilter')

        for f in filterfields:
            klass = getattr(filternaut.filters, f)
            klass('fieldname')

        for f in filterfields_dj14_plus:
            if DJANGO_VERSION >= (1, 4):
                klass = getattr(filternaut.filters, f)
                klass('fieldname')
            else:
                assert not hasattr(filternaut.filters, f)
