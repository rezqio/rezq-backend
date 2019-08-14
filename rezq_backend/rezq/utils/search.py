def gen_queryset(sqs):
    for x in sqs:
        yield x.object
