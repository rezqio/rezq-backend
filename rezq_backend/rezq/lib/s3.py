import abc
import logging

import boto3
from botocore.exceptions import ClientError
from django.conf import settings


logger = logging.getLogger(__name__)

EXPIRES_IN = 300  # seconds
MIN_PDF_SIZE = 50  # bytes
MAX_PDF_SIZE = 5242880  # bytes (5MB)


class _AbstractS3(metaclass=abc.ABCMeta):
    """S3 module

    Sourced from:
    https://github.com/gymapplife/backend/blob/master/backend/lib/s3.py
    """

    @abc.abstractmethod
    def get_upload_dict(self, bucket, key):
        """POST to a presigned url

        Javascript usage example:
        https://github.com/gymapplife/frontend/blob/master/src/components/Photos.js#L40
        """
        pass

    @abc.abstractmethod
    def get_download_url(self, bucket, key):
        """GET from a presigned url
        """
        pass

    @abc.abstractmethod
    def delete(self, bucket, key):
        pass


class _MockS3(_AbstractS3):

    def get_upload_dict(self, bucket, key):
        return {
            'url': f'{settings.BASE_URL}/mock-s3/',
            'fields': {
                'key': key,
                'AWSAccessKeyId': 'foo',
                'policy': 'bar',
                'signature': 'baz',
            },
        }

    def get_download_url(self, bucket, key):
        from django.core.files.storage import default_storage
        from rezq.models.dev import MockS3File

        try:
            f = MockS3File.objects.get(id=key)
            if not default_storage.exists(f.file):
                logger.info(f'{f.file} not found on filesystem.')
                return None
        except Exception as e:
            logger.info(f'{type(e)}: {str(e)}')
            return None

        return f'{settings.BASE_URL}/mock-s3/?key={key}'

    def delete(self, bucket, key):
        pass


class _S3(_AbstractS3):
    """Thanks George Gao
    """

    def __init__(self):
        self.client = boto3.client('s3')

    def get_upload_dict(self, bucket, key):
        conditions = [
            ['content-length-range', MIN_PDF_SIZE, MAX_PDF_SIZE],
        ]

        return self.client.generate_presigned_post(
            Bucket=bucket,
            Key=key,
            Conditions=conditions,
            ExpiresIn=EXPIRES_IN,
        )

    def get_download_url(self, bucket, key):
        try:
            self.client.head_object(Bucket=bucket, Key=key)
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                return None
            raise

        return self.client.generate_presigned_url(
            'get_object',
            Params={
                'Bucket': bucket,
                'Key': key,
            },
            HttpMethod='GET',
            ExpiresIn=EXPIRES_IN,
        )

    def delete(self, bucket, key):
        self.client.delete_object(
            Bucket=bucket,
            Key=key,
        )


S3 = _MockS3() if settings.DEBUG else _S3()
