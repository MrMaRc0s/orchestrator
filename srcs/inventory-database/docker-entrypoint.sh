#!/bin/sh
set -eu

if [ "$1" = "postgres" ]; then
    : "${POSTGRES_DB:?POSTGRES_DB is required}"
    : "${POSTGRES_USER:?POSTGRES_USER is required}"
    : "${POSTGRES_PASSWORD:?POSTGRES_PASSWORD is required}"

    mkdir -p "$PGDATA" /var/run/postgresql
    chown -R postgres:postgres "$PGDATA" /var/run/postgresql
    chmod 700 "$PGDATA"

    if [ ! -s "$PGDATA/PG_VERSION" ]; then
        runuser -u postgres -- initdb \
            --pgdata="$PGDATA" \
            --username=postgres \
            --encoding=UTF8 \
            --locale=C \
            --auth-local=trust \
            --auth-host=scram-sha-256

        runuser -u postgres -- pg_ctl \
            --pgdata="$PGDATA" \
            --options="-c listen_addresses=''" \
            --wait start

        runuser -u postgres -- psql \
            --set=ON_ERROR_STOP=1 \
            --set=db_name="$POSTGRES_DB" \
            --set=db_user="$POSTGRES_USER" \
            --set=db_password="$POSTGRES_PASSWORD" \
            --username=postgres \
            --dbname=postgres <<-'SQL'
		CREATE USER :"db_user" WITH PASSWORD :'db_password';
		CREATE DATABASE :"db_name" OWNER :"db_user";
	SQL

        runuser -u postgres -- pg_ctl \
            --pgdata="$PGDATA" \
            --mode=fast \
            --wait stop
    fi

    if ! grep -Fxq 'host all all all scram-sha-256' "$PGDATA/pg_hba.conf"; then
        printf '%s\n' 'host all all all scram-sha-256' >> "$PGDATA/pg_hba.conf"
    fi

    exec runuser -u postgres -- "$@"
fi

exec "$@"
