FROM alpine:3.9
RUN apk add python3
WORKDIR /app
ADD bin/requirements.txt /app
RUN pip3 install -r requirements.txt
COPY bin/labmon_cni.py /app
ADD bin/bootstrap.sh /app
ENTRYPOINT [ "/bin/sh", "-c", "/app/bootstrap.sh" ]
