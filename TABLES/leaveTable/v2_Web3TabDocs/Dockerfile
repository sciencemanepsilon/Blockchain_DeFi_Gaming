FROM python:3.10-slim
ENV PYTHONUNBUFFERED True
WORKDIR /app
RUN pip install gunicorn flask[async] \
&& pip install httpx \
&& pip install --upgrade google-auth \
&& pip install --upgrade google-cloud-pubsub \
&& adduser -u 5678 --disabled-password --gecos "" appuser \
&& chown -R appuser .
USER appuser
COPY . ./
CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 0 main:app