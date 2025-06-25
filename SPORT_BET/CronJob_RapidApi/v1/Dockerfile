FROM alpine:3.20
COPY main.sh /main.sh
RUN apk add --no-cache curl && chmod +x /main.sh
ENTRYPOINT ["/main.sh"]