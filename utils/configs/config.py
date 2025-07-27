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


settings = Settings()
