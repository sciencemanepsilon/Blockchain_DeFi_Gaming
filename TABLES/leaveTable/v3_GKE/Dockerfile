FROM python:3.10-slim
ENV PYTHONUNBUFFERED=True
WORKDIR /app
RUN pip install fastapi \
&& pip install uvicorn \
&& pip install httpx \
&& pip install --upgrade google-cloud-pubsub \
&& adduser -u 5678 --disabled-password --gecos "" appuser \
&& chown -R appuser .
USER appuser
COPY . ./
ENTRYPOINT ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]