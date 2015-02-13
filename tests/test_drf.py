from django.contrib.auth.models import User
import mock

from filternaut.filters import EmailFilter


try:
    from rest_framework import test, generics
    from filternaut.drf import FilternautBackend
except ImportError:
    from nose import SkipTest
    raise SkipTest('Django REST Framework must be installed to test DRF'
                   'integration')


class IntegrationTests(test.APITestCase):

    def setUp(self):
        self.factory = test.APIRequestFactory()
        self.request = self.factory.get('/users/', data={
            'email': 'user@example.org'})

    def test_backend_requires_filterattr(self):
        class UserView(generics.ListAPIView):
            queryset = User.objects.all()
            filter_backends = (FilternautBackend, )

        queryset = mock.Mock()
        uv = UserView()
        self.request = uv.initialize_request(self.request)
        uv.request = self.request
        with self.assertRaises(AttributeError):
            uv.filter_queryset(queryset)

    def test_backend_filters_queryset(self):
        class UserView(generics.ListAPIView):
            queryset = User.objects.all()
            filter_backends = (FilternautBackend, )
            filternaut_filters = EmailFilter('email')

        queryset = mock.Mock()
        uv = UserView()
        self.request = uv.initialize_request(self.request)
        uv.request = self.request
        uv.filter_queryset(queryset)
        assert queryset.filter.called

    def test_callable_filterattr(self):
        class UserView(generics.ListAPIView):
            queryset = User.objects.all()
            filter_backends = (FilternautBackend, )

            def filternaut_filters(self, request):
                return EmailFilter('email')

        queryset = mock.Mock()
        uv = UserView()
        self.request = uv.initialize_request(self.request)
        uv.request = self.request
        uv.filter_queryset(queryset)
        assert queryset.filter.called
