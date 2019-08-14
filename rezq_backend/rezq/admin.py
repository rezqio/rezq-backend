from django.conf import settings
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from rezq.actions import match_critiquers
from rezq.actions import match_critiques
from rezq.forms import RezqUserChangeForm
from rezq.forms import RezqUserCreationForm
from rezq.models import CritiquerRequest
from rezq.models import LinkedCritique
from rezq.models import LinkedCritiqueComment
from rezq.models import MatchedCritique
from rezq.models import MatchedCritiqueComment
from rezq.models import PageReport
from rezq.models import Pool
from rezq.models import PooledCritique
from rezq.models import PooledCritiqueComment
from rezq.models import PooledCritiqueVote
from rezq.models import Resume
from rezq.models import User


@admin.register(User)
class RezqUserAdmin(UserAdmin):

    form = RezqUserChangeForm
    add_form = RezqUserCreationForm

    add_fieldsets = (
        (
            None, {
                'classes': ('wide',),
                'fields': ('email', 'password1', 'password2', ),
            },
        ),
    )

    fieldsets = UserAdmin.fieldsets[:2] + (
        (
            'RezQ', {
                'fields': (
                    'unverified_email',
                    'waterloo_id',
                    'facebook_id',
                    'google_id',
                    'industries',
                    'email_subscribed',
                    'is_verified',
                    'is_premium',
                ),
            },
        ),
    ) + UserAdmin.fieldsets[2:]

    list_display = (
        'username', 'email', 'waterloo_id',
        'facebook_id', 'google_id', 'is_active', 'date_joined',
    )
    ordering = ('-date_joined',)


class RezqModelAdmin(admin.ModelAdmin):

    list_display = ('id', 'created_on')
    ordering = ('-created_on',)
    readonly_fields = ('id', 'created_on', 'updated_on')


@admin.register(Resume)
class ResumeAdmin(RezqModelAdmin):

    def has_add_permission(self, request):
        return False

    list_display = (
        'uploader', 'name', 'industries',
        'link_enabled', 'pool', 'created_on',
    )

    readonly_fields = (
        'id', 'created_on', 'updated_on',
        'download_url', 'thumbnail_download_url',
    )


@admin.register(CritiquerRequest)
class CritiquerRequestAdmin(RezqModelAdmin):

    actions = [match_critiquers]

    list_display = ('critiquer', 'industries', 'created_on')


@admin.register(MatchedCritique)
class MatchedCritiqueAdmin(RezqModelAdmin):

    actions = [match_critiques]

    list_display = ('critiquer', 'submitted', 'created_on')

    readonly_fields = (
        'id', 'created_on', 'updated_on',
        'matched_on', 'submitted_on',
    )


@admin.register(MatchedCritiqueComment)
class MatchedCritiqueCommentAdmin(RezqModelAdmin):

    pass


@admin.register(LinkedCritique)
class LinkedCritiqueAdmin(RezqModelAdmin):

    list_display = ('critiquer', 'submitted', 'created_on')

    readonly_fields = (
        'id', 'created_on', 'updated_on',
        'submitted_on',
    )


@admin.register(LinkedCritiqueComment)
class LinkedCritiqueCommentAdmin(RezqModelAdmin):

    pass


@admin.register(PooledCritique)
class PooledCritiqueAdmin(RezqModelAdmin):

    list_display = ('critiquer', 'submitted', 'upvotes', 'created_on')

    readonly_fields = (
        'id', 'created_on', 'updated_on',
        'submitted_on', 'upvotes',
    )


@admin.register(PooledCritiqueVote)
class PooledCritiqueVoteAdmin(RezqModelAdmin):

    list_display = ('voter', 'is_upvote', 'created_on')


@admin.register(PooledCritiqueComment)
class PooledCritiqueCommentAdmin(RezqModelAdmin):

    pass


@admin.register(PageReport)
class PageReportAdmin(RezqModelAdmin):

    list_display = ('reporter', 'pathname', 'stars', 'reply_to', 'created_on')


@admin.register(Pool)
class PoolAdmin(admin.ModelAdmin):

    list_display = ('id', 'created_on')
    ordering = ('id',)


if settings.DEBUG:
    from rezq.models.dev.mock_s3_file import MockS3File

    @admin.register(MockS3File)
    class MockS3FileAdmin(RezqModelAdmin):

        readonly_fields = (
            'id', 'created_on', 'updated_on', 'download_url',
        )
