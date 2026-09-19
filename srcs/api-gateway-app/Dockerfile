FROM debian:12-slim

RUN apt-get update \
    && apt-get install --yes --no-install-recommends \
        python3 \
        python3-flask \
        python3-requests \
        python3-pika \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY app.py .

EXPOSE 3000
CMD ["python3", "app.py"]
