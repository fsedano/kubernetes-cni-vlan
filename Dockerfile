FROM alpine:3.9
RUN apk add python3
WORKDIR /app
COPY bin/labmon.py /app
ADD bin/bootstrap.sh /app
ENTRYPOINT [ "/bin/sh", "-c", "/app/bootstrap.sh" ]
