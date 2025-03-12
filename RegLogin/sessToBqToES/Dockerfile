FROM python:3.10-slim
ENV PYTHONUNBUFFERED True
WORKDIR /app
RUN pip install gunicorn flask[async] \
&& pip install requests \
&& pip install elasticsearch \
&& pip install --upgrade google-cloud-bigquery \
&& adduser -u 5678 --disabled-password --gecos "" appuser \
&& chown -R appuser .
USER appuser
COPY . ./
CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 0 wsgi:app