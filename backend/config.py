from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List
import json
import base64


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Gemini
    gemini_api_key: str = ""
    # gemini-2.0-flash free tier is zeroed out (limit:0). 2.5-flash works on this key.
    gemini_model: str = "gemini-2.5-flash"
    # Set false to skip all Gemini calls and use heuristic fallbacks (fast dev/testing,
    # zero quota burn). Flip to true (or just drop in a fresh key) to re-enable real AI.
    gemini_enabled: bool = True

    # Google OAuth (Calendar + Gmail)
    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "http://localhost:8000/auth/callback"

    # Firebase
    firebase_project_id: str = ""
    firebase_service_account_json: str = ""  # base64-encoded JSON service account key
    firebase_web_api_key: str = ""

    # Google Speech-to-Text
    google_speech_api_key: str = ""

    # Cloud SQL
    database_url: str = "postgresql+asyncpg://postgres:password@localhost:5432/lifesaver"

    # Cloud Storage
    gcs_bucket_name: str = ""
    gcp_project_id: str = ""

    # App
    cors_origins: List[str] = ["http://localhost:3000", "http://localhost:3001"]
    secret_key: str = "dev-secret-key-change-in-production"
    debug: bool = False
    internal_api_secret: str = "internal-secret-for-scheduler"
    # When true, a Bearer token of "dev" (or no token) maps to a fixed local dev user.
    # For local testing only — never enable in production.
    dev_auth_bypass: bool = False
    dev_user_email: str = "dev@lifesaver.local"

    @property
    def firebase_service_account_dict(self) -> dict:
        if not self.firebase_service_account_json:
            return {}
        try:
            decoded = base64.b64decode(self.firebase_service_account_json).decode("utf-8")
            return json.loads(decoded)
        except Exception:
            return {}


settings = Settings()