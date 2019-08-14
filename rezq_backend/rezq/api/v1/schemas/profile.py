import logging

import graphene
from django.conf import settings
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.utils import IntegrityError
from graphene_django.types import DjangoObjectType
from rezq.lib import cas
from rezq.lib import facebook
from rezq.lib import google
from rezq.lib.s3 import S3
from rezq.models import CritiquerRequest
from rezq.models import User
from rezq.utils import auth
from rezq.utils.mailer import send_email_verification_mail
from rezq.utils.patch_model import patch_model
from server.constants import EMAIL_REGEX
from server.constants import USERNAME_REGEX


logger = logging.getLogger(__name__)


def merge_profiles(this, that):
    """Merges this profile with that profile.
    Uses information from this profile if possible.
    Deletes that profile and returns this profile.
    """
    with transaction.atomic():
        # Some automatic account info stuff
        this.date_joined = min(this.date_joined, that.date_joined)
        # TODO: Set last_login properly
        # this.last_login = max(this.last_login, that.last_login)

        # Profile info
        this.first_name = this.first_name or that.first_name
        this.last_name = this.last_name or that.last_name
        this.industries = this.industries or that.industries

        # 3rd party auth
        this.waterloo_id = this.waterloo_id or that.waterloo_id
        this.facebook_id = this.facebook_id or that.facebook_id
        this.google_id = this.google_id or that.google_id

        # Email
        # Prefer this, but if this isn't verified and that is, use that
        if not this.is_verified and that.is_verified:
            this.is_verified = True
            this.email = that.email

        this.username = this.username or that.username

        # TODO: How to handle this?
        this.is_premium = this.is_premium or that.is_premium

        # Resumes
        for resume in that.resume_set.all():
            resume.uploader = this
            resume.save()

        # Request to critique
        try:
            # Check if this profile has a critiquer request
            this.critiquerrequest
        except CritiquerRequest.DoesNotExist:
            # This profile doesn't have a critiquer request
            try:
                that.critiquerrequest.critiquer = this
                that.critiquerrequest.save()
            except CritiquerRequest.DoesNotExist:
                pass

        # Critiques
        for critique in that.matchedcritique_set.all():
            critique.critiquer = this
            critique.save()

        for critique in that.linkedcritique_set.all():
            critique.critiquer = this
            critique.save()

        for critique in that.pooledcritique_set.all():
            critique.critiquer = this
            critique.save()

        # Comments
        for comment in that.matchedcritiquecomment_set.all():
            comment.user = this
            comment.save()

        for comment in that.linkedcritiquecomment_set.all():
            comment.user = this
            comment.save()

        for comment in that.pooledcritiquecomment_set.all():
            comment.user = this
            comment.save()

        # Upvotes
        # Need to prevent duplicate upvotes
        this_upvoted_critiques = {
            vote.critique.id
            for vote in this.pooledcritiquevote_set.all()
        }
        for vote in that.pooledcritiquevote_set.all():
            # If both accounts upvoted the same critique, then skip this
            # The extra one will be deleted later
            if vote.critique.id in this_upvoted_critiques:
                continue
            vote.voter = this
            vote.save()

        # Reports
        for report in that.pagereport_set.all():
            report.reporter = this
            report.save()

        # Finish the merge
        that.delete()
        this.full_clean()
        this.save()

    return this


def generate_email_verification(user_id, user_email):
    verification_token = auth.create_email_verification_token(
        user_id,
        user_email,
    )
    verification_link = (
        f'{settings.FRONTEND_URL}/verify-email'
        f'?token={verification_token}'
    )

    try:
        send_email_verification_mail(
            user_email, verification_link,
        )
    except Exception as e:
        logger.error(f'{type(e)}: {str(e)}')


class PasswordValidationException(Exception):

    def __init__(self, messages):
        self.messages = messages


class EmailUniquenessException(Exception):

    pass


