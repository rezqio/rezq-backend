import uuid

from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.models import BaseUserManager
from django.core.validators import RegexValidator
from django.db import models
from rezq.lib.s3 import S3
from rezq.utils.institution import get_institution_from_email
from rezq.validators import validate_industries


class UserManager(BaseUserManager):
    """
    https://github.com/django/django/blob/master/django/contrib/auth/models.py#L131

    Modified to make nothing mandatory.
    """
    use_in_migrations = True

    def _create_user(self, username, email, password, **extra_fields):
        """
        Create and save a user with the given username, email, and password.
        """
        email = self.normalize_email(email) if email else None
        username = self.model.normalize_username(
            username,
        ) if username else None
        user = self.model(username=username, email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(
        self, username=None, email=None, password=None, **extra_fields
    ):
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        extra_fields.setdefault('is_active', False)
        return self._create_user(username, email, password, **extra_fields)

    def create_superuser(
        self, username=None, email=None, password=None, **extra_fields
    ):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self._create_user(username, email, password, **extra_fields)


class User(AbstractUser):

    objects = UserManager()

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    # Some custom handle the user may want
    username = models.CharField(
        unique=True,
        db_index=True,
        max_length=64,
        null=True,
        blank=True,
        validators=[
            RegexValidator(
                r'^[0-9a-zA-Z]*$',
                'Only alphanumeric characters are allowed.',
            ),
        ],
        verbose_name='username',
        error_messages={'unique': 'A user with that username already exists.'},
        help_text=(
            '64 characters or fewer. '
            'Letters and digits only.'
        ),
    )

    email = models.EmailField(
        unique=True,
        db_index=True,
        null=True,
        blank=True,
        verbose_name='email address',
    )

    unverified_email = models.EmailField(
        unique=True,
        db_index=True,
        null=True,
        blank=True,
        verbose_name='unverified email address',
    )

    password = models.CharField(
        null=True,
        blank=True,
        max_length=128,
        verbose_name='password',
    )

    @property
    def has_password(self):
        return bool(self.password)

    waterloo_id = models.CharField(
        unique=True,
        db_index=True,
        max_length=32,
        null=True,
        blank=True,
        verbose_name='waterloo user id',
    )

    facebook_id = models.CharField(
        unique=True,
        db_index=True,
        max_length=24,
        null=True,
        blank=True,
        verbose_name='facebook user id',
    )

    google_id = models.CharField(
        unique=True,
        db_index=True,
        max_length=24,
        null=True,
        blank=True,
        verbose_name='google user id',
    )

    # Comma delimited list of rezq.server.constants.INDUSTRIES
    # User sets this. It is industries this person works in.
    industries = models.TextField(
        blank=True,
        default='',
        validators=[validate_industries],
    )

    email_subscribed = models.BooleanField(default=True)

    is_verified = models.BooleanField(default=False)
    is_premium = models.BooleanField(default=False)

    biography = models.TextField(
        blank=True,
        default='',
    )

    @property
    def institutions(self):
        """
        A set of email domains. E.g., set(['uwaterloo.ca'])
        """
        instits = set()

        if not self.is_active:
            # if your not active then
            # the email you signed up with isn't verified
            # or you didn't sign up with 3rd party auth
            return instits

        email_instit = get_institution_from_email(self.email)

        if email_instit:
            if email_instit == 'edu.uwaterloo.ca':
                email_instit = 'uwaterloo.ca'

            instits.add(email_instit)

        if self.waterloo_id:
            instits.add('uwaterloo.ca')

        return instits

    def can_access_pool(self, pool):
        # __str__ of pool returns its id
        return str(pool) in self.institutions

    @property
    def avatar_download_url(self):
        return S3.get_download_url(
            settings.S3_AVATAR_BUCKET,
            f'{self.id}.png',
        )

    @property
    def avatar_upload_info(self):
        return S3.get_upload_dict(
            settings.S3_AVATAR_BUCKET,
            f'{self.id}.png',
        )

    def __repr__(self):
        return '<{}: {}>'.format(self.__class__.__name__, self)

    def __str__(self):
        return (
            f"{self.first_name or ''} {self.last_name or ''}".strip() or
            self.username or
            self.waterloo_id or
            str(self.email)
        )

    def delete(self):
        S3.delete(settings.S3_AVATAR_BUCKET, f'{self.id}.png')
        super().delete()

    def _save(self, *args, **kwargs):
        if not self.email:
            self.email = None
        else:
            self.email = self.email.lower()

        if not self.unverified_email:
            self.unverified_email = None
        else:
            self.unverified_email = self.unverified_email.lower()

        if not self.username:
            self.username = None
        else:
            self.username = self.username.lower()

        if not self.password:
            self.password = None

        if not self.waterloo_id:
            self.waterloo_id = None

        if not self.facebook_id:
            self.facebook_id = None

        if not self.google_id:
            self.google_id = None

        super().save(*args, **kwargs)

    if settings.DEBUG:
        def save(self, *args, **kwargs):
            from rezq.models.dev import MockS3File
            try:
                MockS3File.objects.get(id=f'{self.id}.png')
            except MockS3File.DoesNotExist:
                MockS3File.objects.create(id=f'{self.id}.png')

            self._save(*args, **kwargs)
    else:
        save = _save

    def clean(self):
        if self.get_username():
            setattr(
                self,
                self.USERNAME_FIELD,
                self.normalize_username(self.get_username()),
            )
