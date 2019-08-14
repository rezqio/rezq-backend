import logging
import operator
from functools import reduce

import graphene
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import connection
from django.db import transaction
from django.db.models import Q
from graphene_django.types import DjangoObjectType
from rezq.models import Pool
from rezq.models import Resume
from rezq.models import User
from rezq.utils.patch_model import patch_model
from rezq.utils.request import get_client_info_str
from server.constants import DOMAIN_REGEX
from server.constants import MAX_RESUMES
from server.constants import PUBLIC


logger = logging.getLogger(__name__)


if settings.DEBUG:
    from uuid import UUID

    def _parse_pooled_critiques_user_upvoted_rows(rows):
        return {
            str(UUID(uuid)): user_upvoted
            for uuid, user_upvoted in rows
        }
else:
    def _parse_pooled_critiques_user_upvoted_rows(rows):
        return {
            str(uuid): user_upvoted
            for uuid, user_upvoted in rows
        }


def _get_pooled_critiques_user_upvoted(resume_id, user_id):
    lj_q = f"""
        LEFT JOIN (
            SELECT
                critique_id,
                is_upvote
            FROM rezq_pooledcritiquevote
            WHERE
                voter_id = '{str(user_id).replace('-', '')}'
        ) v
        ON
            c.id = v.critique_id
    """ if user_id else ''
    q = f"""
        SELECT
            id,
            {'' if user_id else 'NULL AS '}is_upvote
        FROM (
            SELECT
                id
            FROM rezq_pooledcritique
            WHERE
                resume_id = '{str(resume_id).replace('-', '')}'
        ) c
        {lj_q};
    """

    cursor = connection.cursor()

    cursor.execute(q)

    return _parse_pooled_critiques_user_upvoted_rows(cursor.fetchall())


def _should_get_pooled_critiques_user_upvoted(info):
    try:
        for sel in info.field_asts[0].selection_set.selections:
            if sel.name.value == 'pooledCritiquesUserUpvoted':
                return True
    except Exception as e:
        logger.error(f'{type(e)}: {str(e)}')
    return False


class PoolType(DjangoObjectType):

    class Meta:
        model = Pool
        only_fields = ('id',)


class ResumeType(DjangoObjectType):

    class Meta:
        model = Resume
        only_fields = (
            'id', 'uploader', 'name', 'description', 'industries',
            'notes_for_critiquer', 'link_enabled', 'pool',
            'created_on', 'matchedcritique_set',
            'linkedcritique_set', 'pooledcritique_set',
        )

    token = graphene.String()
    download_url = graphene.String()
    thumbnail_download_url = graphene.String()
    user_is_premium = graphene.Boolean()
    pooled_critiques_user_upvoted = graphene.types.json.JSONString()


class PublicResumeType(DjangoObjectType):

    class Meta:
        model = Resume
        only_fields = (
            'id', 'uploader', 'name', 'description', 'industries',
            'notes_for_critiquer', 'pool', 'created_on',
            'pooledcritique_set',
        )

    token = graphene.String()
    download_url = graphene.String()
    thumbnail_download_url = graphene.String()
    pooled_critiques_user_upvoted = graphene.types.json.JSONString()


class PublicResumeTypeWithCount(graphene.ObjectType):

    resumes = graphene.List(PublicResumeType)
    total_count = graphene.Int()


class ResumeQuery:

    resumes = graphene.List(ResumeType)

    resume = graphene.Field(
        ResumeType,
        id=graphene.String(required=True),
    )

    def resolve_resumes(self, info, **kwargs):
        return Resume.objects.filter(
            uploader=info.context.user,
        ).order_by('-created_on')

    def resolve_resume(self, info, **kwargs):
        try:
            resume = Resume.objects.get(id=kwargs['id'])
        except Resume.DoesNotExist:
            return None

        if not resume.download_url:
            resume.delete()
            return None

        if not (
            info.context.user == resume.uploader
            or resume.matchedcritique_set.filter(
                critiquer=info.context.user,
            ).exists()
        ):
            return None

        resume.user_is_premium = info.context.user.is_premium

        if _should_get_pooled_critiques_user_upvoted(info):
            resume.pooled_critiques_user_upvoted = (
                _get_pooled_critiques_user_upvoted(
                    kwargs['id'],
                    info.context.user.id,
                )
            )

        return resume


