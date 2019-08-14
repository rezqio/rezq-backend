import graphene
from rezq.api.v1.schemas import CritiqueMutation
from rezq.api.v1.schemas import CritiqueQuery
from rezq.api.v1.schemas import LinkedCritiqueMutation
from rezq.api.v1.schemas import LinkedCritiqueQuery
from rezq.api.v1.schemas import PasswordResetMutation
from rezq.api.v1.schemas import PooledCritiqueMutation
from rezq.api.v1.schemas import PooledCritiqueQuery
from rezq.api.v1.schemas import ProfileMutationPrivate
from rezq.api.v1.schemas import ProfileMutationPublic
from rezq.api.v1.schemas import ProfileQuery
from rezq.api.v1.schemas import ProfileQueryPublic
from rezq.api.v1.schemas import ReportPageMutation
from rezq.api.v1.schemas import ResumeMutation
from rezq.api.v1.schemas import ResumeQuery
from rezq.api.v1.schemas import ResumeQueryPublic
from rezq.api.v1.schemas import ServerTimeQuery
from rezq.api.v1.schemas import TokenMutationPrivate
from rezq.api.v1.schemas import TokenMutationPublic


class PrivateQuery(
    CritiqueQuery,
    PooledCritiqueQuery,
    ProfileQuery,
    ResumeQuery,
    ResumeQueryPublic,
    graphene.ObjectType,
):
    """These queries require authentication.
    """
    pass


class PrivateMutation(
    ReportPageMutation,
    ProfileMutationPrivate,
    PooledCritiqueMutation,
    TokenMutationPrivate,
    ResumeMutation,
    CritiqueMutation,
    LinkedCritiqueMutation,
    graphene.ObjectType,
):
    """These mutations require authentication.
    """
    pass


class PublicQuery(
    ServerTimeQuery,
    LinkedCritiqueQuery,
    ResumeQueryPublic,
    ProfileQueryPublic,
    graphene.ObjectType,
):
    """These queries don't require authentication.
    """
    pass


class PublicMutation(
    ReportPageMutation,
    ProfileMutationPublic,
    TokenMutationPublic,
    LinkedCritiqueMutation,
    PasswordResetMutation,
    graphene.ObjectType,
):
    """These mutations don't require authentication.
    """
    pass


private_schema = graphene.Schema(query=PrivateQuery, mutation=PrivateMutation)
public_schema = graphene.Schema(query=PublicQuery, mutation=PublicMutation)
