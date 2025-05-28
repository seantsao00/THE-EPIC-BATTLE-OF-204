from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    openai_api_key: str = ""
    dns_ip: str = "127.0.0.1"
    dns_port: int = 5353
    api_ip: str = "127.0.0.1"
    api_port: int = 8000
    secret_key: str = "placeholder_secret_key"
    sqlalchemy_database_url: str = "sqlite:///./firewall.db"
    clam_url: str = "cool.ntu.edu.tw"

    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()
