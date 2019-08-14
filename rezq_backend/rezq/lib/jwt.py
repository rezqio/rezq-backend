import jwt
from django.conf import settings
from jwt import exceptions
from jwt import ExpiredSignatureError


HS256 = 'HS256'


def encode(payload):
    return jwt.encode(
        payload, key=settings.SECRET_KEY, algorithm=HS256,
    ).decode('ascii')


def decode(encoded, verify=True):
    return jwt.decode(
        encoded, key=settings.SECRET_KEY, verify=verify, algorithms=[HS256],
    )


__all__ = [
    encode,
    decode,
    ExpiredSignatureError,
    exceptions,
]
