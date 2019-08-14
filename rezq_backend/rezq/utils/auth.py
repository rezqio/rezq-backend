import logging
from datetime import timedelta

from django.utils import timezone
from rezq.lib import jwt
from server.constants import AUTH_TOKEN_EXPIRE_MINUTES
from server.constants import EMAIL_VERIFICATION_TOKEN_EXPIRE_MINUTES
from server.constants import PASSWORD_RESET_TOKEN_EXPIRE_MINUTES

logger = logging.getLogger(__name__)


def create_token(user_id, minutes=AUTH_TOKEN_EXPIRE_MINUTES):
    expires = timezone.now() + timedelta(minutes=minutes)
    return (
        jwt.encode({
            'user': str(user_id),
            'exp': expires,
        }),
        expires,
    )


def create_password_reset_token(
        user_email,
        minutes=PASSWORD_RESET_TOKEN_EXPIRE_MINUTES,
):
    expires = timezone.now() + timedelta(minutes=minutes)
    return jwt.encode({
        'pass_reset_email': user_email,
        'exp': expires,
    })


def validate_password_reset_token(token):
    try:
        payload = jwt.decode(token)
        email = payload['pass_reset_email']

        return True, email
    except Exception as e:
        logger.info(f'{type(e)}: {str(e)}')
        return False, None


def create_email_verification_token(
    user_id,
    user_email,
    minutes=EMAIL_VERIFICATION_TOKEN_EXPIRE_MINUTES,
):
    expires = timezone.now() + timedelta(minutes=minutes)
    return jwt.encode({
        'email_verification_user_id': str(user_id),
        'email_verification_user_email': user_email,
        'exp': expires,
    })


def validate_email_verification_token(token):
    try:
        payload = jwt.decode(token)
        user_id = payload['email_verification_user_id']
        user_email = payload['email_verification_user_email']

        return True, user_id, user_email
    except Exception as e:
        logger.info(f'{type(e)}: {str(e)}')
        return False, None


def create_email_unsubscribe_token(
    user_id,
):
    return jwt.encode({
        'email_unsub_user_id': str(user_id),
    })


def validate_email_unsubscribe_token(token):
    try:
        payload = jwt.decode(token)
        user_id = payload['email_unsub_user_id']

        return True, user_id
    except Exception as e:
        logger.info(f'{type(e)}: {str(e)}')
        return False, None
