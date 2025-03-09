FROM python:3.11-slim
ENV PYTHONUNBUFFERED True
WORKDIR /app
RUN pip install fastapi==0.105.0 \
&& pip install uvicorn==0.27.1 \
&& pip install httpx \
&& pip install --upgrade google-cloud-tasks \
&& adduser -u 5678 --disabled-password --gecos "" appuser \
&& chown -R appuser .
USER appuser
COPY . ./
CMD uvicorn main:app --host 0.0.0.0 --port 8080