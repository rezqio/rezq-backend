from django.conf import settings
from django.db import models
from rezq.models.abstract.timestamp_model import TimestampModel


class MockS3File(TimestampModel):

    id = models.CharField(primary_key=True, max_length=50, unique=True)
    file = models.FileField(upload_to='mock-s3/', null=True, blank=True)

    @property
    def download_url(self):
        return f'{settings.BASE_URL}/mock-s3?key={self.id}'
