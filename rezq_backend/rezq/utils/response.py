from django.conf import settings
from django.http import HttpResponse


class HttpResponseUnauthorized(HttpResponse):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.status_code = 401
        self['WWW-Authenticate'] = f'Bearer realm="{settings.AUTH_REALM}"'


class HttpResponseTooManyRequests(HttpResponse):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.status_code = 429
