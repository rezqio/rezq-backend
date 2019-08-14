from django.db import models
from rezq.models.abstract.timestamp_model import TimestampModel
from rezq.models.pooled_critique import PooledCritique
from rezq.models.user import User


class PooledCritiqueVote(TimestampModel):

    voter = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
    )

    critique = models.ForeignKey(
        PooledCritique,
        on_delete=models.CASCADE,
    )

    # Otherwise is downvote
    is_upvote = models.BooleanField(default=True)

    class Meta:
        unique_together = ('voter', 'critique')
