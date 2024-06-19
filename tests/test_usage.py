from unittest import TestCase

from django.http import QueryDict

from filternaut.filters import FieldFilter, Filter


class ExtensionTests(TestCase):
    """
    Check that folk can extend filternaut in useful ways.
    """

    def test_with_custom_field(self):
        """
        Custom fields should work with FieldFilter.
        """

        class DoublingField(object):
            def clean(self, value):
                return int(value) * 2

        filter = FieldFilter("integer", field=DoublingField())
        query = filter.parse({"integer": 3})

        actual = dict(query.children)
        expected = {"integer": 6}
        assert actual == expected

    def test_basic_filter_with_subclassed_clean(self):
        """
        Basic filters should let their source values be cleaned.
        """

        class PotatoFilter(Filter):
            def clean(self, value):
                return "potato"

        filter = PotatoFilter("fieldname")
        assert filter.clean("anything") == "potato"

    def test_specialcase_multiple_source_values(self):
        """
        If multiple source values are presented to parse, make sure we allow
        handling the picking of a single value.
        """

        class BiggestValueFilter(Filter):
            def get_source_value(self, key, data, many=False):
                values = data.getlist(key)
                return max(map(int, values))

        data = QueryDict("field=3&field=6&field=1&field=2")
        filter = BiggestValueFilter("field")
        query = filter.parse(data)
        actual = dict(query.children)
        expected = {"field": 6}
        assert actual == expected
