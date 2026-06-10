from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "FICCT Diagramador API"
    app_env: str = "development"
    app_debug: bool = True
    api_prefix: str = "/api"
    protected_admin_email: str = "administrador@acb.com"
    protected_admin_password: str = "123ppp+++"
    protected_admin_full_name: str = "Administrador ACB"
    protected_admin_phone: str = "70000000"
    workshop_initial_password: str = "acb123*"
    base_url_ai: str = "http://34.122.37.25:8010"
    ai_service_timeout_seconds: int = 10

    postgres_db: str = "diagramador"
    postgres_user: str = "diagramador"
    postgres_password: str = "diagramador"
    postgres_host: str = "db"
    postgres_port: int = 5432
    postgres_connect_timeout: int = 5
    ms_ia_multimedia_url: str = "http://ms-ia-multimedia:8080"
    ms_ia_timeout_seconds: int = 10
    rabbitmq_url: str = "amqp://guest:guest@rabbitmq:5672/"
    rabbitmq_analysis_queue: str = "emergency.analysis.requested"
    uploads_dir: str = "uploads"
    whisper_enabled: bool = True
    whisper_model: str = "base"
    whisper_language: str | None = "es"
    photo_classification_enabled: bool = False
    photo_classification_model: str = "gpt-5-mini"
    fcm_enabled: bool = False
    firebase_credentials_path: str | None = None
    jwt_secret: str = "change-this-jwt-secret-in-production"
    jwt_access_expires_minutes: int = 480
    jwt_issuer: str = "ficct-core-backend"
    password_reset_token_expires_minutes: int = 15

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+psycopg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


settings = Settings()
