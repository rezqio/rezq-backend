import logging

import graphene
from django.core.exceptions import ValidationError
from graphene_django.types import DjangoObjectType
from rezq.models import PooledCritique
from rezq.models import PooledCritiqueComment
from rezq.models import PooledCritiqueVote
from rezq.models import Resume
from rezq.utils.patch_model import patch_model
from rezq.utils.request import get_client_info_str
from server.constants import DOMAIN_REGEX
from server.constants import PUBLIC


logger = logging.getLogger(__name__)


class PooledCritiqueType(DjangoObjectType):

    class Meta:
        model = PooledCritique
        only_fields = (
            'id', 'resume', 'summary', 'critiquer',
            'annotations', 'submitted', 'submitted_on',
            'pooledcritiquecomment_set',
        )

    upvotes = graphene.Int()
    user_upvoted = graphene.Boolean()


class PublicPooledCritiqueType(DjangoObjectType):

    class Meta:
        model = PooledCritique
        only_fields = (
            'id', 'resume', 'summary', 'critiquer',
            'annotations', 'submitted', 'submitted_on',
            'pooledcritiquecomment_set',
        )

    upvotes = graphene.Int()
    user_upvoted = graphene.Boolean()


class PooledCritiqueCommentType(DjangoObjectType):

    class Meta:
        model = PooledCritiqueComment
        only_fields = (
            'id', 'critique', 'user', 'comment', 'created_on',
        )


class PublicPooledCritiqueCommentType(DjangoObjectType):

    class Meta:
        model = PooledCritiqueComment
        only_fields = (
            'id', 'critique', 'user', 'comment', 'created_on',
        )


class PooledCritiqueQuery:

    pooled_critique = graphene.Field(
        PooledCritiqueType,
        id=graphene.String(required=True),
        private_pool=graphene.String(required=False),
    )

    def resolve_pooled_critique(self, info, **kwargs):
        try:
            critique = PooledCritique.objects.get(id=kwargs['id'])
        except PooledCritique.DoesNotExist:
            return None

        user = info.context.user

        pools = user.institutions
        pools.add(PUBLIC)
        if kwargs.get('private_pool'):
            if DOMAIN_REGEX.match(kwargs['private_pool']):
                # This guy is trying to hack institution pools!
                return None
            pools.add(kwargs['private_pool'])

        if not (
            critique.critiquer == user or (
                critique.submitted and (
                    (
                        critique.resume.pool and
                        str(critique.resume.pool) in pools
                    ) or
                    critique.resume.uploader == user
                )
            )
        ):
            return None

        try:
            critique.user_upvoted = PooledCritiqueVote.objects.get(
                voter=user, critique=kwargs['id'],
            ).is_upvote
        except PooledCritiqueVote.DoesNotExist:
            pass

        logger.info(
            '%s accessed critique: %s',
            get_client_info_str(info.context),
            str(critique.id),
        )

        return critique


class CreatePooledCritique(graphene.Mutation):

    class Arguments:
        resume_id = graphene.String(required=True)
        private_pool = graphene.String(required=False)

    critique = graphene.Field(PooledCritiqueType)
    errors = graphene.types.json.JSONString()

    def mutate(self, info, **kwargs):
        if not info.context.user.is_active:
            return CreatePooledCritique(
                errors={
                    'user': 'Email requires verification.',
                },
            )

        user = info.context.user

        pools = user.institutions
        pools.add(PUBLIC)
        if kwargs.get('private_pool'):
            if DOMAIN_REGEX.match(kwargs['private_pool']):
                # This guy is trying to hack institution pools!
                return CreatePooledCritique(
                    errors={
                        'resume_id': 'This resume does not exist.',
                    },
                )
            pools.add(kwargs['private_pool'])

        try:
            resume = Resume.objects.get(
                id=kwargs['resume_id'], pool__in=pools,
            )
        except Resume.DoesNotExist:
            return CreatePooledCritique(
                errors={
                    'resume_id': 'This resume does not exist.',
                },
            )

        try:
            # User continues their previously unsubmitted critique
            critique = PooledCritique.objects.get(
                critiquer=user,
                resume=resume,
                submitted=False,
            )
        except PooledCritique.DoesNotExist:
            critique = PooledCritique.objects.create(
                critiquer=user,
                resume=resume,
            )

        logger.info(
            '%s created critique: %s',
            get_client_info_str(info.context),
            str(critique.id),
        )

        return CreatePooledCritique(critique=critique)


