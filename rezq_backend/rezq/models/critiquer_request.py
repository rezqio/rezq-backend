from django.db import models
from rezq.models.abstract.timestamp_model import TimestampModel
from rezq.models.user import User
from rezq.validators import validate_industries


class CritiquerRequest(TimestampModel):

    critiquer = models.OneToOneField(User, on_delete=models.CASCADE)
    industries = models.TextField(validators=[validate_industries])
