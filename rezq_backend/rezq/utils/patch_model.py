def patch_model(model_object, data):
    """Updates and saves a model object with provided data.

    :param model_object: any Django model
    :type model_object: django.db.models.Model
    :param data: attribute to value
    :type data: dict

    :raises something: on invalid attributes
    """
    for k, v in data.items():
        setattr(model_object, k, v)
    model_object.full_clean()
    model_object.save()
