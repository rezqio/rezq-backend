from datetime import timedelta
from unittest import mock

import pytest
from django.http import HttpResponseBadRequest
from django.http import HttpResponseForbidden
from django.utils import timezone
from rezq.lib import jwt
from rezq.mixins.auth_mixin import AuthMixin
from rezq.models import User
from rezq.utils.response import HttpResponseUnauthorized


ARGS = ['foo', 'bar']
KWARGS = {'biz': 'baz'}
USER = 'USER'
RESPONSE = 'RESPONSE'

GOOD_TOKEN = jwt.encode({
    'user': 0, 'exp': timezone.now() + timedelta(minutes=60),
})
EXPIRED_TOKEN = jwt.encode({
    'user': 0, 'exp': timezone.now() - timedelta(minutes=60),
})
BAD_SIGNATURE_TOKEN = GOOD_TOKEN[:-1]
MISSING_USER_TOKEN = jwt.encode({
    'exp': timezone.now() + timedelta(minutes=60),
})


@pytest.mark.parametrize(
    'expected_log,token,resp_type', [
        ('Missing auth header', None, HttpResponseBadRequest),
        ('Bad auth format', 'a bad format', HttpResponseBadRequest),
        (
            'Wrong auth type',
            'Basic QWxhZGRpbjpPcGVuU2VzYW1l',
            HttpResponseBadRequest,
        ),
        (
            "<class 'jwt.exceptions.ExpiredSignatureError'>: " +
            'Signature has expired',
            f'Bearer {EXPIRED_TOKEN}',
            HttpResponseUnauthorized,
        ),
        (
            "<class 'jwt.exceptions.DecodeError'>: Not enough segments",
            'Bearer malformed_token',
            HttpResponseBadRequest,
        ),
        (
            "<class 'jwt.exceptions.InvalidSignatureError'>: " +
            'Signature verification failed',
            f'Bearer {BAD_SIGNATURE_TOKEN}',
            HttpResponseUnauthorized,
        ),
        (
            'Missing user id from payload',
            f'Bearer {MISSING_USER_TOKEN}', HttpResponseBadRequest,
        ),
        (
            'User does not exist; probably deleted account',
            f'Bearer {GOOD_TOKEN}',
            HttpResponseForbidden,
        ),
    ],
)
@mock.patch(
    'rezq.mixins.auth_mixin.User.objects.get', side_effect=User.DoesNotExist(),
)
@mock.patch('rezq.mixins.auth_mixin.logger')
def test_dispatch_unauthorized(
    mock_logger, mock_user_get, expected_log, token, resp_type,
):
    mock_auth_view = AuthMixin()
    mock_request = mock.MagicMock()

    mock_request.META = {}
    if token:
        mock_request.META['HTTP_AUTHORIZATION'] = token

    response = mock_auth_view.dispatch(mock_request, *ARGS, **KWARGS)

    assert isinstance(response, resp_type)
    mock_logger.info.assert_called_with(expected_log)


@mock.patch(
    'rezq.mixins.auth_mixin.User.objects.get', return_value=USER,
)
@mock.patch('rezq.mixins.auth_mixin.logger')
def test_dispatch_authorized(mock_logger, mock_user_get):
    mock_dispatch = mock.MagicMock(return_value=RESPONSE)

    class BaseView():
        dispatch = mock_dispatch

    class MockAuthView(AuthMixin, BaseView):
        pass

    mock_auth_view = MockAuthView()
    mock_request = mock.MagicMock()

    mock_request.META = {'HTTP_AUTHORIZATION': f'Bearer {GOOD_TOKEN}'}

    response = mock_auth_view.dispatch(mock_request, *ARGS, **KWARGS)

    mock_dispatch.assert_called_with(mock.ANY, *ARGS, **KWARGS)
    assert not mock_logger.info.called
    assert response == RESPONSE
    assert mock_request.user == USER
