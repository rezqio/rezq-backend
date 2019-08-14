import graphene
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q
from graphene_django.types import DjangoObjectType
from rezq.models import CritiquerRequest
from rezq.models import MatchedCritique
from rezq.models import MatchedCritiqueComment
from rezq.models import Resume
from rezq.utils.patch_model import patch_model
from rezq.validators import IndustryValidationError
from rezq.validators import validate_industries


def _get_currently_critiquing(critiquer):
    """
    :param critiquer: the critiquer
    :type critiquer: rezq.models.user.User

    :return: a namedtuple
    :rtype: rezq.models.critique.Critique or None
    """
    try:
        return MatchedCritique.objects.get(
            critiquer=critiquer,
            submitted=False,
        )
    except MatchedCritique.DoesNotExist:
        return None


class CritiqueType(DjangoObjectType):

    class Meta:
        model = MatchedCritique
        only_fields = (
            'id', 'resume', 'summary',
            'annotations', 'submitted', 'submitted_on',
        )


class PublicCritiqueType(DjangoObjectType):

    class Meta:
        model = MatchedCritique
        only_fields = (
            'id', 'resume', 'summary',
            'annotations', 'submitted', 'submitted_on',
        )


class CritiquerRequestType(DjangoObjectType):

    class Meta:
        model = CritiquerRequest
        only_fields = ()


class PublicCritiquerRequestType(DjangoObjectType):

    class Meta:
        model = CritiquerRequest
        only_fields = ()


class MatchedCritiqueCommentType(DjangoObjectType):

    class Meta:
        model = MatchedCritiqueComment
        only_fields = (
            'id', 'critique', 'user', 'comment',
        )


class PublicMatchedCritiqueCommentType(DjangoObjectType):

    class Meta:
        model = MatchedCritiqueComment
        only_fields = (
            'id', 'critique',
        )


class CritiqueQuery:

    critiques = graphene.List(
        CritiqueType,
        is_critiquee=graphene.Boolean(
            default_value=False,
            description='Critiques you requested',
        ),
        is_critiquer=graphene.Boolean(
            default_value=False,
            description='Critiques you are the critiquer of',
        ),
    )

    critique = graphene.Field(
        CritiqueType,
        id=graphene.String(required=True),
    )

    currently_critiquing = graphene.Field(
        CritiqueType,
    )

    is_critiquer_request_queued = graphene.Field(
        graphene.Boolean,
    )

    def resolve_critiques(self, info, **kwargs):
        if kwargs['is_critiquee'] == kwargs['is_critiquer']:
            return MatchedCritique.objects.filter(
                Q(
                    critiquer=info.context.user,
                ) | Q(
                    resume__uploader=info.context.user,
                ),
            )
        elif kwargs['is_critiquee']:
            return MatchedCritique.objects.filter(
                resume__uploader=info.context.user,
            )
        else:
            return MatchedCritique.objects.filter(
                critiquer=info.context.user,
            )

    def resolve_critique(self, info, **kwargs):
        try:
            critique = MatchedCritique.objects.get(id=kwargs['id'])
        except MatchedCritique.DoesNotExist:
            return None

        if not (
            critique.critiquer == info.context.user or (
                critique.submitted and
                critique.resume.uploader == info.context.user
            )
        ):
            return None

        return critique

    def resolve_currently_critiquing(self, info, **kwargs):
        return _get_currently_critiquing(info.context.user)

    def resolve_is_critiquer_request_queued(self, info, **kwargs):
        try:
            CritiquerRequest.objects.get(
                critiquer=info.context.user,
            )
        except CritiquerRequest.DoesNotExist:
            return False

        return True


class RequestCritique(graphene.Mutation):

    class Arguments:
        resume_id = graphene.String(required=True)
        notes_for_critiquer = graphene.String(required=False)

    critique = graphene.Field(CritiqueType)
    errors = graphene.types.json.JSONString()

    def mutate(self, info, **kwargs):
        if not info.context.user.is_premium:
            return RequestCritique(
                errors={
                    'is_premium': (
                        'Only premium users can use '
                        'the matching functionality.'
                    ),
                },
            )

        try:
            resume = Resume.objects.get(
                id=kwargs['resume_id'],
                uploader=info.context.user,
            )
        except Resume.DoesNotExist:
            return RequestCritique(
                errors={
                    'resume_id': 'This resume does not exist.',
                },
            )

        if resume.matchedcritique_set.filter(submitted=False).exists():
            return RequestCritique(
                errors={
                    'resume_id': 'A critique already queued or in progress.',
                },
            )

        with transaction.atomic():
            # We set the notes_for_critiquer to prevent two round trips
            resume.notes_for_critiquer = (
                resume.notes_for_critiquer or kwargs['notes_for_critiquer']
            )

            resume.save()

            critique = MatchedCritique.objects.create(
                resume=resume,
            )

        return RequestCritique(critique=critique)