class ProfileType(DjangoObjectType):

    class Meta:
        model = User
        only_fields = (
            'id', 'first_name', 'last_name', 'date_joined', 'username',
            'email', 'unverified_email', 'industries', 'waterloo_id',
            'google_id', 'facebook_id', 'matchedcritique_set',
            'pooledcritique_set', 'linkedcritique_set', 'email_subscribed',
            'is_verified', 'is_premium', 'biography',
        )

    has_password = graphene.Boolean()
    avatar_download_url = graphene.String()
    avatar_upload_info = graphene.types.json.JSONString()
    institutions = graphene.List(graphene.String)


class PublicProfileType(DjangoObjectType):

    class Meta:
        model = User
        only_fields = (
            'id', 'first_name', 'last_name', 'date_joined', 'username',
            'industries', 'is_verified', 'is_premium',
            'pooledcritique_set', 'biography',
        )

    avatar_download_url = graphene.String()


class ProfileQuery:

    profile = graphene.Field(ProfileType)

    def resolve_profile(self, info, **kwargs):
        return info.context.user


class ProfileQueryPublic:

    profile = graphene.Field(
        PublicProfileType,
        username=graphene.String(required=True),
    )

    def resolve_profile(self, info, **kwargs):
        try:
            return User.objects.get(username=kwargs['username'].lower())
        except User.DoesNotExist:
            return None


class CreateProfile(graphene.Mutation):

    class Arguments:
        email = graphene.String(required=True)
        password = graphene.String(required=True)
        first_name = graphene.String(default_value='')
        last_name = graphene.String(default_value='')

    profile = graphene.Field(ProfileType)
    profile_created = graphene.Boolean()
    token = graphene.String()
    expires = graphene.types.datetime.DateTime()
    errors = graphene.types.json.JSONString()

    def mutate(self, info, **kwargs):
        if not EMAIL_REGEX.match(kwargs['email']):
            return CreateProfile(
                errors={
                    'email': 'Invalid email address.',
                },
            )

        try:
            with transaction.atomic():
                try:
                    user = User.objects.create_user(
                        email=kwargs['email'],
                        password=kwargs['password'],
                        first_name=kwargs['first_name'],
                        last_name=kwargs['last_name'],
                        unverified_email=kwargs['email'],
                    )
                except IntegrityError as e:
                    if 'email' in str(e):
                        raise EmailUniquenessException()
                    raise

                try:
                    validate_password(kwargs['password'], user=user)
                except ValidationError as e:
                    raise PasswordValidationException(e.messages)

                generate_email_verification(user.id, user.unverified_email)

                token, expires = auth.create_token(user.id)

                return CreateProfile(
                    profile=user,
                    profile_created=True,
                    token=token,
                    expires=expires,
                )
        except EmailUniquenessException:
            return CreateProfile(
                errors={
                    'email': 'This email is already in use.',
                },
            )
        except PasswordValidationException as e:
            return CreateProfile(
                errors={
                    'password': e.messages,
                },
            )


class CreateProfileWithWaterloo(graphene.Mutation):

    class Arguments:
        ticket = graphene.String(required=True)

    profile = graphene.Field(ProfileType)
    profile_created = graphene.Boolean()
    token = graphene.String()
    expires = graphene.types.datetime.DateTime()
    errors = graphene.types.json.JSONString()

    def mutate(self, info, **kwargs):
        waterloo_id = cas.validate_ticket(kwargs['ticket'], 'signup')

        if not waterloo_id:
            return CreateProfileWithWaterloo(
                errors={
                    'ticket': 'Failed to authenticate with Waterloo CAS.',
                },
            )

        user, profile_created = User.objects.get_or_create(
            waterloo_id=waterloo_id,
        )

        token, expires = auth.create_token(user.id)

        return CreateProfileWithWaterloo(
            profile=user,
            profile_created=profile_created,
            token=token,
            expires=expires,
        )


