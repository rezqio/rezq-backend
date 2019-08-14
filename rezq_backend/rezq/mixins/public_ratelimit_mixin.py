import logging

from ratelimit.utils import is_ratelimited
from rezq.utils.request import get_client_ip
from rezq.utils.request import get_gql_operation
from rezq.utils.response import HttpResponseTooManyRequests


logger = logging.getLogger(__name__)


DEFAULT_QUERY_RATE = '60/m'
QUERY_RATELIMITS = {
    'resume': '88/m',
    'linkedCritique': '88/m',
}

DEFAULT_MUTATION_RATE = '30/m'
MUTATION_RATELIMITS = {
    'saveLinkedCritique': '88/m',
}


class PublicRatelimitMixin:

    def dispatch(self, request, *args, **kwargs):
        operation_name, is_mutation = get_gql_operation(request)

        if is_mutation:
            rate = MUTATION_RATELIMITS.get(
                operation_name, DEFAULT_MUTATION_RATE,
            )
        else:
            rate = QUERY_RATELIMITS.get(
                operation_name, DEFAULT_QUERY_RATE,
            )

        client_ip = get_client_ip(request)

        if is_ratelimited(
            request,
            group='',
            key=lambda group, request, client_ip=client_ip: client_ip,
            rate=rate,
            increment=True,
        ):
            logger.error(
                f'{get_client_ip(request)} exceeded rate limit threshold',
            )
            return HttpResponseTooManyRequests()

        return super().dispatch(request, *args, **kwargs)
