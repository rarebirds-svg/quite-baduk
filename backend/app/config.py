from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    db_path: str = "./data/baduk.db"
    katago_bin_path: str = "/usr/local/bin/katago"
    katago_model_path: str = "/katago/models/b18c384nbt-humanv0.bin.gz"
    katago_config_path: str = "/katago/config.cfg"
    katago_human_model_path: str = ""  # optional; when set, adapter passes -human-model
    katago_timeout_sec: int = 60
    katago_mock: bool = False
    cors_origins: str = "http://localhost:3000"

    # Ephemeral-session auth
    session_idle_ttl_sec: int = 3600  # 1 hour
    session_purge_interval_sec: int = 60
    cookie_secure: bool = False  # prod should set true
    nickname_min_len: int = 2
    nickname_max_len: int = 32


settings = Settings()
