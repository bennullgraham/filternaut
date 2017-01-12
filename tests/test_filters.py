# -*- coding: utf8 -*-

from __future__ import absolute_import, print_function, unicode_literals

import tempfile
from unittest import TestCase

import filternaut
from django import VERSION as DJANGO_VERSION
from django.utils.datastructures import MultiValueDict
from filternaut import Filter, Optional
from filternaut.filters import (CharFilter, ChoiceFilter, FilePathFilter,
                                RegexFilter)
from tests.util import NopeFilter, flatten_qobj


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
        assert not f.errors

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
        assert f.errors
        assert 'fieldname' in f.errors

    def test_lookups_can_be_provided_as_a_string(self):
        f = Filter('fieldname', lookups='contains')
        assert f.lookups == ['contains']

    def test_lookups_can_be_provided_as_a_comma_separated_string(self):
        f = Filter('fieldname', lookups='lt,lte,gt,gte')
        assert f.lookups == ['lt', 'lte', 'gt', 'gte']

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

    def test_multivaluedict_as_source(self):
        """
        We don't expect multiple values to be pulled from a multi-value source
        without explicit instruction
        """
        filters = Filter('name')
        data = MultiValueDict(dict(name=['foo', 'bar']))
        filters.parse(data)
        expected = dict(name='bar')  # last one wins
        actual = dict(flatten_qobj(filters.Q))
        assert expected == actual

    def test_multivaluedict_as_source_when_many_values_required(self):
        """
        Having a dest ending in '__in' /does/ constitute explicit instruction
        to pull multiple values from a source.
        """
        filters = Filter('field', lookups=['in'])
        data = MultiValueDict(dict(field=['foo', 'bar']))
        filters.parse(data)
        expected = dict(field__in=['foo', 'bar'])
        actual = dict(flatten_qobj(filters.Q))
        assert expected == actual

    def test_multivaluedict_not_used_for_nonlisty_filtering(self):
        filters = Filter('field', lookups=['exact', 'in'])

        data = MultiValueDict(dict(field=['foo', 'bar']))
        filters.parse(data)
        expected = dict(field='bar')  # last one wins
        actual = dict(flatten_qobj(filters.Q))
        assert expected == actual

        data = MultiValueDict(dict(field__in=['foo', 'bar']))
        filters.parse(data)
        expected = dict(field__in=['foo', 'bar'])
        actual = dict(flatten_qobj(filters.Q))
        assert expected == actual


class TestSourceDestPairCreation(TestCase):

    def test_no_lookup_same_source_and_dest(self):
        filter = Filter('field', lookups=[None])
        expected = [('field', 'field'), ]
        actual = list(filter.source_dest_pairs())
        assert expected == actual

    def test_gte_lookup_same_source_and_dest(self):
        filter = Filter('field', lookups=['gte'])
        expected = [
            ('field__gte', 'field__gte'),
            ('field', 'field__gte')]
        actual = list(filter.source_dest_pairs())
        assert sorted(expected) == sorted(actual)

    def test_no_lookup_differing_source_and_dest(self):
        filter = Filter(source='something', dest='field', lookups=[None])
        expected = [('something', 'field'), ]
        actual = list(filter.source_dest_pairs())
        assert expected == actual

    def test_lte_lookup_differing_source_and_dest(self):
        filter = Filter(source='something', dest='field', lookups=['lte'])
        expected = [
            ('something__lte', 'field__lte'),
            ('something', 'field__lte')]
        actual = list(filter.source_dest_pairs())
        assert sorted(expected) == sorted(actual)


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
        assert filter.errors

        filter = ChoiceFilter(choices=choices, dest='name')
        filter.parse({'name': 'alai'})
        assert not filter.errors

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
        assert filter.errors
        assert 'fieldname' in filter.errors

        filter = RegexFilter('fieldname', r'\d+')
        filter.parse({'fieldname': '1008346'})
        assert not filter.errors
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
            'ImageFilter', 'IntegerFilter', 'MultiValueFilter',
            'MultipleChoiceFilter', 'NullBooleanFilter', 'SlugFilter',
            'SplitDateTimeFilter', 'TimeFilter', 'TypedChoiceFilter',
            'URLFilter')
        filterfields_dj14_plus = (
            'GenericIPAddressFilter', 'TypedMultipleChoiceFilter')
        filterfields_dj19_less = ('IPAddressFilter', )

        for f in filterfields:
            klass = getattr(filternaut.filters, f)
            klass('fieldname')

        for f in filterfields_dj14_plus:
            if DJANGO_VERSION >= (1, 4):
                klass = getattr(filternaut.filters, f)
                klass('fieldname')
            else:
                assert not hasattr(filternaut.filters, f)

        for f in filterfields_dj19_less:
            if DJANGO_VERSION < (1, 9):
                klass = getattr(filternaut.filters, f)
                klass('fieldname')
            else:
                assert not hasattr(filternaut.filters, f)

    def test_listlike_values_cleaned_individually(self):
        f = CharFilter('fieldname', lookups='exact,in')
        data = MultiValueDict({
            'fieldname': ['single value'],  # MVDict treats 1-list as single
            'fieldname__in': ['multiple', 'values'],
        })
        expected = {
            'fieldname': 'single value',
            'fieldname__in': ['multiple', 'values']
        }
        f.parse(data)
        actual = dict(flatten_qobj(f.Q))
        assert expected == actual


