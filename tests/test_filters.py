import tempfile
from unittest import TestCase

import pytest
from django.forms import CharField, IntegerField
from django.utils.datastructures import MultiValueDict

import filternaut
from filternaut import Filter, Optional
from filternaut.exceptions import InvalidData
from filternaut.filters import (
    CharFilter,
    ChoiceFilter,
    ComboFilter,
    FieldFilter,
    FilePathFilter,
    IntegerFilter,
    RegexFilter,
)
from tests.util import NopeFilter, assert_parsed_ok, flatten_qobj


class FilterTests(TestCase):
    def test_kwargless_simple_instantiation(self):
        f = Filter("fieldname")
        assert f.source == "fieldname"
        assert f.dest == "fieldname"

    def test_kwarg_instantiation(self):
        f = Filter(dest="fieldname")
        assert f.source == "fieldname"
        assert f.dest == "fieldname"

        f = Filter(source="sourcename", dest="fieldname")
        assert f.source == "sourcename"
        assert f.dest == "fieldname"

    def test_getsourcevalue_does_what_it_says_on_the_tin(self):
        f = Filter("fieldname")
        bar = f.get_source_value("foo", {"foo": "bar"})
        assert bar == "bar"

    def test_getsourcevalue_raises_keyerrors(self):
        f = Filter("fieldname")
        with self.assertRaises(KeyError):
            f.get_source_value("legume", {"foo": "bar"})

    def test_required_filter_is_satisfied_by_one_key_being_present(self):
        f = Filter("fieldname", required=True, lookups=["gte"])
        data = {"fieldname__gte": "foo", "fieldname__lte": "bar"}
        assert_parsed_ok(f.parse(data))

    def test_required_filter_requires_at_least_one_key(self):
        """
        One filter can have many possible sources due to the different lookup
        affixes. One of them being present should be enough to satisfy a
        'required' field.
        """
        f = Filter("fieldname", required=True, lookups=["contains"])
        data = {"fieldname__gte": "foo", "fieldname__lte": "bar"}
        with pytest.raises(InvalidData) as exc_info:
            f.parse(data)
        assert "fieldname" in exc_info.value.errors

    def test_lookups_can_be_provided_as_a_string(self):
        f = Filter("fieldname", lookups="contains")
        assert f.lookups == ["contains"]

    def test_lookups_can_be_provided_as_a_comma_separated_string(self):
        f = Filter("fieldname", lookups="lt,lte,gt,gte")
        assert f.lookups == ["lt", "lte", "gt", "gte"]

    def test_negating_filters(self):
        f = Filter("fieldname")
        assert f.negate is False
        f = ~f
        assert f.negate is True
        f = ~f
        assert f.negate is False

    def test_one_source_to_many_dests(self):
        filters = (
            Filter(source="search", dest="username")
            | Filter(source="search", dest="email")
            | Filter(source="search", dest="name")
        )
        query = filters.parse(dict(search="mynbaev-scheiner"))
        expected = dict(
            username="mynbaev-scheiner",
            email="mynbaev-scheiner",
            name="mynbaev-scheiner",
        )
        actual = dict(flatten_qobj(query))
        assert expected == actual

    def test_many_sources_one_dest(self):
        filters = (
            Filter(source="nominee_1", dest="field")
            | Filter(source="nominee_2", dest="field")
            | Filter(source="nominee_3", dest="field")
        )
        query = filters.parse(dict(nominee_1="one", nominee_2="two", nominee_3="three"))
        expected = dict(field="three")  # last one wins
        actual = dict(flatten_qobj(query))
        assert expected == actual

    def test_multivaluedict_as_source(self):
        """
        We don't expect multiple values to be pulled from a multi-value source
        without explicit instruction
        """
        filters = Filter("name")
        data = MultiValueDict(dict(name=["foo", "bar"]))
        query = filters.parse(data)
        expected = dict(name="bar")  # last one wins
        actual = dict(flatten_qobj(query))
        assert expected == actual

    def test_multivaluedict_as_source_when_many_values_required(self):
        """
        Having a dest ending in '__in' /does/ constitute explicit instruction
        to pull multiple values from a source.
        """
        filters = Filter("field", lookups=["in"])
        data = MultiValueDict(dict(field=["foo", "bar"]))
        query = filters.parse(data)
        expected = dict(field__in=["foo", "bar"])
        actual = dict(flatten_qobj(query))
        assert expected == actual

    def test_multivaluedict_not_used_for_nonlisty_filtering(self):
        filters = Filter("field", lookups=["exact", "in"])

        data = MultiValueDict(dict(field=["foo", "bar"]))
        query = filters.parse(data)
        expected = dict(field="bar")  # last one wins
        actual = dict(flatten_qobj(query))
        assert expected == actual

        data = MultiValueDict(dict(field__in=["foo", "bar"]))
        query = filters.parse(data)
        expected = dict(field__in=["foo", "bar"])
        actual = dict(flatten_qobj(query))
        assert expected == actual


