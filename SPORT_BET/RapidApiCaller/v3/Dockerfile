FROM python:3.11-slim
ENV PYTHONUNBUFFERED=True
WORKDIR /app
RUN pip install fastapi==0.110.0 \
&& pip install uvicorn==0.30.0 \
&& pip install cachetools \
&& pip install httpx \
&& adduser -u 5678 --disabled-password --gecos "" appuser \
&& chown -R appuser .
USER appuser
COPY . ./
ENTRYPOINT ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]