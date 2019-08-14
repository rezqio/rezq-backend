import logging

from admin_honeypot.signals import honeypot
from django.dispatch import receiver


logger = logging.getLogger(__name__)


@receiver(honeypot)
def admin_honeypot_callback(instance, request, **kwargs):
    logger.info(
        '%s tried to log into /admin/ honeypot with username %s',
        instance.ip_address,
        instance.username,
    )