class SavePooledCritique(graphene.Mutation):

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

    critique = graphene.Field(PooledCritiqueType)
    errors = graphene.types.json.JSONString()

    def mutate(self, info, **kwargs):
        try:
            critique = PooledCritique.objects.get(
                id=kwargs['id'],
                critiquer=info.context.user,
            )
        except PooledCritique.DoesNotExist:
            return SavePooledCritique(
                errors={
                    'id': 'This critique does not exist.',
                },
            )

        if critique.submitted:
            return SavePooledCritique(
                errors={
                    'submitted': (
                        'You cannot resubmit an already submitted critique.'
                    ),
                },
            )

        if kwargs.get('submit'):
            if not (critique.summary or kwargs.get('summary')):
                return SavePooledCritique(
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
            return SavePooledCritique(errors=e.message_dict)

        return SavePooledCritique(critique=critique)


class VotePooledCritique(graphene.Mutation):

    class Arguments:
        id = graphene.String(required=True)
        is_upvote = graphene.Boolean(required=False)

    errors = graphene.types.json.JSONString()
    result = graphene.String()

    def mutate(self, info, **kwargs):
        if 'is_upvote' not in kwargs:
            try:
                PooledCritiqueVote.objects.get(
                    critique=kwargs['id'],
                    voter=info.context.user,
                ).delete()
            except PooledCritiqueVote.DoesNotExist:
                return VotePooledCritique(result='NO_VOTE')
            return VotePooledCritique(result='UNCASTED')

        try:
            critique = PooledCritique.objects.get(id=kwargs['id'])
        except PooledCritique.DoesNotExist:
            return VotePooledCritique(
                errors={
                    'id': 'This critique does not exist.',
                },
            )

        vote, _ = PooledCritiqueVote.objects.get_or_create(
            critique=critique,
            voter=info.context.user,
        )

        is_upvote = kwargs['is_upvote']

        vote.is_upvote = is_upvote
        vote.save()

        return VotePooledCritique(
            result='UPVOTED' if is_upvote else 'DOWNVOTED',
        )


class CommentPooledCritique(graphene.Mutation):

    class Arguments:
        critique_id = graphene.String(required=True)
        comment = graphene.String(required=True)
        private_pool = graphene.String(required=False)

    comment = graphene.Field(PooledCritiqueCommentType)
    errors = graphene.types.json.JSONString()

    def mutate(self, info, **kwargs):
        try:
            critique = PooledCritique.objects.get(id=kwargs['critique_id'])
        except PooledCritique.DoesNotExist:
            return CommentPooledCritique(
                errors={
                    'critique_id': 'This critique does not exist.',
                },
            )

        user = info.context.user

        pools = user.institutions
        pools.add(PUBLIC)
        if kwargs.get('private_pool'):
            if DOMAIN_REGEX.match(kwargs['private_pool']):
                # This guy is trying to hack institution pools!
                return CommentPooledCritique(
                    errors={
                        'critique_id': 'This critique does not exist.',
                    },
                )
            pools.add(kwargs['private_pool'])

        if not (
            critique.critiquer == user or
            (
                critique.resume.pool and
                str(critique.resume.pool) in pools
            ) or
            critique.resume.uploader == user
        ):
            return CommentPooledCritique(
                errors={
                    'critique_id': 'This critique does not exist.',
                },
            )

        if not critique.submitted:
            return CommentPooledCritique(
                errors={
                    'critique_id': (
                        'Cannot comment on an unsubmitted critique.'
                    ),
                },
            )

        comment = PooledCritiqueComment.objects.create(
            critique=critique,
            user=user,
            comment=kwargs['comment'],
        )

        return CommentPooledCritique(comment=comment)


class PooledCritiqueMutation:

    create_pooled_critique = CreatePooledCritique.Field()
    save_pooled_critique = SavePooledCritique.Field()
    vote_pooled_critique = VotePooledCritique.Field()
    comment_pooled_critique = CommentPooledCritique.Field()
