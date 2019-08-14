import graphene
from django.core.exceptions import ValidationError
from graphene_django.types import DjangoObjectType
from rezq.models import LinkedCritique
from rezq.models import LinkedCritiqueComment
from rezq.models import Resume
from rezq.models import User
from rezq.utils.patch_model import patch_model


class LinkedCritiqueType(DjangoObjectType):

    class Meta:
        model = LinkedCritique
        only_fields = (
            'id', 'resume', 'summary', 'critiquer',
            'annotations', 'submitted', 'submitted_on',
        )

    token = graphene.String()


class PublicLinkedCritiqueType(DjangoObjectType):

    class Meta:
        model = LinkedCritique
        only_fields = (
            'id', 'resume', 'summary', 'critiquer',
            'annotations', 'submitted', 'submitted_on',
        )

    token = graphene.String()


class LinkedCritiqueCommentType(DjangoObjectType):

    class Meta:
        model = LinkedCritiqueComment
        only_fields = (
            'id', 'critique', 'user', 'comment',
        )


class PublicLinkedCritiqueCommentType(DjangoObjectType):

    class Meta:
        model = LinkedCritiqueComment
        only_fields = (
            'id', 'critique',
        )


class LinkedCritiqueQuery:

    linked_critique = graphene.Field(
        LinkedCritiqueType,
        token=graphene.String(required=True),
    )

    def resolve_linked_critique(self, info, **kwargs):
        try:
            return LinkedCritique.objects.get_by_token(kwargs['token'])
        except LinkedCritique.DoesNotExist:
            return None

        return None


class CreateLinkedCritique(graphene.Mutation):

    class Arguments:
        resume_token = graphene.String(required=True)

    critique = graphene.Field(LinkedCritiqueType)
    critique_created = graphene.Boolean()
    errors = graphene.types.json.JSONString()

    def mutate(self, info, **kwargs):
        try:
            resume = Resume.objects.get_by_token(kwargs['resume_token'])
        except Resume.DoesNotExist:
            return CreateLinkedCritique(
                errors={
                    'resume_token': 'This resume does not exist.',
                },
            )

        critique_created = True

        # If user is logged in
        if isinstance(info.context.user, User):
            try:
                # User continues their previously unsubmitted critique
                critique = LinkedCritique.objects.get(
                    resume=resume,
                    critiquer=info.context.user,
                    submitted=False,
                )
                critique_created = False
            except LinkedCritique.DoesNotExist:
                critique = LinkedCritique.objects.create(
                    resume=resume,
                    critiquer=info.context.user,
                )
        else:
            critique = LinkedCritique.objects.create(resume=resume)

        return CreateLinkedCritique(
            critique=critique, critique_created=critique_created,
        )


class SaveLinkedCritique(graphene.Mutation):

    class Arguments:
        token = graphene.String(required=True)
        submit = graphene.Boolean(
            default_value=False,
            description='Set `true` indicate submission',
        )
        summary = graphene.String(required=False)
        annotations = graphene.String(
            required=False,
            description='Serialized of PDF annotations',
        )

    critique = graphene.Field(LinkedCritiqueType)
    errors = graphene.types.json.JSONString()

    def mutate(self, info, **kwargs):
        try:
            critique = LinkedCritique.objects.get_by_token(kwargs['token'])
        except LinkedCritique.DoesNotExist:
            return SaveLinkedCritique(
                errors={
                    'token': 'This critique does not exist.',
                },
            )

        if critique.submitted:
            return SaveLinkedCritique(
                errors={
                    'submitted': (
                        'You cannot resubmit an already submitted critique.'
                    ),
                },
            )

        if kwargs.get('submit'):
            if not (critique.summary or kwargs.get('summary')):
                return SaveLinkedCritique(
                    errors={
                        'summary': 'You cannot submit without any comments.',
                    },
                )
            kwargs['submitted'] = True

        kwargs.pop('token', None)
        kwargs.pop('submit', None)

        # If user is logged in
        if isinstance(info.context.user, User):
            kwargs['critiquer'] = info.context.user

        try:
            patch_model(critique, kwargs)
        except ValidationError as e:
            return SaveLinkedCritique(errors=e.message_dict)

        return SaveLinkedCritique(critique=critique)


class CommentLinkedCritique(graphene.Mutation):

    class Arguments:
        critique_id = graphene.String(required=True)
        comment = graphene.String(required=True)

    comment = graphene.Field(LinkedCritiqueCommentType)
    errors = graphene.types.json.JSONString()

    def mutate(self, info, **kwargs):
        try:
            critique = LinkedCritique.objects.get(id=kwargs['critique_id'])
        except LinkedCritique.DoesNotExist:
            return CommentLinkedCritique(
                errors={
                    'critique_id': 'This critique does not exist.',
                },
            )

        if not critique.submitted:
            return CommentLinkedCritique(
                errors={
                    'critique_id': (
                        'Cannot comment on an unsubmitted critique.'
                    ),
                },
            )

        user = info.context.user

        comment = LinkedCritiqueComment.objects.create(
            critique=critique,
            user=user if type(user) is User else None,
            comment=kwargs['comment'],
        )

        return CommentLinkedCritique(comment=comment)


class LinkedCritiqueMutation:

    create_linked_critique = CreateLinkedCritique.Field()
    save_linked_critique = SaveLinkedCritique.Field()
    comment_linked_critique = CommentLinkedCritique.Field()
