from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "School Tutor"
    environment: str = "local"
    database_url: str = "sqlite:///./school_tuter.db"
    auto_create_tables: bool = True
    ncert_base_url: str = "https://www.ncert.nic.in/textbook/pdf"

    llm_provider: str = "stub"
    llm_model: str | None = None
    llm_max_retries: int = 2
    llm_timeout_seconds: int = 120

    groq_api_key: str | None = None
    groq_base_url: str = "https://api.groq.com/openai/v1"
    groq_default_model: str = "llama-3.3-70b-versatile"

    openai_api_key: str | None = None
    openai_base_url: str = "https://api.openai.com/v1"
    openai_default_model: str = "gpt-4o-mini"

    artifact_dir: str = "data/artifacts"
    # "local" (filesystem under artifact_dir) or "gcs" (Cloud Storage bucket).
    # Cloud Run is stateless, so the deployed config uses "gcs".
    artifact_backend: str = "local"
    gcs_bucket: str | None = None
    # Optional key prefix inside the bucket so artifacts don't collide with
    # other content in the same bucket.
    gcs_prefix: str = "artifacts/"

    # Comma-separated origins the SPA can call from. Dev defaults to Vite's
    # localhost; in deploy set ALLOWED_ORIGINS="https://your-app.web.app,https://your-app.firebaseapp.com".
    allowed_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    jwt_secret: str = "dev-insecure-change-me-before-deploying"
    jwt_algorithm: str = "HS256"
    jwt_ttl_minutes: int = 60 * 12
    jwt_issuer: str = "school-tuter"

    anthropic_api_key: str | None = None
    anthropic_default_model: str = "claude-sonnet-4-5"

    # Smart-speaker / voice integration (public device API). A single shared
    # secret gates every /smart-speaker call (sent as the X-API-Key header),
    # and the calling device identifies the learner with X-User-Email. Leave
    # unset to keep the surface disabled (endpoints return 503). This is the
    # least-secure auth model — a leaked key exposes every user whose email is
    # known — so rotate it if it leaks and prefer per-device tokens later.
    smart_speaker_api_key: str | None = None
    # Lifetime of a stateless turn-by-turn test session token (minted at
    # tests/start, replayed on tests/answer). Long enough for one sitting.
    smart_speaker_session_ttl_minutes: int = 240

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def allowed_origins_list(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
