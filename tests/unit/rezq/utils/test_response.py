from django.conf import settings
from django.http import HttpResponse
from rezq.utils.response import HttpResponseTooManyRequests
from rezq.utils.response import HttpResponseUnauthorized


def test_HttpResponseUnauthorized():
    response = HttpResponseUnauthorized()

    assert isinstance(response, HttpResponse)
    assert response.status_code == 401

    www_auth = f'Bearer realm="{settings.AUTH_REALM}"'
    assert response['WWW-Authenticate'] == www_auth


def test_HttpResponseTooManyRequests():
    response = HttpResponseTooManyRequests()

    assert isinstance(response, HttpResponse)
    assert response.status_code == 429
