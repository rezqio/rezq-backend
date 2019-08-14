from testing.container import backend_container
from testing.gql_client import GqlClient


FAILED_TO_AUTHENTICATE = (
    '{"login": "The information you provided is incorrect."}'
)


def test_create_token_user_not_exist():
    with backend_container() as uri:
        client = GqlClient(uri, login=False)
        data = client.public("""
            mutation {
                createToken(email: "foobar@rezq.io", password: "password") {
                    token
                    errors
                }
            }
        """)
        assert data['createToken']['token'] is None
        assert data['createToken']['errors'] == FAILED_TO_AUTHENTICATE