class ResumeQueryPublic:

    resume = graphene.Field(
        ResumeType,
        token=graphene.String(required=True),
    )

    pooled_resumes = graphene.Field(
        PublicResumeTypeWithCount,
        industries=graphene.String(required=False),
        first=graphene.Int(required=False),
        offset=graphene.Int(required=False),
        private_pool=graphene.String(required=False),
    )

    pooled_resume = graphene.Field(
        PublicResumeType,
        id=graphene.String(required=True),
        private_pool=graphene.String(required=False),
    )

    def resolve_resume(self, info, **kwargs):
        try:
            resume = Resume.objects.get_by_token(kwargs['token'])
        except Resume.DoesNotExist:
            return None

        if not resume.download_url:
            resume.delete()
            return None

        return resume

    def resolve_pooled_resumes(self, info, **kwargs):
        """
        If a page size is n resumes, then the client would pass in
        first = n and offset = pagenumber * n
        """
        # if user is logged in, else None
        user = info.context.user
        user = user if type(user) is User else None

        querys = []

        if kwargs.get('industries', '') != '':
            industries = kwargs['industries'].split(',')

            querys.append(
                reduce(
                    operator.and_, (
                        Q(industries__contains=industry)
                        for industry in industries
                    ),
                ),
            )

        if kwargs.get('private_pool'):
            if DOMAIN_REGEX.match(kwargs['private_pool']):
                # This guy is trying to hack institution pools!
                return []

            resumes = Resume.objects.filter(
                *querys,
                pool=kwargs['private_pool'],
            )
        elif user:
            pools = user.institutions
            pools.add(PUBLIC)
            resumes = Resume.objects.filter(
                *querys,
                pool__in=pools,
            )
        else:
            resumes = Resume.objects.filter(
                *querys,
                pool=PUBLIC,
            )

        resumes = resumes.order_by('-created_on')

        total_count = resumes.count()

        # Move cursor to the m'th resume. The offset occurs first.
        if 'offset' in kwargs:
            resumes = resumes[kwargs['offset']:]

        # Return the first n items after some offset. This is our batch size.
        if 'first' in kwargs:
            resumes = resumes[:kwargs['first']]

        logger.info(
            '%s accessed resumes: %s',
            get_client_info_str(info.context),
            str([str(r.id) for r in resumes]),
        )

        return PublicResumeTypeWithCount(
            resumes=resumes,
            total_count=total_count,
        )

    def resolve_pooled_resume(self, info, **kwargs):
        # if user is logged in, else None
        user = info.context.user
        user = user if type(user) is User else None

        try:
            if kwargs.get('private_pool'):
                if DOMAIN_REGEX.match(kwargs['private_pool']):
                    # This guy is trying to hack institution pools!
                    return None
                resume = Resume.objects.get(
                    id=kwargs['id'], pool=kwargs['private_pool'],
                )
            elif user:
                pools = user.institutions
                pools.add(PUBLIC)
                resume = Resume.objects.get(id=kwargs['id'], pool__in=pools)
            else:
                resume = Resume.objects.get(id=kwargs['id'], pool=PUBLIC)
        except Resume.DoesNotExist:
            return None

        if not resume.download_url:
            resume.delete()
            return None

        if _should_get_pooled_critiques_user_upvoted(info):
            resume.pooled_critiques_user_upvoted = (
                _get_pooled_critiques_user_upvoted(
                    kwargs['id'],
                    info.context.user.id,
                )
            )

        logger.info(
            '%s accessed resume: %s',
            get_client_info_str(info.context),
            str(resume.id),
        )

        return resume


class UploadResume(graphene.Mutation):

    class Arguments:
        name = graphene.String(
            required=True,
        )
        description = graphene.String(
            default_value='',
        )
        industries = graphene.String(
            required=True,
            description='Comma delimited string of industries',
        )
        link_enabled = graphene.Boolean(
            default_value=False,
        )

        # institution_pool is autocreated
        institution_pool = graphene.String(
            required=False,
        )
        # we create private pools in /admin
        private_pool = graphene.String(
            required=False,
        )

    resume = graphene.Field(ResumeType)
    upload_info = graphene.types.json.JSONString()
    thumbnail_upload_info = graphene.types.json.JSONString()
    errors = graphene.types.json.JSONString()

    def mutate(self, info, **kwargs):
        user = info.context.user

        if not user.is_active:
            return UploadResume(
                errors={
                    'user': 'Email requires verification.',
                },
            )

        if not kwargs['name']:
            return UploadResume(
                errors={
                    'name': 'Your resume name cannot be blank.',
                },
            )

        if not kwargs['industries']:
            return UploadResume(
                errors={
                    'industries': 'You must enter at least one industry.',
                },
            )

        # if both are not empty strings or null
        if kwargs.get('institution_pool') and kwargs.get('private_pool'):
            return UploadResume(
                errors={
                    'pool': (
                        'Only one of industry pool or '
                        'private pool may be entered.'
                    ),
                },
            )

        if info.context.user.resume_set.count() >= MAX_RESUMES:
            return UploadResume(
                errors={
                    'max_num': (
                        f'You cannot upload more than {MAX_RESUMES} resumes.'
                    ),
                },
            )

        if (
            kwargs.get('institution_pool') and
            not user.can_access_pool(kwargs['institution_pool'])
        ):
            return UploadResume(
                errors={
                    'institution_pool': 'You don\'t have access to this pool.',
                },
            )

        # default none
        pool = None

        if kwargs.get('private_pool'):
            if DOMAIN_REGEX.match(kwargs['private_pool']):
                # This guy is trying to hack institution pools!
                return UploadResume(
                    errors={
                        'private_pool': 'Invalid private pool.',
                    },
                )
            try:
                pool = Pool.objects.get(id=kwargs['private_pool'])
            except Pool.DoesNotExist:
                # we need to create this in /admin
                return UploadResume(
                    errors={
                        'private_pool': 'Invalid private pool.',
                    },
                )

        try:
            with transaction.atomic():
                if kwargs.get('institution_pool'):
                    # autocreate
                    pool, _ = Pool.objects.get_or_create(
                        id=kwargs['institution_pool'],
                    )

                resume = Resume.objects.create(
                    uploader=user,
                    name=kwargs['name'],
                    description=kwargs['description'],
                    industries=kwargs['industries'],
                    link_enabled=kwargs['link_enabled'],
                    pool=pool,
                )

                resume.full_clean()
        except ValidationError as e:
            return UploadResume(errors=e.message_dict)

        return UploadResume(
            resume=resume,
            upload_info=resume.upload_info,
            thumbnail_upload_info=resume.thumbnail_upload_info,
        )


