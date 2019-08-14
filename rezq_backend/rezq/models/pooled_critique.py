from django.conf import settings
from django.core.cache import cache
from rezq.models.abstract.critique import Critique


class PooledCritique(Critique):

    @property
    def upvotes(self):
        cache_key = f'pcv:{self.id}'
        cached_votes = cache.get(cache_key)
        if cached_votes is not None and not settings.DEBUG:
            return cached_votes

        votes = 0
        for v in self.pooledcritiquevote_set.all():
            votes += 1 if v.is_upvote else -1

        cache.set(cache_key, votes, 30)

        return votes
