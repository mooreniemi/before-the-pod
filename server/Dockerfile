FROM docker:24.0.5-cli

RUN apk add --no-cache python3 py3-pip && pip3 install flask

WORKDIR /app

COPY server/app.py .
COPY deploy/certs /certs

CMD ["python3", "app.py"]
