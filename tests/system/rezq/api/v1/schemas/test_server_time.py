from testing.container import backend_container
from testing.gql_client import GqlClient


def test_server_time():
    with backend_container() as uri:
        client = GqlClient(uri, login=False)
        data = client.public('{serverTime}')
        assert 'serverTime' in data
