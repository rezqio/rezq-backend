import logging

import facebook
from requests.exceptions import ConnectionError
from retrying import retry


logger = logging.getLogger(__name__)


GRAPH_VERSION = '3.0'


@retry(
    stop_max_attempt_number=3,
    wait_exponential_multiplier=1000,
    retry_on_exception=lambda e: isinstance(e, ConnectionError),
)
def _get_profile_object(graph):
    return graph.get_object(id='me?fields=first_name,last_name')


def get_profile(token):
    try:
        graph = facebook.GraphAPI(access_token=token, version=GRAPH_VERSION)
    except Exception:
        logger.critical('Failed to construct Facebook client')
        return None

    try:
        return _get_profile_object(graph)
    except facebook.GraphAPIError:
        logger.info('Failed to authenticate with Facebook')
        return None
    except ConnectionError:
        logger.error('Could not connect to Facebook')
        return None


def validate_token(token):
    profile = get_profile(token)
    return profile.get('id') if profile else None