class DeleteCritiqueRequest(graphene.Mutation):

    class Arguments:
        id = graphene.String(required=True)

    errors = graphene.types.json.JSONString()

    def mutate(self, info, **kwargs):
        try:
            critique = MatchedCritique.objects.get(id=kwargs['id'])
        except MatchedCritique.DoesNotExist:
            return DeleteCritiqueRequest(
                errors={
                    'id': 'This critique does not exist.',
                },
            )

        if critique.resume.uploader != info.context.user:
            return DeleteCritiqueRequest(
                errors={
                    'id': 'This critique does not exist.',
                },
            )

        if critique.matched_on is not None:
            return DeleteCritiqueRequest(
                errors={
                    'matched_on': (
                        'You cannot delete an already matched critique.'
                    ),
                },
            )

        critique.delete()

        return DeleteCritiqueRequest()


class RequestToCritique(graphene.Mutation):

    class Arguments:
        industries = graphene.String(
            required=False,
            description='Comma delimited string of industries',
        )

    critiquer_request = graphene.Field(CritiquerRequestType)
    errors = graphene.types.json.JSONString()

    def mutate(self, info, **kwargs):
        user = info.context.user

        if not user.is_verified:
            return RequestCritique(
                errors={
                    'is_verified': (
                        'Only verified users can request '
                        'to critique through matching.'
                    ),
                },
            )

        if not user.is_active:
            return RequestToCritique(
                errors={
                    'user': 'Email requires verification.',
                },
            )

        if _get_currently_critiquing(user):
            return RequestToCritique(
                errors={
                    'user': 'You are already critiquing a resume.',
                },
            )

        try:
            CritiquerRequest.objects.get(critiquer=user)
            return RequestToCritique(
                errors={
                    'user': 'You are already in queue to critique a resume.',
                },
            )
        except CritiquerRequest.DoesNotExist:
            pass

        if kwargs.get('industries'):
            try:
                validate_industries(kwargs['industries'])
            except IndustryValidationError as e:
                return RequestCritique(
                    errors={
                        'industries': e.message,
                    },
                )
            industries = kwargs['industries']
        else:
            industries = user.industries

        critiquer_request = CritiquerRequest.objects.create(
            critiquer=user,
            industries=industries,
        )

        return RequestToCritique(critiquer_request=critiquer_request)


class CancelRequestToCritique(graphene.Mutation):

    errors = graphene.types.json.JSONString()

    def mutate(self, info, **kwargs):
        user = info.context.user

        try:
            CritiquerRequest.objects.get(critiquer=user).delete()
            return RequestToCritique()
        except CritiquerRequest.DoesNotExist:
            return CancelRequestToCritique(
                errors={
                    'user': 'You are not in queue to critique a resume.',
                },
            )


class SaveCritique(graphene.Mutation):

    class Arguments:
        id = graphene.String(required=True)
        submit = graphene.Boolean(
            default_value=False,
            description='Set `true` indicate submission',
        )
        summary = graphene.String(required=False)
        annotations = graphene.String(
            required=False,
            description='Serialized of PDF annotations',
        )

    critique = graphene.Field(CritiqueType)
    errors = graphene.types.json.JSONString()

    def mutate(self, info, **kwargs):
        try:
            critique = MatchedCritique.objects.get(id=kwargs['id'])
        except MatchedCritique.DoesNotExist:
            return SaveCritique(
                errors={
                    'id': 'This critique does not exist.',
                },
            )

        if critique.critiquer != info.context.user:
            return SaveCritique(
                errors={
                    'user': 'You are not the critiquer.',
                },
            )

        if critique.submitted:
            return SaveCritique(
                errors={
                    'submitted': (
                        'You cannot resubmit an already submitted critique.'
                    ),
                },
            )

        if kwargs.get('submit'):
            if not (critique.summary or kwargs.get('summary')):
                return SaveCritique(
                    errors={
                        'summary': 'You cannot submit without any comments.',
                    },
                )
            kwargs['submitted'] = True

        kwargs.pop('id', None)
        kwargs.pop('submit', None)

        try:
            patch_model(critique, kwargs)
        except ValidationError as e:
            return SaveCritique(errors=e.message_dict)

        return SaveCritique(critique=critique)


class CommentMatchedCritique(graphene.Mutation):

    class Arguments:
        critique_id = graphene.String(required=True)
        comment = graphene.String(required=True)

    comment = graphene.Field(MatchedCritiqueCommentType)
    errors = graphene.types.json.JSONString()

    def mutate(self, info, **kwargs):
        try:
            critique = MatchedCritique.objects.get(id=kwargs['critique_id'])
        except MatchedCritique.DoesNotExist:
            return CommentMatchedCritique(
                errors={
                    'critique_id': 'This critique does not exist.',
                },
            )

        if not (
            critique.critiquer == info.context.user or
            critique.resume.uploader == info.context.user
        ):
            return CommentMatchedCritique(
                errors={
                    'critique_id': 'This critique does not exist.',
                },
            )

        if not critique.submitted:
            return CommentMatchedCritique(
                errors={
                    'critique_id': (
                        'Cannot comment on an unsubmitted critique.'
                    ),
                },
            )

        comment = MatchedCritiqueComment.objects.create(
            critique=critique,
            user=info.context.user,
            comment=kwargs['comment'],
        )

        return CommentMatchedCritique(comment=comment)


class CritiqueMutation:

    request_critique = RequestCritique.Field()
    delete_critique_request = DeleteCritiqueRequest.Field()
    request_to_critique = RequestToCritique.Field()
    cancel_request_to_critique = CancelRequestToCritique.Field()
    save_critique = SaveCritique.Field()
    comment_critique = CommentMatchedCritique.Field()
