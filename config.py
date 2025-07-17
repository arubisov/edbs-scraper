from pydantic import EmailStr, HttpUrl
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    start_url: HttpUrl  # your site
    wix_password: str  # login
    email_to: EmailStr  # recipient
    email_from: EmailStr  # sender
    credentials_file: str = "credentials.json"
    token_file: str = "token.json"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# one global instance you import everywhere
settings = Settings()
