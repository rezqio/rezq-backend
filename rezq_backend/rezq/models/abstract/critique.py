from django.conf import settings
from django.db import models
from django.utils import timezone
from rezq.models.abstract.timestamp_model import TimestampModel
from rezq.models.resume import Resume
from rezq.models.user import User
from rezq.utils.auth import create_email_unsubscribe_token
from rezq.utils.mailer import send_critique_completed_notif_mail


class Critique(TimestampModel):

    class Meta:
        abstract = True

    # Do not delete this Critique if the critiquer Profile is deleted
    critiquer = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    resume = models.ForeignKey(
        Resume,
        on_delete=models.CASCADE,
    )

    summary = models.TextField(
        blank=True,
        default='',
    )

    annotations = models.TextField(
        default='[]',
    )

    submitted = models.BooleanField(default=False, db_index=True)
    submitted_on = models.DateTimeField(blank=True, null=True)

    def save(self, *args, **kwargs):
        if self.submitted:
            self.submitted_on = timezone.now()

            uploader = self.resume.uploader
            if uploader.email is not None and uploader.email_subscribed:
                unsubscribe_token = create_email_unsubscribe_token(uploader.id)
                unsubscribe_link = (
                    f'{settings.FRONTEND_URL}/unsubscribe-email'
                    f'?token={unsubscribe_token}'
                )
                send_critique_completed_notif_mail(
                    uploader.email,
                    self.resume.name,
                    unsubscribe_link,
                )

        super().save(*args, **kwargs)
