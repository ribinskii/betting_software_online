import logging
import sys
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    DB_USER: str
    DB_PASSWORD: str
    DB_HOST: str
    DB_PORT: int
    DB_NAME: str

    REDIS_HOST: str
    REDIS_PORT: int

    RABBIT_HOST: str
    RABBIT_PORT: int
    RABBIT_USER: str
    RABBIT_PASSWORD: str

    LOG_LEVEL: str

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env"
    )

    @property
    def get_db_url(self):
        return (f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASSWORD}@"
                f"{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}")

    @property
    def get_redis_url(self):
        return (f"redis://{self.REDIS_HOST}")

    @property
    def get_rabbitmq_url(self):
        return (f"amqp://{self.RABBIT_USER}:{self.RABBIT_PASSWORD}@"
                f"{self.RABBIT_HOST}:{self.RABBIT_PORT}/")



def setup_logging(log_level) -> None:
    logging.basicConfig(
        level=log_level.upper(),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
        ],
    )

    logger = logging.getLogger(__name__)
    logger.debug("Debug level log message")
    logger.info("Info level log message")
    logger.warning("Warning level log message")
    logger.error("Error level log message")
    logger.critical("Critical level log message")




settings = Settings()


