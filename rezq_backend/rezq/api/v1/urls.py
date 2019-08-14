from django.conf import settings
from django.urls import path
from django.views.decorators.csrf import csrf_exempt
from rezq.api.v1.middleware import QueryDepthMiddleware
from rezq.api.v1.middleware import QueryTimeoutMiddleware
from rezq.api.v1.schema import private_schema
from rezq.api.v1.schema import public_schema
from rezq.api.views import PrivateGraphQLView
from rezq.api.views import PublicGraphQLView


urlpatterns = [
    path(
        'public/',
        csrf_exempt(
            PublicGraphQLView.as_view(
                graphiql=settings.DEBUG,
                schema=public_schema,
                middleware=[QueryTimeoutMiddleware, QueryDepthMiddleware],
            ),
        ),
    ),
    path(
        'private/',
        PrivateGraphQLView.as_view(
            graphiql=settings.DEBUG,
            schema=private_schema,
            middleware=[QueryTimeoutMiddleware, QueryDepthMiddleware],
        ),
    ),
]
