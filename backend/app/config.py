from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "sqlite:///./biofactory.db"
    secret_key: str = "dev-only-change-me"
    access_token_minutes: int = 480
    reset_token_minutes: int = 30
    dev_mode: bool = True
    cors_origins: str = "http://localhost:5173"
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
