from django.db import models
from rezq.models.abstract.timestamp_model import TimestampModel
from rezq.models.linked_critique import LinkedCritique
from rezq.models.user import User


class LinkedCritiqueComment(TimestampModel):

    critique = models.ForeignKey(
        LinkedCritique,
        on_delete=models.CASCADE,
    )

    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    comment = models.CharField(max_length=1024)
