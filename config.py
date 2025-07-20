from pydantic import EmailStr
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    start_url: str = ""
    url_blacklist: list[str] = [""]
    wix_password: str = ""
    email_to: EmailStr = "test@test.com"
    email_from: EmailStr = "test@test.com"
    email_subject: str = ""
    email_body: str = ""
    credentials_file: str = "credentials.json"
    token_file: str = "token.json"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# one global instance you import everywhere
settings = Settings()
