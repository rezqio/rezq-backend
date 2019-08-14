import logging
from time import time as timer

from graphql import GraphQLError


logger = logging.getLogger(__name__)

MAX_TIMEOUT_MS = 10000
MAX_QUERY_DEPTH = 6

# TODO: throttle based on query complexity
# TODO: timeout needs to be killing the thread from another thread


class QueryTimeoutMiddleware:

    def __init__(self):
        self.query_stopwatch_ms = 0.0

    def resolve(self, next, root, info, **args):
        # reset stopwatch on new query
        if len(info.path) == 1:
            self.query_stopwatch_ms = 0.0

        start = timer()
        return_value = next(root, info, **args)
        duration_ms = (timer() - start) * 1000

        logger.debug('%s: %.2f ms', info.field_name, duration_ms)

        self.query_stopwatch_ms += duration_ms

        if self.query_stopwatch_ms > MAX_TIMEOUT_MS:
            if len(info.path) == 1:
                logger.info(info.operation)
            self.query_stopwatch_ms = 0.0
            raise GraphQLError('GraphQL query timed out.')

        return return_value


class QueryDepthMiddleware:

    def check_query_depth(self, selection_set, query_depth=1):
        if hasattr(selection_set, 'selections'):
            for field in selection_set.selections:
                if hasattr(field, 'selection_set'):
                    if query_depth + 1 > MAX_QUERY_DEPTH:
                        raise GraphQLError(
                            'GraphQL query depth maximum exceeded.',
                        )

                    self.check_query_depth(
                        field.selection_set, query_depth=query_depth + 1,
                    )

    def resolve(self, next, root, info, **args):
        query_ast = info.operation

        try:
            self.check_query_depth(query_ast.selection_set)
        except GraphQLError:
            if len(info.path) == 1:
                logger.info(query_ast)
            raise

        return next(root, info, **args)
