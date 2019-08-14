from django.db import models
from rezq.models.abstract.timestamp_model import TimestampModel
from rezq.models.matched_critique import MatchedCritique
from rezq.models.user import User


class MatchedCritiqueComment(TimestampModel):

    critique = models.ForeignKey(
        MatchedCritique,
        on_delete=models.CASCADE,
    )

    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    comment = models.CharField(max_length=1024)