class CreateProfileWithFacebook(graphene.Mutation):

    class Arguments:
        token = graphene.String(required=True)

    profile = graphene.Field(ProfileType)
    profile_created = graphene.Boolean()
    token = graphene.String()
    expires = graphene.types.datetime.DateTime()
    errors = graphene.types.json.JSONString()

    def mutate(self, info, **kwargs):
        facebook_id = facebook.validate_token(kwargs['token'])

        if not facebook_id:
            return CreateProfileWithFacebook(
                errors={
                    'token': 'Failed to authenticate with Facebook.',
                },
            )

        with transaction.atomic():
            user, profile_created = User.objects.get_or_create(
                facebook_id=facebook_id,
            )
            if profile_created:
                fb_profile = facebook.get_profile(kwargs['token'])
                user.first_name = fb_profile.get('first_name')
                user.last_name = fb_profile.get('last_name')
                user.save()

        token, expires = auth.create_token(user.id)

        return CreateProfileWithFacebook(
            profile=user,
            profile_created=profile_created,
            token=token,
            expires=expires,
        )


class CreateProfileWithGoogle(graphene.Mutation):

    class Arguments:
        token = graphene.String(required=True)

    profile = graphene.Field(ProfileType)
    profile_created = graphene.Boolean()
    token = graphene.String()
    expires = graphene.types.datetime.DateTime()
    errors = graphene.types.json.JSONString()

    def mutate(self, info, **kwargs):
        google_id = google.validate_token(kwargs['token'])

        if not google_id:
            return CreateProfileWithGoogle(
                errors={
                    'token': 'Failed to authenticate with Google.',
                },
            )

        with transaction.atomic():
            user, profile_created = User.objects.get_or_create(
                google_id=google_id,
            )
            if profile_created:
                g_profile = google.get_profile(kwargs['token'])
                user.first_name = g_profile.get('first_name')
                user.last_name = g_profile.get('last_name')
                user.save()

        token, expires = auth.create_token(user.id)

        return CreateProfileWithGoogle(
            profile=user,
            profile_created=profile_created,
            token=token,
            expires=expires,
        )


class VerifyEmail(graphene.Mutation):

    class Arguments:
        verification_token = graphene.String(required=True)

    token = graphene.String()
    expires = graphene.types.datetime.DateTime()
    errors = graphene.types.json.JSONString()

    def mutate(self, info, **kwargs):
        verification_token = kwargs['verification_token']

        is_valid, user_id, user_email = auth.validate_email_verification_token(
            verification_token,
        )

        if not is_valid:
            return VerifyEmail(
                errors={
                    'token': 'Invalid email verification token.',
                },
            )

        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return VerifyEmail(
                errors={
                    'token': 'Invalid email verification token.',
                },
            )

        if not user.unverified_email or user.unverified_email != user_email:
            return VerifyEmail(
                errors={
                    'token': 'Invalid email verification token.',
                },
            )

        try:
            user.is_active = True
            user.email = user.unverified_email
            user.unverified_email = None
            user.save()
        except Exception as e:
            logger.error(f'{type(e)}: {str(e)}')
            return VerifyEmail(
                errors={
                    'token': 'Invalid email verification token.',
                },
            )

        token, expires = auth.create_token(user.id)

        return VerifyEmail(
            token=token,
            expires=expires,
        )


class UnsubscribeEmail(graphene.Mutation):

    class Arguments:
        unsubscribe_token = graphene.String(required=True)

    errors = graphene.types.json.JSONString()

    def mutate(self, info, **kwargs):
        unsubscribe_token = kwargs['unsubscribe_token']

        is_valid, user_id = auth.validate_email_unsubscribe_token(
            unsubscribe_token,
        )

        if not is_valid:
            return UnsubscribeEmail(
                errors={
                    'token': 'Invalid email unsubscribe token.',
                },
            )

        try:
            user = User.objects.get(id=user_id)

            user.email_subscribed = False
            user.save()
        except User.DoesNotExist:
            return UnsubscribeEmail(
                errors={
                    'token': 'Invalid email unsubscribe token.',
                },
            )

        return UnsubscribeEmail()