class TestSourceDestPairCreation(TestCase):
    def test_no_lookup_same_source_and_dest(self):
        filter = Filter("field", lookups=[None])
        expected = [
            ("field", "field"),
        ]
        actual = list(filter.source_dest_pairs())
        assert expected == actual

    def test_gte_lookup_same_source_and_dest(self):
        filter = Filter("field", lookups=["gte"])
        expected = [("field__gte", "field__gte"), ("field", "field__gte")]
        actual = list(filter.source_dest_pairs())
        assert sorted(expected) == sorted(actual)

    def test_no_lookup_differing_source_and_dest(self):
        filter = Filter(source="something", dest="field", lookups=[None])
        expected = [
            ("something", "field"),
        ]
        actual = list(filter.source_dest_pairs())
        assert expected == actual

    def test_lte_lookup_differing_source_and_dest(self):
        filter = Filter(source="something", dest="field", lookups=["lte"])
        expected = [("something__lte", "field__lte"), ("something", "field__lte")]
        actual = list(filter.source_dest_pairs())
        assert sorted(expected) == sorted(actual)


class ParsingTests(TestCase):
    def test_parse_simple_source(self):
        filter = Filter("word")
        data = {"word": "a_value", "unrelated_key": ""}
        query = filter.parse(data)
        flat = dict(flatten_qobj(query))

        assert "word" in flat
        assert flat["word"] == "a_value"

    def test_parse_source_with_lookups(self):
        filter = Filter("word", lookups=["gte", "gt", "lte", "lt"])
        data = {"word__gte": 1, "word__gt": 2, "word__lte": 3, "word__lt": 4}

        query = filter.parse(data)
        flat = dict(flatten_qobj(query))

        for key in data:
            assert key in flat
        for key, value in data.items():
            assert flat[key] == value

    def test_more_extensive_parsing(self):
        filters = (
            Filter("field_1", lookups=["contains", "icontains"])
            | Filter(source="field_2", dest="field_2a")
            | Filter(source="field_3", dest="f3", lookups=["lt", "gt"])
            | Filter(source="id", dest="relationship__spanning__id")
        )
        data = {
            "field_1__contains": "first",
            "field_2": "second",
            "field_3__lt": "third",
            "field_3__gt": "fourth",
            "id": "fifth",
        }
        expected = {
            "field_1__contains": "first",
            "field_2a": "second",
            "f3__lt": "third",
            "f3__gt": "fourth",
            "relationship__spanning__id": "fifth",
        }
        query = filters.parse(data)
        actual = dict(flatten_qobj(query))
        assert expected == actual


