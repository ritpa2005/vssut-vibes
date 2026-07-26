from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    APP_NAME: str = "VSSUT Vibes API"
    VERSION: str = "1.0.0"
    DEBUG: bool = True
    
    MONGODB_URI: str 
    DATABASE_NAME: str 
    
    SECRET_KEY: str 
    ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int 

    CLOUDINARY_CLOUD_NAME: str
    CLOUDINARY_API_KEY:    str
    CLOUDINARY_API_SECRET: str
    BASE_URL:              str = "http://127.0.0.1:8000"
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()