FROM python:3.11-slim

# Install just Docker CLI the simple way
RUN apt-get update && \
    apt-get install -y docker.io && \
    rm -rf /var/lib/apt/lists/*

RUN pip install flask

WORKDIR /app

COPY server/app.py .
COPY deploy/certs /certs

EXPOSE 443

CMD ["python", "app.py"]
