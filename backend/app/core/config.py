from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://cascadeiq:cascadeiq_dev@localhost:5432/cascadeiq"
    OPENWEATHER_API_KEY: str = "demo"
    GROQ_API_KEY: str = "demo"
    SECRET_KEY: str = "dev_secret_key"
    DEBUG: bool = True
    FRONTEND_URL: str = "http://localhost:3000"

    class Config:
        env_file = ".env"
        extra = "allow"


settings = Settings()