class EditResume(graphene.Mutation):

    class Arguments:
        id = graphene.String(
            required=True,
        )
        name = graphene.String(
            required=False,
        )
        description = graphene.String(
            required=False,
        )
        industries = graphene.String(
            required=False,
            description='Comma delimited string of industries',
        )
        notes_for_critiquer = graphene.String(
            required=False,
        )
        link_enabled = graphene.Boolean(
            required=False,
        )

        # institution_pool is autocreated
        institution_pool = graphene.String(
            required=False,
        )
        # we create private pools in /admin
        private_pool = graphene.String(
            required=False,
        )

    resume = graphene.Field(ResumeType)
    errors = graphene.types.json.JSONString()

    def mutate(self, info, **kwargs):
        user = info.context.user

        if 'name' in kwargs and not kwargs['name']:
            return EditResume(
                errors={
                    'name': 'Your resume name cannot be blank.',
                },
            )

        if 'industries' in kwargs and not kwargs['industries']:
            return EditResume(
                errors={
                    'industries': 'You must enter at least one industry.',
                },
            )

        # pop first cuz we pass kwargs into patch_model()
        institution_pool = kwargs.pop('institution_pool', None)
        private_pool = kwargs.pop('private_pool', None)

        # if both not empty strings and not null
        # then the only way to disable pool is to
        # # send one or both as empty string
        if institution_pool and private_pool:
            return EditResume(
                errors={
                    'pool': (
                        'Only one of industry pool or '
                        'private pool may be entered.'
                    ),
                },
            )

        if (
            institution_pool and
            not user.can_access_pool(institution_pool)
        ):
            return EditResume(
                errors={
                    'institution_pool': 'You don\'t have access to this pool.',
                },
            )

        pool = None

        if private_pool:
            if DOMAIN_REGEX.match(private_pool):
                # This guy is trying to hack institution pools!
                return EditResume(
                    errors={
                        'private_pool': 'Invalid private pool.',
                    },
                )
            try:
                pool = Pool.objects.get(id=private_pool)
            except Pool.DoesNotExist:
                return EditResume(
                    errors={
                        'private_pool': 'Invalid private pool.',
                    },
                )

        try:
            resume = Resume.objects.get(
                id=kwargs['id'],
                uploader=info.context.user,
            )
        except Resume.DoesNotExist:
            return EditResume(
                errors={
                    'id': 'This resume does not exist.',
                },
            )

        if not resume.download_url:
            resume.delete()
            return EditResume(
                errors={
                    'id': 'This resume does not exist.',
                },
            )

        try:
            with transaction.atomic():
                if institution_pool:
                    pool, _ = Pool.objects.get_or_create(
                        id=institution_pool,
                    )

                # if either were passed in
                # (but not both cuz we verified that earlier)
                # this allows us to disable pooling if
                # one of them is the empty string
                if not (institution_pool is None and private_pool is None):
                    kwargs['pool'] = pool

                patch_model(resume, kwargs)
        except ValidationError as e:
            return EditResume(errors=e.message_dict)

        return EditResume(resume=resume)


class DeleteResume(graphene.Mutation):

    class Arguments:
        id = graphene.String(required=True)

    errors = graphene.types.json.JSONString()

    def mutate(self, info, **kwargs):
        try:
            resume = Resume.objects.get(
                id=kwargs['id'],
                uploader=info.context.user,
            )
        except Resume.DoesNotExist:
            return DeleteResume(
                errors={
                    'id': 'This resume does not exist.',
                },
            )

        resume.delete()

        return DeleteResume()


class DeleteResumes(graphene.Mutation):

    class Arguments:
        ids = graphene.List(graphene.String, required=True)

    errors = graphene.types.json.JSONString()

    def mutate(self, info, **kwargs):
        with transaction.atomic():
            for r in Resume.objects.filter(
                id__in=kwargs['ids'],
                uploader=info.context.user,
            ):
                r.delete()

        return DeleteResumes()


class ResumeMutation:

    upload_resume = UploadResume.Field()
    edit_resume = EditResume.Field()
    delete_resume = DeleteResume.Field()
    delete_resumes = DeleteResumes.Field()
