import re

import simplejson as json
from rezq.models import User


OPERATION_NAME_REGEX = re.compile(r'[a-zA-Z]+')


def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0]
    return request.META.get('REMOTE_ADDR')


def get_gql_operation(request):
    operation_name = None
    is_mutation = False

    if request.body:
        body_json = json.loads(request.body.decode('utf-8'))
        operation_name = body_json.get('operationName')

        if operation_name is None:
            query = body_json['query'].lstrip()

            if query[:8] == 'mutation':
                is_mutation = True
                query = query[8:]

            re_search = re.search(OPERATION_NAME_REGEX, query)

            if re_search:
                operation_name = re_search.group()

    return operation_name, is_mutation


def get_client_info_str(request):
    ip = get_client_ip(request)
    user = request.user if type(request.user) is User else None
    if user:
        if user.waterloo_id:
            return f'{ip} - {user.id} - {user.waterloo_id} -'
        else:
            return f'{ip} - {user.id} - -'
    else:
        return f'{ip} - - -'
