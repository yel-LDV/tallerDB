from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)

    database_url: str
    secret_key: str
    session_cookie_name: str = "session"
    app_name: str = "TallerDB"
    debug: bool = True

    # Admin user (creado automaticamente al iniciar)
    admin_email: str = "admin@tallerdb.local"
    admin_password: str = "admin123"


settings = Settings()