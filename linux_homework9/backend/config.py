from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "sqlite+aiosqlite:///./huaqiang_game.db"
    anthropic_api_key: str = ""
    ai_enabled: bool = False
    app_title: str = "华强卖瓜 — 买瓜宇宙"

    model_config = SettingsConfigDict(env_file=".env", extra="allow")


settings = Settings()
