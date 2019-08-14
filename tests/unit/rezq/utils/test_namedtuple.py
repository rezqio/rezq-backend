from collections import namedtuple

from rezq.utils.namedtuple import namedtuple_and_choices_from_kwargs
from rezq.utils.namedtuple import namedtuple_from_kwargs
from rezq.utils.namedtuple import namedtuple_to_tuple_list

empty_tuple = namedtuple('EmptyTuple', field_names=[])()
ab_tuple = namedtuple('ABTuple', field_names=['a', 'b'])(a=1, b=2)
aa_bb_tuple = namedtuple('ABTuple', field_names=['a', 'b'])(
    a='a',
    b='b',
)


def test_namedtuple_from_kwargs_empty():
    nt = namedtuple_from_kwargs('EmptyTuple')
    assert nt == empty_tuple
    assert nt.__class__.__name__ == empty_tuple.__class__.__name__


def test_namedtuple_from_kwargs_not_empty():
    nt = namedtuple_from_kwargs('ABTuple', a=1, b=2)
    assert nt == ab_tuple
    assert nt.__class__.__name__ == ab_tuple.__class__.__name__


def test_namedtuple_to_tuple_list_empty():
    assert namedtuple_to_tuple_list(empty_tuple) == []


def test_namedtuple_to_tuple_list_not_empty():
    assert namedtuple_to_tuple_list(ab_tuple) == [('a', 1), ('b', 2)]


def test_namedtuple_and_choices_from_kwargs_empty():
    nt, choices = namedtuple_and_choices_from_kwargs('EmptyTuple')
    assert nt == empty_tuple
    assert nt.__class__.__name__ == empty_tuple.__class__.__name__
    assert choices == []


def test_namedtuple_and_choices_from_kwargs_not_empty():
    nt, choices = namedtuple_and_choices_from_kwargs('ABTuple', a=1, b=2)
    assert nt == aa_bb_tuple
    assert nt.__class__.__name__ == aa_bb_tuple.__class__.__name__
    assert choices == [('a', 1), ('b', 2)]
