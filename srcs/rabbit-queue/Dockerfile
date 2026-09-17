FROM debian:12-slim

ENV RABBITMQ_LOGS=- \
    RABBITMQ_SASL_LOGS=-

RUN apt-get update \
    && apt-get install --yes --no-install-recommends rabbitmq-server \
    && rabbitmq-plugins --offline enable rabbitmq_management \
    && rm -rf /var/lib/apt/lists/*

EXPOSE 5672 15672

USER rabbitmq

CMD ["rabbitmq-server"]
