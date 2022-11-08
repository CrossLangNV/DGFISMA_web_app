#!/bin/bash

git submodule update --init

cp secrets/django-docker.env.sample secrets/django-docker.env

docker-compose up -d

# Setup Solr
docker run --rm --network host jwilder/dockerize -wait http://localhost:8983 -timeout 60s
exit_code=$?
if [ $exit_code -ne 0 ]; then
  echo "Error"
  exit
fi
sleep 10
cd solr; ./fields.sh; cd ..

# Setup admin user
DJANGO_ADMIN_USERNAME=admin
DJANGO_ADMIN_PASSWORD=admin
DJANGO_ADMIN_EMAIL=nobody@crosslang.com
echo "from django.contrib.auth.models import User; User.objects.create_superuser('$DJANGO_ADMIN_USERNAME', '$DJANGO_ADMIN_EMAIL', '$DJANGO_ADMIN_PASSWORD')" | docker-compose exec -T django python manage.py shell

# Setup credentials for frontend
ANGULAR_DJANGO_CLIENT_ID=$(grep ANGULAR_DJANGO_CLIENT_ID secrets/django-docker.env | sed -e 's/.*=//')
ANGULAR_DJANGO_CLIENT_SECRET=$(grep ANGULAR_DJANGO_CLIENT_SECRET secrets/django-docker.env | sed -e 's/.*=//')
docker-compose exec django python manage.py createapplication --name searchapp confidential password --client-id $ANGULAR_DJANGO_CLIENT_ID --client-secret $ANGULAR_DJANGO_CLIENT_SECRET

# Load data
docker-compose exec django python manage.py loaddata websites

# Now run the scraper
echo "INSTALLATION COMPLETE"
echo "---------------------"
echo "login at http://localhost:8000 ($DJANGO_ADMIN_USERNAME:$DJANGO_ADMIN_PASSWORD)"
echo ""
echo "You may now fetch some data:"
echo "(crawls 500 pages from EURLEX year 2020)"
echo ""
echo "docker-compose exec django scrapy crawl -s CLOSESPIDER_ITEMCOUNT=500 -a year=2020 -L INFO eurlex"
