import requests

from testing.container import backend_container


def test_mock_s3():
    with backend_container() as uri:
        assert requests.head(f'{uri}/mock-s3/').status_code == 400


def test_admin():
    with backend_container() as uri:
        assert requests.head(f'{uri}/admin/login/').status_code == 302


def test_v1_public():
    with backend_container() as uri:
        assert requests.head(f'{uri}/v1/public/').status_code == 405


def test_v1_private():
    with backend_container() as uri:
        assert requests.head(f'{uri}/v1/private/').status_code == 400
