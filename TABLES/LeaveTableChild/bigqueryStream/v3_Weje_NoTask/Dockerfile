FROM python:3.10-slim
ENV PYTHONUNBUFFERED True
WORKDIR /app
RUN pip install --upgrade protobuf \
&& pip install gunicorn flask[async] \
&& pip install google-cloud-bigquery-storage \
&& adduser -u 5678 --disabled-password --gecos "" appuser \
&& chown -R appuser .
USER appuser
COPY . ./
CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 0 main:app