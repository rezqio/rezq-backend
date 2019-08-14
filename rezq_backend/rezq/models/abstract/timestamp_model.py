import uuid

from django.core.exceptions import ValidationError
from django.db import models


class TimestampModelManager(models.Manager):

    def get(self, *args, **kwargs):
        try:
            return super().get(*args, **kwargs)
        except ValidationError as e:
            if e.message[-5:] == 'UUID.':
                raise self.model.DoesNotExist()
            raise e


class TimestampModel(models.Model):

    class Meta:
        abstract = True

    objects = TimestampModelManager()

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    created_on = models.DateTimeField(auto_now_add=True)
    updated_on = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.__class__.__name__
