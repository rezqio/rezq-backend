# RezQ Backend

## Development

Doesn't support Windows.

### Prerequisites

1. `python3.6`
2. `virtualenv`
3. `make`
4. `docker`

### Environment Variables

#### Development

```
```

#### Production

```
DJANGO_PROD='TRUE'
DJANGO_ADMIN_PAGE_PATH'???'
DJANGO_SECRET_KEY='???'
DJANGO_DB_HOST='???'
DJANGO_DB_PASSWORD='???'
EMAIL_HOST_PASSWORD='???'
```

### Make

Try `make help`.

### Virtual Environment

You **must** activate the `.venv` every time! You can either:

* Install `direnv` to activate automatically: https://direnv.net/
* `source .venv/bin/activate` manually

## Original Authors

* [Andrew Gapic](https://github.com/agapic)
* [Evan Cao](https://github.com/evancoa)
* [Fanny Deng](https://github.com/fannydengdeng)
* [Gary Zheng](https://github.com/dongyuzheng)
* [Ian Yuan](https://github.com/iyyuan)
* [Judy Chen](https://github.com/ju-de)