class FieldFilterTests(TestCase):
    def test_choicefilter_choices(self):
        choices = (("alai", "Alai"), ("petra", "Petra"))
        filter = ChoiceFilter(choices=choices, dest="name")

        with pytest.raises(InvalidData):
            filter.parse({"name": "bean"})

        # no exception
        filter.parse({"name": "alai"})

    def test_choicefilter_instantiation_styles(self):
        fieldname = "fieldname"
        choices = ["choice1", "choice2"]

        filters = [
            # no kwargs
            ChoiceFilter(fieldname, choices),
            # arg fieldname, kwarg choices
            ChoiceFilter(fieldname, choices=choices),
            # all kwargs
            ChoiceFilter(source=fieldname, dest=fieldname, choices=choices),
        ]

        for filter in filters:
            assert filter.source == fieldname
            assert filter.field.choices == choices

    def test_regexfilter(self):
        filter = RegexFilter("fieldname", r"\d+")
        with pytest.raises(InvalidData) as exc_info:
            filter.parse({"fieldname": "alpha"})
        assert "fieldname" in exc_info.value.errors

        filter = RegexFilter("fieldname", r"\d+")
        query = filter.parse({"fieldname": "1008346"})
        assert_parsed_ok(query)

    def test_filepathfilter(self):
        # this isn't a great test, since we just instantiate the filter.
        # however, proper testing requires monkeying about changing the test
        # system's filesystem; and, being a subclass of choicefilter, that
        # class' tests should cover us.
        path = tempfile.gettempdir()
        FilePathFilter("fieldname", path)

    def test_combofilter(self):
        filter = ComboFilter(
            "fieldname",
            fields=[
                CharField(min_length=2, max_length=4),
                CharField(min_length=3, max_length=6),
            ],
        )
        invalids = "", "a", "aa", "aaaaa", "aaaaaa", "aaaaaaa"
        valids = "aaa", "aaaa"

        for invalid in invalids:
            with pytest.raises(InvalidData) as exc_info:
                filter.parse({"fieldname": invalid})
            assert "fieldname" in exc_info.value.errors

        for valid in valids:
            query = filter.parse({"fieldname": valid})
            assert_parsed_ok(query)

    def test_multivaluefilter(self):
        # TODO this field is relatively complex. have not written a test for it
        # yet.
        pass

    def test_instantiate_all_filterfields_without_special_args(self):
        # ChoiceFilter, FilePathFilter, and some others have their own specific
        # tests, because their fields' constructors, and therefore their own
        # constructors, require additional arguments
        filterfields = (
            "BooleanFilter",
            "CharFilter",
            "DateFilter",
            "DateTimeFilter",
            "DecimalFilter",
            "EmailFilter",
            "FloatFilter",
            "ImageFilter",
            "IntegerFilter",
            "MultipleChoiceFilter",
            "NullBooleanFilter",
            "SlugFilter",
            "SplitDateTimeFilter",
            "TimeFilter",
            "TypedChoiceFilter",
            "URLFilter",
            "GenericIPAddressFilter",
            "TypedMultipleChoiceFilter",
        )

        for f in filterfields:
            klass = getattr(filternaut.filters, f)
            klass("fieldname")

    def test_listlike_values_cleaned_individually(self):
        f = CharFilter("fieldname", lookups="exact,in")
        data = MultiValueDict(
            {
                "fieldname": ["single value"],  # MVDict treats 1-list as single
                "fieldname__in": ["multiple", "values"],
            }
        )
        expected = {
            "fieldname": "single value",
            "fieldname__in": ["multiple", "values"],
        }
        query = f.parse(data)
        actual = dict(flatten_qobj(query))
        assert expected == actual


class DefaultValueTests(TestCase):
    def test_default_value_used_if_no_sourcedata_found(self):
        filters = Filter("count", lookups=["lte", "gte"], default=3)
        query = filters.parse({})  # no value for 'count'

        expected = {"count__exact": 3}
        actual = dict(flatten_qobj(query))

        assert expected == actual

    def test_default_lookup_is_exact(self):
        f = Filter("count", default=3)
        assert f.default_lookup == "exact"

    def test_other_lookups_ignored_when_default_used(self):
        filters = Filter("count", lookups=["lte", "gte"], default=3)
        query = filters.parse({})  # no value for 'count'

        keys = dict(flatten_qobj(query)).keys()

        assert "lte" not in keys
        assert "gte" not in keys

    def test_default_lookup_type_can_be_changed(self):
        filters = Filter(
            "count", lookups=["lte", "gte"], default=3, default_lookup="gt"
        )
        query = filters.parse({})  # no value for 'count'

        expected = {"count__gt": 3}
        actual = dict(flatten_qobj(query))

        assert expected == actual

    def test_default_ignored_if_sourcedata_found(self):
        filters = Filter(
            "count", lookups=["lte", "gte"], default=3, default_lookup="foobarbaz"
        )
        query = filters.parse({"count__gte": 4})

        expected = {"count__gte": 4}
        actual = dict(flatten_qobj(query))

        assert expected == actual

    def test_default_can_be_callable(self):
        filters = Filter("count", lookups=["lte", "gte"], default=lambda: 3)
        query = filters.parse({})  # no value for 'count'

        expected = {"count__exact": 3}
        actual = dict(flatten_qobj(query))

        assert expected == actual


