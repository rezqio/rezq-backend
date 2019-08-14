import logging

import graphene
from django.conf import settings
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from rezq.models import User
from rezq.utils import auth
from rezq.utils.mailer import send_password_reset_mail

logger = logging.getLogger(__name__)


class CreatePasswordResetToken(graphene.Mutation):

    class Arguments:
        email = graphene.String(required=True)

    errors = graphene.types.json.JSONString()

    def mutate(self, info, **kwargs):

        email = kwargs['email'].lower()

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return CreatePasswordResetToken()

        reset_token = auth.create_password_reset_token(user.email)
        reset_link = (
            f'{settings.FRONTEND_URL}/reset-password'
            f'?token={reset_token}'
        )

        try:
            send_password_reset_mail(email, reset_link)
        except Exception as e:
            logger.error(f'{type(e)}: {str(e)}')

        return CreatePasswordResetToken()


class ResetPassword(graphene.Mutation):

    class Arguments:
        token = graphene.String(required=True)
        new_password = graphene.String(required=True)

    errors = graphene.types.json.JSONString()

    def mutate(self, info, **kwargs):
        token = kwargs['token']
        new_password = kwargs['new_password']

        is_valid, email = auth.validate_password_reset_token(token)

        if not is_valid:
            return ResetPassword(
                errors={
                    'token': 'Invalid password reset token.',
                },
            )

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return ResetPassword(
                errors={
                    'token': 'Invalid password reset token.',
                },
            )

        try:
            try:
                validate_password(new_password, user=user)
            except ValidationError as e:
                return ResetPassword(
                    errors={
                        'password': e.messages,
                    },
                )
            user.set_password(new_password)
            user.save()
        except ValidationError as e:
            return ResetPassword(errors=e.message_dict)

        return ResetPassword()


class PasswordResetMutation:

    create_password_reset_token = CreatePasswordResetToken.Field()
    reset_password = ResetPassword.Field()
