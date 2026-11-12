from types import SimpleNamespace
from unittest.mock import patch

from django.http import HttpResponse
from django.test import RequestFactory, SimpleTestCase

from .views.core import FinloView


class FragmentHeaderTests(SimpleTestCase):
    def test_normal_request_restores_cached_headers_after_fragment(self):
        self.check_fragment(False)

    def test_exception_restores_original_htmx_headers(self):
        self.check_fragment(True)

    def check_fragment(self, raises):
        request = RequestFactory().get('/shell/', HTTP_HX_REQUEST='false')
        request.user = object()
        user = request.user
        headers = request.headers
        original_get = request.GET
        view = FinloView()
        view.request = request

        def fragment(req):
            self.assertEqual(req.headers['HX-Request'], 'true')
            self.assertEqual(req.method, 'GET')
            self.assertIs(req.user, user)
            if raises:
                raise ValueError('fragment failed')
            return HttpResponse('fragment')

        match = SimpleNamespace(func=fragment, args=(), kwargs={})
        with patch('django.urls.resolve', return_value=match):
            result = view._render_subview('/fragment/?page=2')
        self.assertEqual(result, '' if raises else 'fragment')
        self.assertIs(request.headers, headers)
        self.assertEqual(request.META['HTTP_HX_REQUEST'], 'false')
        self.assertIs(request.GET, original_get)
        self.assertIs(request.user, user)
        self.assertEqual(request.method, 'GET')
