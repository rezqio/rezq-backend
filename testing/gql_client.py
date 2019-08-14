import requests


class GqlClient:

    def __init__(self, endpoint, login=True):
        self._public_endpoint = f'{endpoint}/v1/public/'
        self._private_endpoint = f'{endpoint}/v1/private/'

        self._client = requests.session()
        self._client.head(f'{endpoint}/~csrf')
        self._client.headers['X-CSRFToken'] = self._client.cookies['csrftoken']

        if login:
            self.login()

    def _query(self, gql, is_public):
        resp = self._client.post(
            self._public_endpoint if is_public else self._private_endpoint,
            json={'query': gql},
        )

        resp.raise_for_status()

        return resp.json()['data']

    def public(self, gql):
        return self._query(gql, True)

    def private(self, gql):
        return self._query(gql, False)

    def login(self):
        token = self.public("""
            mutation {
                createToken(email: "dzheng@rezq.io", password: "password") {
                    token
                }
            }
        """)['createToken']['token']

        self._client.headers['Authorization'] = f'Bearer {token}'
