FROM node:20-slim
WORKDIR /usr/src/app
COPY package*.json ./
RUN npm install \
&& adduser -u 5678 --disabled-password --gecos "" appuser \
&& chown -R appuser .
USER appuser
COPY . ./
ENTRYPOINT ["npm", "run", "dev"];