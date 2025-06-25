FROM python:3.11-slim
ENV PYTHONUNBUFFERED True
WORKDIR /app
#RUN pip install google-cloud-container \
#&& pip install --upgrade google-auth \
RUN pip install --upgrade google-cloud-pubsub \
&& pip install firebase-admin \
&& adduser -u 5678 --disabled-password --gecos "" appuser \
&& chown -R appuser .
USER appuser
COPY . ./
ENTRYPOINT ["python", "main.py"]