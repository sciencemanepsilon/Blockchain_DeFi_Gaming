FROM python:3.11-slim
ENV PYTHONUNBUFFERED True
WORKDIR /app
RUN pip install gunicorn flask \
&& pip install requests \
&& pip install cachetools \
&& adduser -u 5678 --disabled-password --gecos "" appuser \
&& chown -R appuser .
USER appuser
COPY . ./
CMD exec gunicorn --bind :8080 --workers 1 --threads 1 --timeout 0 main:app
