import os
import time

import psycopg2
from flask import Flask, jsonify, request

DB_HOST = os.environ.get("INVENTORY_DB_HOST", "inventory-database")
DB_PORT = os.environ.get("INVENTORY_DB_PORT", "5432")
DB_NAME = os.environ["INVENTORY_DB_NAME"]
DB_USER = os.environ["INVENTORY_DB_USER"]
DB_PASSWORD = os.environ["INVENTORY_DB_PASSWORD"]

app = Flask(__name__)


def connect():
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


def init_db():
    conn = connect()
    try:
        with conn, conn.cursor() as cursor:
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS movies (
                    id SERIAL PRIMARY KEY,
                    title TEXT NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
                )
                """
            )
    finally:
        conn.close()


@app.get("/healthz")
def healthz():
    return jsonify(status="ok")


@app.get("/movies")
def list_movies():
    conn = connect()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT id, title, created_at FROM movies ORDER BY id")
            rows = cursor.fetchall()
    finally:
        conn.close()
    return jsonify(
        [
            {"id": row[0], "title": row[1], "created_at": row[2].isoformat()}
            for row in rows
        ]
    )


@app.post("/movies")
def create_movie():
    payload = request.get_json(silent=True) or {}
    title = payload.get("title")
    if not title:
        return jsonify(error="title is required"), 400

    conn = connect()
    try:
        with conn, conn.cursor() as cursor:
            cursor.execute(
                "INSERT INTO movies (title) VALUES (%s) RETURNING id, created_at",
                (title,),
            )
            movie_id, created_at = cursor.fetchone()
    finally:
        conn.close()
    return jsonify(id=movie_id, title=title, created_at=created_at.isoformat()), 201


if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=8080)
