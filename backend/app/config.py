from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    db_path: str = "./data/baduk.db"
    jwt_secret: str = "dev-secret-change-me"
    jwt_access_ttl_hours: int = 24
    jwt_refresh_ttl_days: int = 30
    bcrypt_cost: int = 12
    katago_bin_path: str = "/usr/local/bin/katago"
    katago_model_path: str = "/katago/models/b18c384nbt-humanv0.bin.gz"
    katago_config_path: str = "/katago/config.cfg"
    katago_timeout_sec: int = 60
    katago_mock: bool = False
    cors_origins: str = "http://localhost:3000"


settings = Settings()
