from django.db import models
from rezq.models.abstract.timestamp_model import TimestampModel
from rezq.models.pooled_critique import PooledCritique
from rezq.models.user import User


class PooledCritiqueComment(TimestampModel):

    critique = models.ForeignKey(
        PooledCritique,
        on_delete=models.CASCADE,
    )

    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    comment = models.CharField(max_length=1024)
