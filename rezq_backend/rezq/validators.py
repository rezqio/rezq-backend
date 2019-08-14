from django.core.exceptions import ValidationError
from server.constants import INDUSTRIES


class IndustryValidationError(ValidationError):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class JsonArrayValidationError(ValidationError):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


def validate_industries(industries_string):
    industries = industries_string.split(',')
    industries_set = set(industries)

    if len(industries) != len(industries_set):
        raise ValidationError('Duplicate industries')

    invalid_industries_set = industries_set - INDUSTRIES

    if invalid_industries_set:
        raise IndustryValidationError(
            f'Invalid industries: {invalid_industries_set}. '
            f'Must be comma delimited string of: {INDUSTRIES}',
        )