class ProfileMutationPublic:

    create_profile = CreateProfile.Field()
    create_profile_with_waterloo = CreateProfileWithWaterloo.Field()
    create_profile_with_facebook = CreateProfileWithFacebook.Field()
    create_profile_with_google = CreateProfileWithGoogle.Field()
    verify_email = VerifyEmail.Field()
    unsubscribe_email = UnsubscribeEmail.Field()


class EditProfile(graphene.Mutation):

    class Arguments:
        first_name = graphene.String(required=False)
        last_name = graphene.String(required=False)
        username = graphene.String(required=False)
        email = graphene.String(required=False)
        current_password = graphene.String(required=False)
        new_password = graphene.String(required=False)
        biography = graphene.String(required=False)
        industries = graphene.String(
            required=False,
            description='Comma delimited string of industries',
        )
        email_subscribed = graphene.Boolean(
            required=False,
            description='Set `true` indicate subscription to email notifs',
        )

    profile = graphene.Field(ProfileType)
    errors = graphene.types.json.JSONString()

    def mutate(self, info, **kwargs):
        # TODO: this mutation is in major need of refactoring
        user = info.context.user

        if 'email' in kwargs and kwargs['email'].lower() != user.email:
            if not EMAIL_REGEX.match(kwargs['email']):
                return EditProfile(
                    errors={
                        'email': 'Invalid email address.',
                    },
                )
            if user.has_password and 'current_password' not in kwargs:
                return EditProfile(
                    errors={
                        'current_password': (
                            'Your current password is required for ' +
                            'changing your email.'
                        ),
                    },
                )
            if not user.has_password and 'new_password' not in kwargs:
                return EditProfile(
                    errors={
                        'new_password': (
                            'A password must be set when adding an email.'
                        ),
                    },
                )

        if (
            'username' in kwargs and
            kwargs['username'].lower() != user.username
        ):
            if not USERNAME_REGEX.match(kwargs['username']):
                return EditProfile(
                    errors={
                        'username': (
                            'Your username must only '
                            'contain letters and digits.'
                        ),
                    },
                )
            if user.has_password and 'current_password' not in kwargs:
                return EditProfile(
                    errors={
                        'current_password': (
                            'Your current password is required for ' +
                            'changing your username.'
                        ),
                    },
                )
            if not user.has_password and 'new_password' not in kwargs:
                return EditProfile(
                    errors={
                        'new_password': (
                            'A password must be set when adding a username.'
                        ),
                    },
                )

        if 'new_password' in kwargs:
            if user.has_password and 'current_password' not in kwargs:
                return EditProfile(
                    errors={
                        'current_password': (
                            'Your current password is required for ' +
                            'changing your password.'
                        ),
                    },
                )
            if (
                not user.email and
                'email' not in kwargs and
                not user.username and
                'username' not in kwargs
            ):
                return EditProfile(
                    errors={
                        'new_password': (
                            'An email or username must be entered when ' +
                            'setting your password for the first time.'
                        ),
                    },
                )

        if (
            'current_password' in kwargs and
            not user.check_password(kwargs['current_password'])
        ):
            return EditProfile(
                errors={
                    'current_password': 'Your password was incorrect.',
                },
            )

        new_password = kwargs.pop('new_password', None)
        new_email = kwargs.pop('email').lower() if (
            'email' in kwargs and
            kwargs['email'].lower() != user.email
        ) else None

        try:
            with transaction.atomic():
                patch_model(user, kwargs)
                if new_password:
                    try:
                        validate_password(new_password, user=user)
                    except ValidationError as e:
                        return EditProfile(
                            errors={
                                'new_password': e.messages,
                            },
                        )
                    user.set_password(new_password)
                if new_email:
                    try:
                        User.objects.get(email=new_email)
                        return EditProfile(
                            errors={
                                'new_email': 'Email is in use.',
                            },
                        )
                    except User.DoesNotExist:
                        pass

                    generate_email_verification(user.id, new_email)

                    user.unverified_email = new_email
                if new_password or new_email:
                    user.save()
        except ValidationError as e:
            return EditProfile(errors=e.message_dict)

        return EditProfile(profile=user)


