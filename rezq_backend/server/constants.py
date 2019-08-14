import re


DOMAIN_REGEX = re.compile(
    r'^(?:[a-zA-Z0-9-]+\.)+[a-zA-Z0-9-]{2,6}$',
)

EMAIL_REGEX = re.compile(
    r'(^[a-zA-Z0-9_+-]+(?:\.[a-zA-Z0-9_+-]+)*'
    r'@(?:[a-zA-Z0-9-]+\.)+[a-zA-Z0-9-]{2,6}$)',
)

USERNAME_REGEX = re.compile(r'^[0-9a-zA-Z]+$')

AUTH_TOKEN_EXPIRE_MINUTES = 720

PASSWORD_RESET_TOKEN_EXPIRE_MINUTES = 30

EMAIL_VERIFICATION_TOKEN_EXPIRE_MINUTES = 90

MAX_RESUMES = 5

FROM_EMAIL_ADDRESS = 'noreply@rezq.io'

INDUSTRIES = {
    'ACC',
    'ADM',
    'ANA',
    'ARCH',
    'BANK',
    'BIO',
    'BUS',
    'CHEM',
    'COMM',
    'CONS',
    'DATA',
    'DES',
    'ENG',
    'ENV',
    'FIN',
    'FINT',
    'GEOL',
    'GEOM',
    'HARD',
    'HEAL',
    'LAW',
    'MATH',
    'MECH',
    'MED',
    'MUSI',
    'PHYS',
    'PROJ',
    'RES',
    'RET',
    'ROBO',
    'SERV',
    'SOFT',
    'TEAC',
    'TECH',
    'WRIT',
}

PUBLIC = 'bUbl1c623'
