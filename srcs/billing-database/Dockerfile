FROM debian:12-slim

ENV PGDATA=/var/lib/postgresql/data \
    PATH="/usr/lib/postgresql/15/bin:$PATH"

RUN apt-get update \
    && apt-get install --yes --no-install-recommends \
        postgresql \
        postgresql-client \
    && rm -rf /var/lib/apt/lists/*

COPY --chmod=755 docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh

EXPOSE 5432
VOLUME ["/var/lib/postgresql/data"]

ENTRYPOINT ["docker-entrypoint.sh"]
CMD ["postgres", "-c", "listen_addresses=*"]
