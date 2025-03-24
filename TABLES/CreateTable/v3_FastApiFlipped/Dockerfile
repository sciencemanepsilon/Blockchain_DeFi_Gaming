FROM python:3.10-slim
ENV PYTHONUNBUFFERED True
WORKDIR /app
RUN pip install fastapi \
&& pip install uvicorn \
&& pip install firebase-admin \
&& adduser -u 5678 --disabled-password --gecos "" appuser \
&& chown -R appuser .
USER appuser
COPY . ./
CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 0 wsgi:app