import json

from django.contrib.auth.models import User
from django.core.handlers.wsgi import WSGIRequest
from django.http import HttpResponse, HttpResponseBadRequest
from django.test import Client, TestCase

from filternaut.exceptions import InvalidData
from filternaut.filters import CharFilter, ChoiceFilter, EmailFilter

try:
    from django.test import RequestFactory
except ImportError:

    class RequestFactory(Client):
        """
        Django 1.2 does not have RequestFactory. credit:
        https://djangosnippets.org/snippets/963/
        """

        def request(self, **request):
            """
            Similar to parent class, but returns the request object as soon as
            it has created it.
            """
            environ = {
                "HTTP_COOKIE": self.cookies,
                "PATH_INFO": "/",
                "QUERY_STRING": "",
                "REQUEST_METHOD": "GET",
                "SCRIPT_NAME": "",
                "SERVER_NAME": "testserver",
                "SERVER_PORT": 80,
                "SERVER_PROTOCOL": "HTTP/1.1",
            }
            environ.update(self.defaults)
            environ.update(request)
            return WSGIRequest(environ)


def user_to_native(user):
    return dict(
        id=user.id, username=user.username, email=user.email, first_name=user.first_name
    )


def resp_to_users(resp):
    data = json.loads(resp.content.decode("utf-8"))
    pks = [d["id"] for d in data]
    users = []
    for pk in pks:
        # get+append to preserve order of resp'd data
        users.append(User.objects.get(pk=pk))
    return users


def my_view(request):
    names = "nomatch", "Bret", "Jemaine", "Murray"
    filters = CharFilter("username") | (
        EmailFilter("email") & ChoiceFilter("first_name", choices=zip(names, names))
    )
    try:
        query = filters.parse(request.GET)
        users = User.objects.filter(query)
        native = [user_to_native(u) for u in users]
        return HttpResponse(json.dumps(native))
    except InvalidData as ex:
        return HttpResponseBadRequest(json.dumps(ex.errors))


class FullStackTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.u1 = User.objects.create(
            username="one", email="one@example.org", first_name="Bret"
        )
        self.u2 = User.objects.create(
            username="two", email="two@example.org", first_name="Jemaine"
        )
        self.u3 = User.objects.create(
            username="three", email="three@example.org", first_name="Murray"
        )

    def test_request_no_params(self):
        """
        With no required filters, we present no filtering arguments and get all
        users returned.
        """
        request = self.factory.get("/my_view/")
        resp = my_view(request)
        actual = resp_to_users(resp)
        expected = [self.u1, self.u2, self.u3]

        assert resp.status_code == 200
        assert actual == expected

    def test_request_irrelevant_params(self):
        """
        Filternaut doesn't care if the 'foo' param is present
        """
        request = self.factory.get("/my_view/?foo=bar")
        resp = my_view(request)
        actual = resp_to_users(resp)
        expected = [self.u1, self.u2, self.u3]

        assert resp.status_code == 200
        assert actual == expected

    def test_request_nonmatching_param(self):
        """
        Filter on a non-existing username. Nothing comes back.
        """
        data = {"username": "nomatch"}
        request = self.factory.get("/my_view/", data=data)
        resp = my_view(request)
        actual = resp_to_users(resp)
        expected = []

        assert resp.status_code == 200
        assert actual == expected

        assert resp.status_code == 200
        assert actual == expected

    def test_both_ANDed_filters_but_nonmatching(self):
        """
        Provide both ANDed filters, but with values that don't match anything.
        Expect no results.
        """
        data = {"email": "nomatch@example.org", "first_name": "nomatch"}
        request = self.factory.get("/my_view/", data=data)
        resp = my_view(request)
        actual = resp_to_users(resp)
        expected = []

        assert resp.status_code == 200
        assert actual == expected

    def test_both_ANDed_filters_mixed_matching(self):
        """
        Provide both ANDed filters, with a matching email, but non-matching
        first name. Expect no results.
        """
        data = {
            "email": "one@example.org",  # a match
            "first_name": "nomatch",
        }  # a non-match
        request = self.factory.get("/my_view/", data=data)
        resp = my_view(request)
        actual = resp_to_users(resp)
        expected = []

        assert resp.status_code == 200
        assert actual == expected

    def test_both_ANDed_filters_matching(self):
        """
        Provide both ANDed filters. Both are matching. Expect one matching
        result.
        """
        data = {"email": "one@example.org", "first_name": "Bret"}
        request = self.factory.get("/my_view/", data=data)
        resp = my_view(request)
        actual = resp_to_users(resp)
        expected = [self.u1]

        assert resp.status_code == 200
        assert actual == expected

    def test_invalid_filters(self):
        """
        Get some validation errors.
        """
        data = {"email": "not an email", "first_name": "not a choice"}
        request = self.factory.get("/my_view/", data=data)
        resp = my_view(request)
        errors = json.loads(resp.content.decode("utf-8"))

        assert resp.status_code == 400
        assert "email" in errors
        assert "first_name" in errors
