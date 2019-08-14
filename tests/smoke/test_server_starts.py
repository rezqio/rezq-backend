from testing.container import backend_container


def test_server_starts():
    with backend_container():
        pass
