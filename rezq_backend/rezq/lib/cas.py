import logging
from xml.etree import ElementTree

import requests
from django.conf import settings
from requests.exceptions import ConnectionError
from retrying import retry


logger = logging.getLogger(__name__)


CAS_VALIDATE_URL_TEMPLATE = (
    'https://cas.uwaterloo.ca/cas/serviceValidate?'
    'service={}/{{}}&ticket={{}}'
).format(settings.FRONTEND_URL)


@retry(
    stop_max_attempt_number=3,
    wait_exponential_multiplier=1000,
    retry_on_exception=lambda e: isinstance(e, ConnectionError),
)
def _get_cas_response(url):
    return requests.get(url).text


def validate_ticket(ticket, service):
    url = CAS_VALIDATE_URL_TEMPLATE.format(service, ticket)

    try:
        resp = _get_cas_response(url)
    except ConnectionError:
        logger.error('Could not connect to Waterloo CAS')
        return None

    try:
        tree = ElementTree.fromstring(resp)
    except ElementTree.ParseError:
        logger.info('Could not parse response')
        return None

    nested = tree.find('{http://www.yale.edu/tp/cas}authenticationSuccess')

    if nested is None:
        logger.info('Failed to authenticate with CAS')
        return None

    user = nested.find('{http://www.yale.edu/tp/cas}user')

    if user is None:
        logger.error('Malformed CAS response')
        return None

    return user.text
