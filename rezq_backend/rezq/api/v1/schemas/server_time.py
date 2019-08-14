import graphene
from django.utils import timezone


class ServerTimeQuery:

    server_time = graphene.types.datetime.DateTime()

    def resolve_server_time(self, info, **kwargs):
        return timezone.now()
