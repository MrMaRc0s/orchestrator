import logging
from pathlib import Path

from app import create_app
from app.config.settings import load_settings


LOGGER = logging.getLogger(__name__)
LOG_DIRECTORY = Path("/app/logs")


def main() -> None:
    LOG_DIRECTORY.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(LOG_DIRECTORY / "gateway.log"),
        ],
    )

    settings = load_settings()
    app = create_app(settings)

    LOGGER.info("API Gateway is listening on port %s", settings.gateway_port)
    app.run(host="0.0.0.0", port=settings.gateway_port)


if __name__ == "__main__":
    main()
