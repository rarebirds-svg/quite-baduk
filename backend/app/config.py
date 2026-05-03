from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Deployment env. "production" turns on stricter defaults
    # (Secure cookies, HSTS, etc.).
    app_env: str = "development"

    db_path: str = "./data/baduk.db"
    katago_bin_path: str = "/usr/local/bin/katago"
    katago_model_path: str = "/katago/models/b18c384nbt-humanv0.bin.gz"
    katago_config_path: str = "/katago/config.cfg"
    katago_human_model_path: str = ""  # optional; when set, adapter passes -human-model
    katago_timeout_sec: int = 60
    katago_mock: bool = False
    # Worker pool size. With Metal on M4, 4 concurrent KataGo subprocesses
    # share one GPU comfortably; raise after profiling if you ever see all
    # four queues backed up at peak. 1 is fine for tests/dev.
    katago_pool_size: int = 4
    cors_origins: str = "http://localhost:3000"

    # Ephemeral-session auth
    session_idle_ttl_sec: int = 3600  # 1 hour
    session_purge_interval_sec: int = 60
    # When unset, cookie_secure is True in production and False otherwise.
    # Explicit `COOKIE_SECURE=true|false` always wins.
    cookie_secure_override: bool | None = None
    nickname_min_len: int = 2
    nickname_max_len: int = 32

    # When True, trust the ``CF-Connecting-IP`` header for client IP
    # identification (rate limiting, audit logging). Set this only when the
    # FastAPI process is reachable exclusively through Cloudflare (e.g. via
    # cloudflared tunnel) — otherwise a client can spoof the header.
    # ``X-Forwarded-For`` is never trusted: it is too easy for clients to set.
    cf_trusted_proxy: bool = False

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() == "production"

    @property
    def cookie_secure(self) -> bool:
        if self.cookie_secure_override is not None:
            return self.cookie_secure_override
        return self.is_production


settings = Settings()
