"""Application settings. This is the only module that reads environment variables."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import List, Literal, Optional

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]
REPO_DIR = BACKEND_DIR.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(BACKEND_DIR / ".env"), env_file_encoding="utf-8", extra="ignore", case_sensitive=False
    )

    environment: str = "development"
    log_level: str = "INFO"

    # Supabase
    supabase_url: str = ""
    supabase_service_role_key: str = ""
    supabase_jwt_secret: str = ""
    database_url: str = ""

    # How access tokens are verified.
    #   supabase     : supabase-py get_claims (asymmetric keys verified locally via JWKS, HS256 via Supabase Auth)
    #   local_hs256  : verify HS256 tokens locally with SUPABASE_JWT_SECRET (also used by the tests)
    auth_mode: Literal["supabase", "local_hs256"] = "supabase"
    # Where files live. "memory" is for tests and offline development only.
    storage_backend: Literal["supabase", "memory"] = "supabase"
    attachments_bucket: str = "attachments"
    rag_docs_bucket: str = "rag-docs"

    # LLM
    llm_provider: Literal["groq", "gemini", "none"] = "none"
    llm_fallback_provider: Literal["groq", "gemini", "none"] = "none"
    groq_api_key: str = ""
    groq_model: str = ""
    gemini_api_key: str = ""
    gemini_model: str = ""
    llm_timeout_seconds: float = 20.0

    # Only for scripts/seed.py --auth: the password given to the demo Supabase Auth users.
    seed_demo_password: str = ""

    email_provider: Literal["mock", "gmail"] = "mock"

    # Demo controls (simulated insurer, "reset demo"). Off unless asked for, and refused in production.
    demo_mode: bool = False
    # A retention rule is a policy decision, not a fact from this codebase: 5 is a PLACEHOLDER for counsel or the compliance officer.
    retention_years: int = Field(default=5, ge=1, le=50)

    allowed_origins: str = "http://localhost:5173"
    max_upload_bytes: int = 10 * 1024 * 1024
    max_attachments_per_claim: int = 40
    max_attachments_per_request: int = 5
    signed_url_ttl_seconds: int = 600
    assistant_rate_limit_per_min: int = Field(default=10, ge=1)

    # Small pool: Supabase's pooler and free tiers have low connection limits.
    db_pool_min: int = 1
    db_pool_max: int = 8

    @property
    def cors_origins(self) -> List[str]:
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]

    def missing_required(self) -> List[str]:
        """Names of required variables that are unset, given the selected modes."""
        missing: List[str] = []
        if not self.database_url:
            missing.append("DATABASE_URL")
        if self.auth_mode == "supabase":
            if not self.supabase_url:
                missing.append("SUPABASE_URL")
            if not self.supabase_service_role_key:
                missing.append("SUPABASE_SERVICE_ROLE_KEY")
        if self.auth_mode == "local_hs256" and not self.supabase_jwt_secret:
            missing.append("SUPABASE_JWT_SECRET")
        if self.storage_backend == "supabase":
            if not self.supabase_url:
                missing.append("SUPABASE_URL")
            if not self.supabase_service_role_key:
                missing.append("SUPABASE_SERVICE_ROLE_KEY")
        for prov in {self.llm_provider, self.llm_fallback_provider}:
            if prov == "groq":
                if not self.groq_api_key:
                    missing.append("GROQ_API_KEY")
                if not self.groq_model:
                    missing.append("GROQ_MODEL")
            if prov == "gemini":
                if not self.gemini_api_key:
                    missing.append("GEMINI_API_KEY")
                if not self.gemini_model:
                    missing.append("GEMINI_MODEL")
        return sorted(set(missing))

    def config_problems(self) -> List[str]:
        """Values that are set but obviously wrong, each with what to do about it. Checked at startup."""
        problems: List[str] = []
        if self.database_url and not self.database_url.startswith(("postgresql://", "postgres://")):
            problems.append(
                "DATABASE_URL is not a Postgres connection string (it must start with postgresql://). "
                "An https://…supabase.co URL is the REST API address, not the database."
            )
        key = self.supabase_service_role_key
        if key.startswith("sb_publishable_"):
            problems.append(
                "SUPABASE_SERVICE_ROLE_KEY holds a publishable key (sb_publishable_…), which cannot create users, "
                "store files or bypass access rules. Use the project's secret key (sb_secret_…) or legacy service_role key."
            )
        if "groq" in {self.llm_provider, self.llm_fallback_provider} and self.groq_api_key.startswith("xai-"):
            problems.append("GROQ_API_KEY looks like an xAI (Grok) key (xai-…). Groq and xAI are different companies; get a Groq key (gsk_…).")
        return problems

    @model_validator(mode="after")
    def _sanity(self) -> "Settings":
        if self.email_provider == "gmail":
            raise ValueError("EMAIL_PROVIDER=gmail is reserved and not built; use 'mock'.")
        if self.demo_mode and self.environment.lower() in ("production", "prod"):
            raise ValueError("DEMO_MODE must be off when ENVIRONMENT=production: it enables a data reset and a simulated insurer.")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()


def validate_settings(settings: Optional[Settings] = None) -> Settings:
    """Fail fast, naming every missing variable."""
    s = settings or get_settings()
    missing = s.missing_required()
    problems = s.config_problems()
    if missing or problems:
        lines = []
        if missing:
            lines.append("Missing required environment variable(s): " + ", ".join(missing))
        lines += [f"Invalid value: {p}" for p in problems]
        raise RuntimeError("\n".join(lines))
    return s
