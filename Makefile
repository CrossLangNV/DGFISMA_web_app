
SHELL=/bin/bash

.PHONY: up
up:
	docker-compose up -d

.PHONY: down
down:
	docker-compose down

.PHONY: psql
psql:
	docker-compose exec postgres psql $$(grep POSTGRES_DB secrets/django-docker.env | sed -e 's/.*=//') $$(grep POSTGRES_USER secrets/django-docker.env | sed -e 's/.*=//')

.PHONY: make-migrations
make-migrations:
	docker-compose exec django python manage.py makemigrations -v 3

.PHONY: migrate
migrate:
	docker-compose exec django python manage.py migrate
