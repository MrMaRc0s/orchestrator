FROM debian:12-slim

RUN apt-get update \
    && apt-get install --yes --no-install-recommends \
        python3 \
        python3-psycopg2 \
        python3-pika \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY consumer.py .

CMD ["python3", "consumer.py"]
