import logging

from google.auth.exceptions import TransportError
from google.auth.transport import requests
from google.oauth2 import id_token
from retrying import retry


logger = logging.getLogger(__name__)


CLIENT_ID = (
    '318458844815-pujstcn760q3b2fu9pm5m9dn14mj3c62.apps.googleusercontent.com'
)
ISSUERS = ('accounts.google.com', 'https://accounts.google.com')


@retry(
    stop_max_attempt_number=3,
    wait_exponential_multiplier=1000,
    retry_on_exception=lambda e: isinstance(e, TransportError),
)
def _verify_token(token):
    return id_token.verify_oauth2_token(
        token,
        requests.Request(),
        CLIENT_ID,
    )


def _get_token_info(token):
    """
    https://developers.google.com/identity/sign-in/web/backend-auth
    """
    try:
        idinfo = _verify_token(token)
    except ValueError:
        logger.info('Failed to authenticate with Google')
        return None
    except TransportError:
        logger.error('Could not connect to Google')
        return None

    if idinfo.get('iss') not in ISSUERS:
        logger.info('Incorrect issuer')
        return None

    return idinfo


def validate_token(token):
    return _get_token_info(token).get('sub')


def get_profile(token):
    profile = _get_token_info(token)
    return {
        'id': profile.get('sub'),
        'first_name': profile.get('given_name'),
        'last_name': profile.get('family_name'),
    }
