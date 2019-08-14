ifeq ($(findstring BSD,$(shell grep --version)),BSD)
  # BSD grep
  VERSION=$(shell cat rezq_backend/__init__.py | \
            grep '__version__ = ' | \
            grep -Eo '\d+\.\d+\.\d+')
else
  # Unix grep
  VERSION=$(shell cat rezq_backend/__init__.py | \
            grep '__version__ = ' | \
            grep -Po '\d+\.\d+\.\d+')
endif


.PHONY: help install deps db shell runserver docker-dev docker-dev-testing \
	lint check-deploy unit-test smoke-test test clean-db clean secret-key deploy


help:  ## display this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'

install: deps db  ## make deps db, then set up pre-commit hooks
	.venv/bin/pre-commit install --install-hooks -f

deps:  ## install dependencies
ifndef VIRTUAL_ENV
	virtualenv -p python3 .venv
endif
	.venv/bin/pip install -r requirements.txt -r requirements-dev.txt || ( \
		virtualenv -p python3 .venv && \
		.venv/bin/pip install -r requirements.txt -r requirements-dev.txt \
	)

db:  ## migrate dev database and add test data
	.venv/bin/python rezq_backend/manage.py makemigrations rezq
	.venv/bin/python rezq_backend/manage.py migrate
	.venv/bin/python rezq_backend/manage.py loaddata fixtures/dev.json

shell:  ## enter interactive Python shell
	.venv/bin/python rezq_backend/manage.py shell_plus

runserver:  ## start the development server
	.venv/bin/python -Wall rezq_backend/manage.py runserver_plus localhost:8000

docker-dev:  ## builds docker DEBUG server (port 80)
	docker build -f dockerfiles/dev/Dockerfile . -t rezq.io/backend-dev:$(VERSION)
	docker tag rezq.io/backend-dev:$(VERSION) rezq.io/backend-dev:latest

docker-dev-testing:  ## builds docker DEBUG server for testing (port 80)
	docker build -f dockerfiles/dev/Dockerfile . -t rezq.io/backend-dev-testing:$(VERSION)
	docker tag rezq.io/backend-dev-testing:$(VERSION) rezq.io/backend-dev-testing:latest

lint:  ## run pre-commit on all files
	.venv/bin/pre-commit install --install-hooks -f
	@echo
	.venv/bin/pre-commit run --all-files

check-deploy:  ## run django checks for deployment settings
	DJANGO_PROD=TRUE \
	DJANGO_ADMIN_PAGE_PATH=secretadminpage \
	DJANGO_SECRET_KEY='^_94mlso&&f5f8wto-wyuaxwq@+0)ra)d^a2!g&byh6es9k739' \
	DJANGO_DB_HOST=foo \
	DJANGO_DB_PASSWORD=bar \
	EMAIL_HOST_PASSWORD=baz \
	.venv/bin/python rezq_backend/manage.py check --deploy --fail-level WARNING

unit-test:  ## run unit tests
	PYTHONPATH=$(PYTHONPATH):rezq_backend:testing \
	.venv/bin/python -m pytest \
	--cov-report term-missing:skip-covered \
	--cov=rezq_backend/ tests/unit

system-test: docker-dev-testing  ## run system tests
	PYTHONPATH=$(PYTHONPATH):rezq_backend:testing \
	.venv/bin/python -m pytest -n 2 tests/system

smoke-test: docker-dev-testing  ## run smoke tests
	PYTHONPATH=$(PYTHONPATH):rezq_backend:testing \
	.venv/bin/python -m pytest -n 2 tests/smoke

test: deps lint check-deploy unit-test smoke-test system-test  ## run all tests

clean-db:  ## clean database
	rm -f rezq_backend/db.sqlite3

clean: clean-db  ## clean artifacts
	rm -f .coverage
	rm -rf rezq_backend/static
	rm -rf .venv
	rm -rf .pytest_cache
	find . -type f -name '*.py[co]' -delete
	find . -type d -name '__pycache__' -delete
	find mock-s3/ ! -name 'mock-resume.pdf' ! -name 'mock-resume-thumbnail.jpg' -type f -delete

secret-key:  ## generate a django secret key
	@python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'

deploy: clean  ## set up the repo for zappa deployment
	virtualenv -p python3 .venv
	.venv/bin/pip install -r requirements.txt
	@echo
	@./scripts/patch-zappa.sh
	@echo
	DJANGO_PROD=TRUE \
	DJANGO_ADMIN_PAGE_PATH=secretadminpage \
	DJANGO_SECRET_KEY='^_94mlso&&f5f8wto-wyuaxwq@+0)ra)d^a2!g&byh6es9k739' \
	DJANGO_DB_HOST=foo \
	DJANGO_DB_PASSWORD=bar \
	EMAIL_HOST_PASSWORD=baz \
	.venv/bin/python rezq_backend/manage.py collectstatic --noinput