class DefaultValueTests(TestCase):

    def test_default_value_used_if_no_sourcedata_found(self):
        filters = Filter('count', lookups=['lte', 'gte'], default=3)
        filters.parse({})  # no value for 'count'

        expected = {'count__exact': 3}
        actual = dict(flatten_qobj(filters.Q))

        assert expected == actual

    def test_default_lookup_is_exact(self):
        f = Filter('count', default=3)
        assert f.default_lookup == 'exact'

    def test_other_lookups_ignored_when_default_used(self):
        filters = Filter('count', lookups=['lte', 'gte'], default=3)
        filters.parse({})  # no value for 'count'

        keys = dict(flatten_qobj(filters.Q)).keys()

        assert 'lte' not in keys
        assert 'gte' not in keys

    def test_default_lookup_type_can_be_changed(self):
        filters = Filter('count', lookups=['lte', 'gte'], default=3,
                         default_lookup='gt')
        filters.parse({})  # no value for 'count'

        expected = {'count__gt': 3}
        actual = dict(flatten_qobj(filters.Q))

        assert expected == actual

    def test_default_ignored_if_sourcedata_found(self):
        filters = Filter('count', lookups=['lte', 'gte'], default=3,
                         default_lookup='foobarbaz')
        filters.parse({'count__gte': 4})

        expected = {'count__gte': 4}
        actual = dict(flatten_qobj(filters.Q))

        assert expected == actual


class OptionalTests(TestCase):

    def setUp(self):
        self.filters = Optional(
            Filter('one', required=True),
            Filter('two'),
            Filter('three', required=True))
        self.unrelated = Filter('ten') & (Filter('eleven') | Filter('twelve'))

    def test_no_values_present(self):
        data = dict()  # no data
        self.filters.parse(data)
        assert self.filters.valid

    def test_all_values_present(self):
        data = dict(one=1, two=2, three=3)
        self.filters.parse(data)
        assert self.filters.valid

    def test_only_required_values_present(self):
        data = dict(one=1, three=3)
        self.filters.parse(data)
        assert self.filters.valid

    def test_only_nonrequired_values_present(self):
        data = dict(two=2)
        self.filters.parse(data)
        assert not self.filters.valid
        assert 'one' in self.filters.errors
        assert 'three' in self.filters.errors
        assert '__all__' in self.filters.errors

    def test_one_required_filter_missing(self):
        data = dict(two=2, three=3)
        self.filters.parse(data)
        assert not self.filters.valid
        assert 'one' in self.filters.errors
        assert 'three' not in self.filters.errors
        assert '__all__' in self.filters.errors

    def test_ANDed_with_unrelated(self):
        filters = self.filters & self.unrelated

        data = dict()  # no data
        filters.parse(data)
        assert filters.valid

        data = dict(one=1, three=3)  # all required data
        filters.parse(data)
        assert filters.valid

        data = dict(ten=10)  # only some unrelated
        filters.parse(data)
        assert filters.valid

        data = dict(ten=10, eleven=11, twelve=12)  # only all unrelated
        filters.parse(data)
        assert filters.valid

    def test_validation_errors_are_not_silenced(self):
        filters = Optional(
            NopeFilter('a', required=True),
            NopeFilter('b', required=True),
            NopeFilter('c'))
        data = dict(a=1, b=2, c=3)
        filters.parse(data)
        assert 'a' in filters.errors
        assert 'b' in filters.errors
        assert 'c' in filters.errors

        data = dict()
        filters.parse(data)
        assert not filters.errors


class BooleanTests(TestCase):
    filter = filternaut.filters.BooleanFilter('approved')

    valid_values = '1', '0', 'true', 'false', 'True', 'False', True, False
    for value in valid_values:
        filter.parse(dict(approved=value))
        assert filter.valid
