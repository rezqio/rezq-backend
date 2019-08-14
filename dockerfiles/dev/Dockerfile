FROM python:3.6.1

ENV PYTHONUNBUFFERED=1

ADD requirements.txt /tmp/requirements.txt

RUN pip install -r /tmp/requirements.txt
RUN pip install django_extensions

ADD mock-s3/mock-resume.pdf /mock-s3/mock-resume.pdf
ADD mock-s3/mock-resume-thumbnail.jpg /mock-s3/mock-resume-thumbnail.jpg

ADD rezq_backend/ /opt/rezq_backend/
RUN rm -rf /opt/rezq_backend/mock-s3

RUN python /opt/rezq_backend/manage.py makemigrations rezq
RUN python /opt/rezq_backend/manage.py migrate

ADD fixtures/ /tmp/fixtures/
RUN python /opt/rezq_backend/manage.py loaddata /tmp/fixtures/dev.json

CMD python /opt/rezq_backend/manage.py runserver_plus 0.0.0.0:80 \
  >> /var/log/backend.log 2>&1
