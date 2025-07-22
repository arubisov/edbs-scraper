import logging

from pydantic import EmailStr
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    start_url: str
    url_blacklist: list[str] = [""]
    wix_password: str = ""
    email_to: list[EmailStr] = ["test@test.com"]
    email_from: EmailStr = "test@test.com"
    email_subject: str = ""
    email_body: str = ""
    credentials_file: str = "credentials.json"
    token_file: str = "token.json"
    openai_api_key: str = ""
    openai_model_version: str = "gpt-4o-mini"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# one global instance you import everywhere
settings = Settings()


class LggWrapper:
    def __init__(self, logger):
        self.em = logger.critical  # EMERGENCY (mapped to CRITICAL)
        self.a = logger.critical  # ALERT     (same as critical)
        self.c = logger.critical  # CRITICAL
        self.er = logger.error  # ERROR
        self.w = logger.warning  # WARNING
        self.n = logger.info  # NOTICE (mapped to INFO)
        self.i = logger.info  # INFO
        self.d = logger.debug  # DEBUG


def setup_logger(level=logging.INFO) -> LggWrapper:
    logging.basicConfig(
        level=level, format="[%(levelname)s] %(message)s", handlers=[logging.StreamHandler()]
    )
    return LggWrapper(logging.getLogger())
