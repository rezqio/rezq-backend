import logging

from django.conf import settings
from django.db import models
from rezq.lib import jwt
from rezq.lib.s3 import S3
from rezq.models.abstract.timestamp_model import TimestampModel
from rezq.models.abstract.timestamp_model import TimestampModelManager
from rezq.models.pool import Pool
from rezq.models.user import User
from rezq.validators import validate_industries


logger = logging.getLogger(__name__)


class ResumeManager(TimestampModelManager):

    def get_by_token(self, token):
        try:
            id = jwt.decode(token)['id']
        except Exception as e:
            logger.info(f'{type(e)}: {str(e)}')
            raise self.model.DoesNotExist(
                'Resume matching query does not exist.',
            )

        return self.get(id=id, link_enabled=True)


class Resume(TimestampModel):

    objects = ResumeManager()

    uploader = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )

    name = models.CharField(max_length=32)

    description = models.CharField(
        max_length=256,
        default='',
        blank=True,
    )

    # Comma delimited list of rezq.server.constants.INDUSTRIES
    industries = models.TextField(
        validators=[validate_industries],
    )

    notes_for_critiquer = models.CharField(
        max_length=1024,
        default='',
        blank=True,
    )

    # Link sharing
    link_enabled = models.BooleanField(default=False)

    pool = models.ForeignKey(
        Pool,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    @property
    def download_url(self):
        return S3.get_download_url(
            settings.S3_RESUME_BUCKET,
            f'{self.id}.pdf',
        )

    @property
    def upload_info(self):
        return S3.get_upload_dict(
            settings.S3_RESUME_BUCKET,
            f'{self.id}.pdf',
        )

    @property
    def thumbnail_download_url(self):
        return S3.get_download_url(
            settings.S3_RESUME_BUCKET,
            f'{self.id}.jpg',
        )

    @property
    def thumbnail_upload_info(self):
        return S3.get_upload_dict(
            settings.S3_RESUME_BUCKET,
            f'{self.id}.jpg',
        )

    @property
    def token(self):
        return jwt.encode(
            {'id': str(self.id)},
        ) if self.link_enabled else None

    def delete(self):
        S3.delete(settings.S3_RESUME_BUCKET, f'{self.id}.pdf')
        S3.delete(settings.S3_RESUME_BUCKET, f'{self.id}.jpg')
        super().delete()

    if settings.DEBUG:
        def save(self, *args, **kwargs):
            from rezq.models.dev import MockS3File
            try:
                MockS3File.objects.get(id=f'{self.id}.pdf')
            except MockS3File.DoesNotExist:
                MockS3File.objects.create(id=f'{self.id}.pdf')
                MockS3File.objects.create(id=f'{self.id}.jpg')

            super().save(*args, **kwargs)

    def __str__(self):
        return self.name