class ResendVerificationEmail(graphene.Mutation):

    errors = graphene.types.json.JSONString()

    def mutate(self, info, **kwargs):
        user = info.context.user

        if not user.unverified_email:
            return ResendVerificationEmail(
                errors={
                    'email': 'No unverified email on account.',
                },
            )

        generate_email_verification(user.id, user.unverified_email)

        return ResendVerificationEmail()


class CancelEmailChange(graphene.Mutation):

    errors = graphene.types.json.JSONString()

    def mutate(self, info, **kwargs):
        user = info.context.user

        if not user.unverified_email:
            return CancelEmailChange(
                errors={
                    'email': 'No unverified email on account.',
                },
            )

        if user.unverified_email == user.email:
            return CancelEmailChange(
                errors={
                    'email': (
                        'Cannot cancel verification for '
                        'the email you signed up with.'
                    ),
                },
            )

        user.unverified_email = None
        user.save()

        return CancelEmailChange()


class LinkProfileWithWaterloo(graphene.Mutation):

    class Arguments:
        ticket = graphene.String(required=True)
        link_existing_account = graphene.Boolean(
            required=False,
            default_value=False,
        )

    profile = graphene.Field(ProfileType)
    errors = graphene.types.json.JSONString()

    def mutate(self, info, **kwargs):
        user = info.context.user
        waterloo_id = cas.validate_ticket(kwargs['ticket'], 'settings')

        if not waterloo_id:
            return LinkProfileWithWaterloo(
                errors={
                    'ticket': 'Failed to authenticate with Waterloo CAS.',
                },
            )

        if user.waterloo_id == waterloo_id:
            return LinkProfileWithWaterloo(profile=user)

        try:
            other_user = User.objects.get(waterloo_id=waterloo_id)

            if kwargs['link_existing_account']:
                return LinkProfileWithWaterloo(
                    profile=merge_profiles(user, other_user),
                )
            else:
                return LinkProfileWithWaterloo(
                    errors={
                        'waterloo_id': (
                            'This Waterloo account is already in use.'
                        ),
                    },
                )
        except User.DoesNotExist:
            pass

        user.waterloo_id = waterloo_id
        user.full_clean()
        user.save()

        return LinkProfileWithWaterloo(profile=user)


class LinkProfileWithFacebook(graphene.Mutation):

    class Arguments:
        token = graphene.String(required=True)
        link_existing_account = graphene.Boolean(
            required=False,
            default_value=False,
        )

    profile = graphene.Field(ProfileType)
    errors = graphene.types.json.JSONString()

    def mutate(self, info, **kwargs):
        user = info.context.user
        facebook_id = facebook.validate_token(kwargs['token'])

        if not facebook_id:
            return LinkProfileWithFacebook(
                errors={
                    'token': 'Failed to authenticate with Facebook.',
                },
            )

        if user.facebook_id == facebook_id:
            return LinkProfileWithFacebook(profile=user)

        try:
            other_user = User.objects.get(facebook_id=facebook_id)

            if kwargs['link_existing_account']:
                return LinkProfileWithFacebook(
                    profile=merge_profiles(user, other_user),
                )
            else:
                return LinkProfileWithFacebook(
                    errors={
                        'facebook_id': (
                            'This Facebook account is already in use.'
                        ),
                    },
                )
        except User.DoesNotExist:
            pass

        user.facebook_id = facebook_id
        user.full_clean()
        user.save()

        return LinkProfileWithFacebook(profile=user)


