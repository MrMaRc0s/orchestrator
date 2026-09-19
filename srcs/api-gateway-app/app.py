import json
import os

import pika
import requests
from flask import Flask, Response, jsonify, request

INVENTORY_APP_URL = os.environ.get("INVENTORY_APP_URL", "http://inventory-app:8080")

RABBITMQ_HOST = os.environ.get("RABBITMQ_HOST", "rabbit-queue")
RABBITMQ_PORT = int(os.environ.get("RABBITMQ_PORT", "5672"))
RABBITMQ_USER = os.environ["RABBITMQ_USER"]
RABBITMQ_PASSWORD = os.environ["RABBITMQ_PASSWORD"]
QUEUE_NAME = os.environ.get("BILLING_QUEUE_NAME", "billing_queue")

app = Flask(__name__)


def publish_order(order):
    credentials = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASSWORD)
    parameters = pika.ConnectionParameters(
        host=RABBITMQ_HOST,
        port=RABBITMQ_PORT,
        credentials=credentials,
    )
    connection = pika.BlockingConnection(parameters)
    try:
        channel = connection.channel()
        channel.queue_declare(queue=QUEUE_NAME, durable=True)
        channel.basic_publish(
            exchange="",
            routing_key=QUEUE_NAME,
            body=json.dumps(order),
            properties=pika.BasicProperties(delivery_mode=2),
        )
    finally:
        connection.close()


@app.get("/healthz")
def healthz():
    return jsonify(status="ok")


@app.get("/movies")
def list_movies():
    upstream = requests.get(f"{INVENTORY_APP_URL}/movies", timeout=5)
    return Response(upstream.content, upstream.status_code, content_type="application/json")


@app.post("/movies")
def create_movie():
    upstream = requests.post(
        f"{INVENTORY_APP_URL}/movies",
        json=request.get_json(silent=True) or {},
        timeout=5,
    )
    return Response(upstream.content, upstream.status_code, content_type="application/json")


@app.post("/billing")
def create_order():
    order = request.get_json(silent=True)
    if not order:
        return jsonify(error="a JSON order body is required"), 400

    # Publishing straight to RabbitMQ decouples this from billing-app,
    # so the gateway still answers while the consumer is scaled to 0.
    publish_order(order)
    return jsonify(status="queued"), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000)
