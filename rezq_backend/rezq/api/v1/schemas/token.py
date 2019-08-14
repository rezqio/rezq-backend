import logging

import graphene
from django.db import transaction
from django.db.models import Q
from rezq.lib import cas
from rezq.lib import facebook
from rezq.lib import google
from rezq.models import User
from rezq.utils import auth


logger = logging.getLogger(__name__)


class CreateToken(graphene.Mutation):

    class Arguments:
        email = graphene.String(required=True)
        password = graphene.String(required=True)

    token = graphene.String()
    expires = graphene.types.datetime.DateTime()
    profile_created = graphene.Boolean()
    unverified_email = graphene.String()
    errors = graphene.types.json.JSONString()

    def mutate(self, info, **kwargs):
        # email or username
        email = kwargs['email'].lower()

        user = User.objects.filter(
            Q(email=email) | Q(username=email),
        )

        if user.count() == 0:
            return CreateToken(
                errors={
                    'login': 'The information you provided is incorrect.',
                },
            )
        elif user.count() > 1:
            # I think this case is impossible due to Django db constraints
            # but maybe someone will modify the database row directly?
            logger.error(
                'User email / username collision (%s): %s',
                email,
                [(u.id, u.email, u.username) for u in user],
            )
            return CreateToken(
                errors={
                    'login': (
                        'Sorry, something went wrong. '
                        'If the problem persists, '
                        'please contact support@rezq.io'
                    ),
                },
            )

        user = user[0]

        if not user.check_password(kwargs['password']):
            return CreateToken(
                errors={
                    'login': 'The information you provided is incorrect.',
                },
            )

        token, expires = auth.create_token(user.id)

        return CreateToken(
            token=token,
            expires=expires,
            profile_created=False,
            unverified_email=user.unverified_email,
        )


class CreateTokenWithWaterloo(graphene.Mutation):

    class Arguments:
        ticket = graphene.String(required=True)

    token = graphene.String()
    expires = graphene.types.datetime.DateTime()
    profile_created = graphene.Boolean()
    unverified_email = graphene.String()
    errors = graphene.types.json.JSONString()

    def mutate(self, info, **kwargs):
        waterloo_id = cas.validate_ticket(kwargs['ticket'], 'login')

        if not waterloo_id:
            return CreateTokenWithWaterloo(
                errors={'login': 'Failed to authenticate with Waterloo CAS.'},
            )

        user, profile_created = User.objects.get_or_create(
            waterloo_id=waterloo_id,
        )

        token, expires = auth.create_token(user.id)

        return CreateTokenWithWaterloo(
            token=token,
            expires=expires,
            profile_created=profile_created,
            unverified_email=user.unverified_email,
        )


class CreateTokenWithFacebook(graphene.Mutation):

    class Arguments:
        token = graphene.String(required=True)

    token = graphene.String()
    expires = graphene.types.datetime.DateTime()
    profile_created = graphene.Boolean()
    unverified_email = graphene.String()
    errors = graphene.types.json.JSONString()

    def mutate(self, info, **kwargs):
        facebook_id = facebook.validate_token(kwargs['token'])

        if not facebook_id:
            return CreateTokenWithFacebook(
                errors={'login': 'Failed to authenticate with Facebook.'},
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

        return CreateTokenWithFacebook(
            token=token,
            expires=expires,
            profile_created=profile_created,
            unverified_email=user.unverified_email,
        )


class CreateTokenWithGoogle(graphene.Mutation):

    class Arguments:
        token = graphene.String(required=True)

    token = graphene.String()
    expires = graphene.types.datetime.DateTime()
    profile_created = graphene.Boolean()
    unverified_email = graphene.String()
    errors = graphene.types.json.JSONString()

    def mutate(self, info, **kwargs):
        google_id = google.validate_token(kwargs['token'])

        if not google_id:
            return CreateTokenWithGoogle(
                errors={'login': 'Failed to authenticate with Google.'},
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

        return CreateTokenWithGoogle(
            token=token,
            expires=expires,
            profile_created=profile_created,
            unverified_email=user.unverified_email,
        )


class TokenMutationPublic:

    create_token = CreateToken.Field()
    create_token_with_waterloo = CreateTokenWithWaterloo.Field()
    create_token_with_facebook = CreateTokenWithFacebook.Field()
    create_token_with_google = CreateTokenWithGoogle.Field()


class RenewToken(graphene.Mutation):

    token = graphene.String()
    expires = graphene.types.datetime.DateTime()
    errors = graphene.types.json.JSONString()

    def mutate(self, info, **kwargs):
        token, expires = auth.create_token(info.context.user.id)

        return RenewToken(
            token=token,
            expires=expires,
        )


class TokenMutationPrivate:

    renew_token = RenewToken.Field()