class OptionalTests(TestCase):
    def setUp(self):
        self.filters = Optional(
            Filter("one", required=True), Filter("two"), Filter("three", required=True)
        )
        self.unrelated = Filter("ten") & (Filter("eleven") | Filter("twelve"))

    def test_no_values_present(self):
        data = dict()  # no data
        query = self.filters.parse(data)
        assert_parsed_ok(query)

    def test_all_values_present(self):
        data = dict(one=1, two=2, three=3)
        query = self.filters.parse(data)
        assert_parsed_ok(query)

    def test_only_required_values_present(self):
        data = dict(one=1, three=3)
        query = self.filters.parse(data)
        assert_parsed_ok(query)

    def test_only_nonrequired_values_present(self):
        data = dict(two=2)
        with pytest.raises(InvalidData) as exc_info:
            self.filters.parse(data)
        assert "one" in exc_info.value.errors
        assert "three" in exc_info.value.errors
        assert "__all__" in exc_info.value.errors

    def test_one_required_filter_missing(self):
        data = dict(two=2, three=3)
        with pytest.raises(InvalidData) as exc_info:
            self.filters.parse(data)
        assert "one" in exc_info.value.errors
        assert "three" not in exc_info.value.errors
        assert "__all__" in exc_info.value.errors

    def test_ANDed_with_unrelated(self):
        filters = self.filters & self.unrelated

        data = dict()  # no data
        query = filters.parse(data)
        assert_parsed_ok(query)

        data = dict(one=1, three=3)  # all required data
        query = filters.parse(data)
        assert_parsed_ok(query)

        data = dict(ten=10)  # only some unrelated
        query = filters.parse(data)
        assert_parsed_ok(query)

        data = dict(ten=10, eleven=11, twelve=12)  # only all unrelated
        query = filters.parse(data)
        assert_parsed_ok(query)

    def test_validation_errors_are_not_silenced(self):
        filters = Optional(
            NopeFilter("a", required=True),
            NopeFilter("b", required=True),
            NopeFilter("c"),
        )
        data = dict(a=1, b=2, c=3)
        with pytest.raises(InvalidData) as exc_info:
            filters.parse(data)
        assert "a" in exc_info.value.errors
        assert "b" in exc_info.value.errors
        assert "c" in exc_info.value.errors

        data = dict()
        assert_parsed_ok(filters.parse(data))


def boolean_tests():
    filter = filternaut.filters.BooleanFilter("approved")

    valid_values = "1", "0", "true", "false", "True", "False", True, False
    for value in valid_values:
        query = filter.parse({"approved": value})
        assert_parsed_ok(query)


class MultiValueWithNoneTests(TestCase):
    def get_output_of_field(self, isnull=False, **data):
        # previously you had to pass a required=False field instance into FieldFilter.
        old_style = FieldFilter(
            "rank",
            lookups="in",
            none_to_isnull=isnull,
            field=IntegerField(required=False),
        )
        # now you can work with the field variants directly.
        new_style = IntegerFilter("rank", lookups="in", none_to_isnull=isnull)

        data = MultiValueDict(data)
        old_query = old_style.parse(data)
        new_query = new_style.parse(data)

        # check both styles produce the same results
        assert old_query == new_query

        # specific tests make their own assertions with this return value too.
        return dict(new_query.children)

    def test_enabled_with_regular_value(self):
        actual = self.get_output_of_field(rank=["1", "2", "3"], isnull=True)
        expected = {"rank__in": [1, 2, 3]}
        assert actual == expected

    def test_enabled_with_none_value_and_regulars(self):
        actual = self.get_output_of_field(rank=["1", "2", "3", ""], isnull=True)
        expected = {"rank__in": [1, 2, 3], "rank__isnull": True}
        assert actual == expected

    def test_enabled_with_only_none_value(self):
        actual = self.get_output_of_field(rank=[""], isnull=True)
        expected = {"rank__isnull": True}
        assert actual == expected

    def test_disabled_with_regular_value(self):
        actual = self.get_output_of_field(rank=["1", "2", "3"], isnull=False)
        expected = {"rank__in": [1, 2, 3]}
        assert actual == expected

    def test_disabled_with_none_value_and_regulars(self):
        with pytest.raises(InvalidData) as exc_info:
            self.get_output_of_field(rank=["1", "2", "3", ""], isnull=False)
        assert "rank" in exc_info.value.errors
        assert exc_info.value.errors["rank"] == [
            "Validation error at 4th item: This field is required."
        ]

    def test_disabled_with_only_none_value(self):
        with pytest.raises(InvalidData) as exc_info:
            self.get_output_of_field(rank=[""], isnull=False)
        assert "rank" in exc_info.value.errors
        assert exc_info.value.errors["rank"] == [
            "Validation error at 1st item: This field is required."
        ]

    def test_ben(self):
        source = MultiValueDict({"parent_id__in": [1, 2, None]})
        filters = filternaut.filters.IntegerFilter(
            "parent_id", lookups="in", none_to_isnull=True
        )
        parsed = filters.parse_to_dict(source)
        pass
