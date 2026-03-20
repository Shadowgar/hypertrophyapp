from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_host: str = "localhost"
    database_port: int = 5432
    database_name: str = "hypertrophy"
    database_user: str = "hypertrophy"
    database_password: str = "change_me"
    database_url: str | None = None
    jwt_secret: str = "change_me"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 1440
    programs_dir: str = "/app/programs"
    compiled_knowledge_dir: str = "/app/knowledge/compiled"
    allow_dev_wipe_endpoints: bool = True

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def resolved_database_url(self) -> str:
        if self.database_url:
            return self.database_url
        return (
            "postgresql+psycopg://"
            f"{self.database_user}:{self.database_password}@"
            f"{self.database_host}:{self.database_port}/{self.database_name}"
        )


settings = Settings()
