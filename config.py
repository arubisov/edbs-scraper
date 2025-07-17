from pydantic import EmailStr, HttpUrl
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    start_url: HttpUrl
    wix_password: str
    email_to: EmailStr
    email_from: EmailStr
    email_subject: str
    email_body: str
    credentials_file: str = "credentials.json"
    token_file: str = "token.json"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# one global instance you import everywhere
settings = Settings()
