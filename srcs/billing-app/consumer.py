import json
import os
import time

import pika
import psycopg2

DB_HOST = os.environ.get("BILLING_DB_HOST", "billing-database")
DB_PORT = os.environ.get("BILLING_DB_PORT", "5432")
DB_NAME = os.environ["BILLING_DB_NAME"]
DB_USER = os.environ["BILLING_DB_USER"]
DB_PASSWORD = os.environ["BILLING_DB_PASSWORD"]

RABBITMQ_HOST = os.environ.get("RABBITMQ_HOST", "rabbit-queue")
RABBITMQ_PORT = int(os.environ.get("RABBITMQ_PORT", "5672"))
RABBITMQ_USER = os.environ["RABBITMQ_USER"]
RABBITMQ_PASSWORD = os.environ["RABBITMQ_PASSWORD"]
QUEUE_NAME = os.environ.get("BILLING_QUEUE_NAME", "billing_queue")


def connect_db():
    last_error = None
    for _ in range(30):
        try:
            return psycopg2.connect(
                host=DB_HOST,
                port=DB_PORT,
                dbname=DB_NAME,
                user=DB_USER,
                password=DB_PASSWORD,
            )
        except psycopg2.OperationalError as error:
            last_error = error
            time.sleep(2)
    raise last_error


def init_db(conn):
    with conn, conn.cursor() as cursor:
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS orders (
                id SERIAL PRIMARY KEY,
                payload JSONB NOT NULL,
                received_at TIMESTAMPTZ NOT NULL DEFAULT now()
            )
            """
        )


def connect_queue():
    credentials = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASSWORD)
    parameters = pika.ConnectionParameters(
        host=RABBITMQ_HOST,
        port=RABBITMQ_PORT,
        credentials=credentials,
    )
    last_error = None
    for _ in range(30):
        try:
            return pika.BlockingConnection(parameters)
        except pika.exceptions.AMQPConnectionError as error:
            last_error = error
            time.sleep(2)
    raise last_error


def main():
    db_conn = connect_db()
    init_db(db_conn)

    queue_conn = connect_queue()
    channel = queue_conn.channel()
    channel.queue_declare(queue=QUEUE_NAME, durable=True)
    channel.basic_qos(prefetch_count=1)

    def on_order(channel, method, properties, body):
        order = json.loads(body)
        with db_conn, db_conn.cursor() as cursor:
            cursor.execute(
                "INSERT INTO orders (payload) VALUES (%s)",
                (json.dumps(order),),
            )
        channel.basic_ack(delivery_tag=method.delivery_tag)

    channel.basic_consume(queue=QUEUE_NAME, on_message_callback=on_order)
    channel.start_consuming()


if __name__ == "__main__":
    main()