class LinkProfileWithGoogle(graphene.Mutation):

    class Arguments:
        token = graphene.String(required=True)
        link_existing_account = graphene.Boolean(
            required=False,
            default_value=False,
        )

    profile = graphene.Field(ProfileType)
    errors = graphene.types.json.JSONString()

    def mutate(self, info, **kwargs):
        user = info.context.user
        google_id = google.validate_token(kwargs['token'])

        if not google_id:
            return LinkProfileWithGoogle(
                errors={
                    'token': 'Failed to authenticate with Google.',
                },
            )

        if user.google_id == google_id:
            return LinkProfileWithGoogle(profile=user)

        try:
            other_user = User.objects.get(google_id=google_id)

            if kwargs['link_existing_account']:
                return LinkProfileWithGoogle(
                    profile=merge_profiles(user, other_user),
                )
            else:
                return LinkProfileWithGoogle(
                    errors={
                        'google_id': 'This Google account is already in use.',
                    },
                )
        except User.DoesNotExist:
            pass

        user.google_id = google_id
        user.full_clean()
        user.save()

        return LinkProfileWithGoogle(profile=user)


class DeleteProfile(graphene.Mutation):

    errors = graphene.types.json.JSONString()

    def mutate(self, info, **kwargs):
        info.context.user.delete()
        return DeleteProfile()


class UnlinkProfileWithWaterloo(graphene.Mutation):

    profile = graphene.Field(ProfileType)
    errors = graphene.types.json.JSONString()

    def mutate(self, info, **kwargs):
        user = info.context.user

        if not (
            (user.email and user.has_password) or
            user.facebook_id or
            user.google_id
        ):
            return UnlinkProfileWithWaterloo(
                errors={
                    'waterloo_id': 'You must set your email/password first.',
                },
            )

        user.waterloo_id = None
        user.save()

        return UnlinkProfileWithWaterloo(profile=user)


class UnlinkProfileWithFacebook(graphene.Mutation):

    profile = graphene.Field(ProfileType)
    errors = graphene.types.json.JSONString()

    def mutate(self, info, **kwargs):
        user = info.context.user

        if not (
            (user.email and user.has_password) or
            user.waterloo_id or
            user.google_id
        ):
            return UnlinkProfileWithFacebook(
                errors={
                    'facebook_id': 'You must set your email/password first.',
                },
            )

        user.facebook_id = None
        user.save()

        return UnlinkProfileWithFacebook(profile=user)


class UnlinkProfileWithGoogle(graphene.Mutation):

    profile = graphene.Field(ProfileType)
    errors = graphene.types.json.JSONString()

    def mutate(self, info, **kwargs):
        user = info.context.user

        if not (
            (user.email and user.has_password) or
            user.waterloo_id or
            user.facebook_id
        ):
            return UnlinkProfileWithGoogle(
                errors={
                    'google_id': 'You must set your email/password first.',
                },
            )

        user.google_id = None
        user.save()

        return UnlinkProfileWithGoogle(profile=user)


class RemoveAvatar(graphene.Mutation):

    errors = graphene.types.json.JSONString()

    def mutate(self, info, **kwargs):
        user = info.context.user

        S3.delete(settings.S3_AVATAR_BUCKET, str(user.id))

        return RemoveAvatar()


class ProfileMutationPrivate:

    edit_profile = EditProfile.Field()
    resend_verification_email = ResendVerificationEmail.Field()
    cancel_email_change = CancelEmailChange.Field()
    link_profile_with_waterloo = LinkProfileWithWaterloo.Field()
    link_profile_with_facebook = LinkProfileWithFacebook.Field()
    link_profile_with_google = LinkProfileWithGoogle.Field()
    unlink_profile_with_waterloo = UnlinkProfileWithWaterloo.Field()
    unlink_profile_with_facebook = UnlinkProfileWithFacebook.Field()
    unlink_profile_with_google = UnlinkProfileWithGoogle.Field()
    delete_profile = DeleteProfile.Field()
    remove_avatar = RemoveAvatar.Field()
