from graphene_django.views import GraphQLView
from rezq.mixins import AuthMixin
from rezq.mixins import PublicRatelimitMixin


class PublicGraphQLView(PublicRatelimitMixin, GraphQLView):
    pass


class PrivateGraphQLView(AuthMixin, GraphQLView):
    pass
