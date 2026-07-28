from pydantic_settings import BaseSettings
from pydantic import validator

class Settings(BaseSettings):
    APP_NAME: str = "VSSUT Vibes API"
    VERSION: str = "1.0.0"
    DEBUG: bool = True
    BASE_URL: str = "http://127.0.0.1:8000"

    MONGODB_URI: str
    DATABASE_NAME: str

    SECRET_KEY: str
    ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int

    CLOUDINARY_CLOUD_NAME: str
    CLOUDINARY_API_KEY:    str
    CLOUDINARY_API_SECRET: str

    @validator("SECRET_KEY")
    def secret_key_strength(cls, v):
        if len(v) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters")
        return v

    @validator("BASE_URL")
    def base_url_no_trailing_slash(cls, v):
        return v.rstrip("/")

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()