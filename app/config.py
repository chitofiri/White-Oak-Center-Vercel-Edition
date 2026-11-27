from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class Settings(BaseSettings):
    app_name: str = "White Oak Center Portal"
    environment: str = "development"
    database_url: str = "sqlite:///./whiteoak_dev.db"
    jwt_secret: str = Field(min_length=32)
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 20
    max_pdf_mb: int = 3
    private_upload_dir: str = "./private_uploads"
    bootstrap_admin_email: str | None = None
    bootstrap_admin_password: str | None = None
    s3_bucket: str | None = None
    s3_endpoint_url: str | None = None
    s3_region: str = "auto"
    s3_access_key_id: str | None = None
    s3_secret_access_key: str | None = None
    ollama_base_url: str = "http://127.0.0.1:11434"
    ollama_model: str = "llama3.2:3b"
    ollama_timeout_seconds: int = 90

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
