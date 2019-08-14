import logging

from django.contrib import messages
from django.db import transaction
from rezq.lib.ga_matcher import get_matchings
from rezq.models import CritiquerRequest
from rezq.models import MatchedCritique

logger = logging.getLogger(__name__)


def match(matched_critiques=None, critiquer_requests=None):
    """Match critiques!
    """
    logger.info('Starting critique matching')

    if matched_critiques is None:
        matched_critiques = MatchedCritique.objects.filter(
            critiquer=None, submitted=False,
        )
    if critiquer_requests is None:
        critiquer_requests = CritiquerRequest.objects.all()

    matchings = get_matchings(matched_critiques, critiquer_requests)

    logger.info('Saving %d matches', len(matchings))

    # Assign critiquer, and delete the critiquer request
    with transaction.atomic():
        for matched_critique, critiquer_request in matchings:
            matched_critique.critiquer = critiquer_request.critiquer
            matched_critique.save()
            critiquer_request.delete()

    logger.info('Matched %d critiques', len(matchings))


def match_critiques(_modeladmin, request, matched_critiques):
    """Match selected "MatchedCritique" objects in Django admin
    """
    for mc in matched_critiques:
        if mc.critiquer:
            messages.error(request, f'{mc.id} is already matched.')
            return
        if mc.submitted:
            messages.error(request, f'{mc.id} is already submitted.')
            return

    match(matched_critiques, CritiquerRequest.objects.all())


def match_critiquers(_modeladmin, _request, critiquer_requests):
    """Match selected "CritiquerRequest" objects in Django admin
    """
    match(
        MatchedCritique.objects.filter(critiquer=None, submitted=False),
        critiquer_requests,
    )
