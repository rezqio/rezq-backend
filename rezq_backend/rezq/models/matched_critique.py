from django.conf import settings
from django.db import models
from django.utils import timezone
from rezq.models.abstract.critique import Critique
from rezq.utils.auth import create_email_unsubscribe_token
from rezq.utils.mailer import send_critiquer_matched_notif_mail


class MatchedCritique(Critique):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Save the old critiquer value to be used in save()
        self._critiquer = self.critiquer

    matched_on = models.DateTimeField(blank=True, null=True)

    def save(self, *args, **kwargs):
        if self._critiquer is None and self.critiquer is not None:
            # If a critiquer is assigned by this save
            self.matched_on = timezone.now()
        elif (
            self._critiquer is not None
            and self.critiquer is None
            and not self.submitted
        ):
            # If a critiquer is removed by this save,
            # and it hasn't been submitted, clear saved critique
            self.summary = ''
            self.annotations = '[]'

        if (
            self._critiquer != self.critiquer and
            self.critiquer.email is not None and
            self.critiquer.email_subscribed
        ):
            unsubscribe_token = create_email_unsubscribe_token(
                self.critiquer.id,
            )
            unsubscribe_link = (
                f'{settings.FRONTEND_URL}/unsubscribe-email'
                f'?token={unsubscribe_token}'
            )
            send_critiquer_matched_notif_mail(
                self.critiquer.email,
                unsubscribe_link,
            )

        super().save(*args, **kwargs)
