import logging

from rezq.lib import jwt
from rezq.models.abstract.critique import Critique
from rezq.models.abstract.timestamp_model import TimestampModelManager


logger = logging.getLogger(__name__)


class LinkedCritiqueManager(TimestampModelManager):

    def get_by_token(self, token):
        try:
            id = jwt.decode(token)['id']
        except Exception as e:
            logger.info(f'{type(e)}: {str(e)}')
            raise self.model.DoesNotExist(
                'LinkedCritique matching query does not exist.',
            )

        return self.get(id=id)


class LinkedCritique(Critique):

    objects = LinkedCritiqueManager()

    @property
    def token(self):
        return jwt.encode({'id': str(self.id)})
