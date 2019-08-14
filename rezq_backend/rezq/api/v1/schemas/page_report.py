import graphene
from rezq.models import PageReport
from rezq.models import User
from server.constants import EMAIL_REGEX


class ReportPage(graphene.Mutation):

    class Arguments:
        pathname = graphene.String(required=True)
        search = graphene.String()
        stars = graphene.Int()
        message = graphene.String()
        reply_to = graphene.String()

    errors = graphene.types.json.JSONString()

    def mutate(self, info, **kwargs):
        if (
            kwargs.get('reply_to') and
            not EMAIL_REGEX.match(kwargs['reply_to'])
        ):
            return ReportPage(
                errors={
                    'replyTo': 'Invalid email address.',
                },
            )

        user = info.context.user

        PageReport.objects.create(
            reporter=user if type(user) is User else None,
            pathname=kwargs['pathname'],
            search=kwargs.get('search') or None,
            stars=kwargs.get('stars') or None,
            message=kwargs.get('message') or None,
            reply_to=kwargs.get('reply_to') or None,
        )

        return ReportPage()


class ReportPageMutation:

    report_page = ReportPage.Field()
