def get_institution_from_email(email):
    if not email:
        return None

    split = email.split('@', 1)

    if len(split) != 2:
        return None

    return split[1]
