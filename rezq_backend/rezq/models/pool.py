from django.core.validators import RegexValidator
from django.db import models
from server.constants import DOMAIN_REGEX


class Pool(models.Model):

    # email domain (edu.uwaterloo.ca) or some secret code we hand out
    id = models.CharField(
        primary_key=True,
        max_length=253,
        validators=[
            RegexValidator(
                regex=DOMAIN_REGEX,
                inverse_match=True,
                message='Pool ID must NOT be a domain.',
            ),
        ],
    )

    created_on = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.id
