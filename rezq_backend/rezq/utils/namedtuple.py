from collections import namedtuple


def namedtuple_from_kwargs(name, **kwargs):
    """Create and instantiate namedtuple using kwargs.

    :param name: typename
    :type name: str
    :param kwargs: field_names to values
    :type kwargs: dict

    :return: a namedtuple
    :rtype: collections.namedtuple
    """
    return namedtuple(name, sorted(kwargs.keys()))(**kwargs)


def namedtuple_to_tuple_list(ntuple):
    """Flattens a namedtuple.

    :param ntuple: any namedtuple
    :type ntuple: collections.namedtuple

    :return: list of field_names and values
    :rtype: list( tuple( str, object ) )
    """
    return list(ntuple._asdict().items())


def namedtuple_and_choices_from_kwargs(name, **kwargs):
    """Used for creating model Field.choices.

    :param name: typename
    :type name: str
    :param kwargs: field_names to values
    :type kwargs: dict

    :return: tuple of namedtuple and choices
    :rtype: tuple( collections.namedtuple, list( tuple( str, object ) ) )
    """
    return (
        namedtuple(name, sorted(kwargs.keys()))(
            **{k: k for k in kwargs.keys()}
        ),
        list(kwargs.items()),
    )
