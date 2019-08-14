import logging

from django.core.exceptions import ValidationError
from django.http import HttpResponseBadRequest
from django.http import HttpResponseForbidden
from ratelimit.utils import is_ratelimited
from rezq.lib import jwt
from rezq.models import User
from rezq.utils.request import get_client_ip
from rezq.utils.response import HttpResponseTooManyRequests
from rezq.utils.response import HttpResponseUnauthorized


logger = logging.getLogger(__name__)


class AuthMixin:

    def dispatch(self, request, *args, **kwargs):
        try:
            auth = request.META['HTTP_AUTHORIZATION'].split()
        except KeyError:
            logger.info('Missing auth header')
            return HttpResponseBadRequest()

        if len(auth) != 2:
            logger.info('Bad auth format')
            return HttpResponseBadRequest()

        if auth[0] != 'Bearer':
            logger.info('Wrong auth type')
            return HttpResponseBadRequest()

        try:
            unverified_payload = jwt.decode(auth[1], verify=False)
        except Exception as e:
            logger.info(f'{type(e)}: {str(e)}')
            return HttpResponseBadRequest()

        try:
            unverified_uid = str(unverified_payload['user'])
        except KeyError:
            logger.info('Missing user id from payload')
            return HttpResponseBadRequest()

        if is_ratelimited(
            request,
            group='',
            key=lambda group, request, uid=unverified_uid: uid,
            rate='88/m',
            increment=True,
        ):
            logger.error(
                f'{get_client_ip(request)} exceeded rate limit threshold for '
                f'user {unverified_uid}',
            )
            return HttpResponseTooManyRequests()

        try:
            payload = jwt.decode(auth[1])
        except Exception as e:
            logger.info(f'{type(e)}: {str(e)}')
            return HttpResponseUnauthorized()

        try:
            user = User.objects.get(id=payload['user'])
        except User.DoesNotExist:
            logger.info('User does not exist; probably deleted account')
            return HttpResponseForbidden()
        except ValidationError as e:
            logger.info(f'{type(e)}: {str(e)}')
            return HttpResponseForbidden()

        request.user = user

        return super().dispatch(request, *args, **kwargs)
