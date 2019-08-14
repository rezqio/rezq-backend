import random
from contextlib import contextmanager

import docker
import requests
from docker.errors import APIError
from requests.exceptions import ConnectionError
from retrying import retry


MIN_PORT = 49152
MAX_PORT = 65535

_docker_client = docker.from_env()


@retry(
    stop_max_attempt_number=3,
    stop_max_delay=10000,
    retry_on_exception=lambda e: isinstance(e, APIError),
)
def _start_testing_container():
    port = random.randint(MIN_PORT, MAX_PORT)
    backend_uri = f'http://localhost:{port}'
    backend_container = _docker_client.containers.run(
        f'rezq.io/backend-dev-testing:latest',
        detach=True,
        ports={'80/tcp': port},
        environment={'DJANGO_BASE_URL': backend_uri},
    )
    return backend_container, backend_uri


@retry(
    stop_max_attempt_number=3,
    wait_exponential_multiplier=1000,
    retry_on_exception=lambda e: isinstance(e, ConnectionError),
)
def _wait_for_connection(uri):
    requests.head(uri)


@contextmanager
def backend_container():
    _backend_container, _backend_uri = _start_testing_container()

    try:
        _wait_for_connection(_backend_uri)
        yield _backend_uri
    finally:
        _backend_container.remove(force=True)
