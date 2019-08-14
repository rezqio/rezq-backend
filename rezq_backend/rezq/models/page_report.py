from django.core.validators import MaxValueValidator
from django.core.validators import MinValueValidator
from django.db import models
from rezq.models.abstract.timestamp_model import TimestampModel
from rezq.models.user import User


class PageReport(TimestampModel):

    reporter = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    pathname = models.CharField(max_length=128)

    search = models.CharField(
        max_length=512,
        null=True,
        blank=True,
    )

    stars = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        null=True,
        blank=True,
    )

    message = models.CharField(
        max_length=1024,
        null=True,
        blank=True,
    )

    reply_to = models.EmailField(
        null=True,
        blank=True,
    )
