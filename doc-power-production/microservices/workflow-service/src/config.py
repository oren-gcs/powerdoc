import os
from pydantic_settings import BaseSettings
from pydantic import Field

class Settings(BaseSettings):
    SERVICE_NAME: str = os.getenv("SERVICE_NAME", "service")
    SERVICE_PORT: int = int(os.getenv("SERVICE_PORT", 8000))
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    # Database
    MONGODB_URI: str = os.getenv("MONGODB_URI", "mongodb://root:changeme@mongodb:27017/doc-power?authSource=admin")
    
    # Cache
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://:changeme@redis:6379/0")
    
    # Queue
    RABBITMQ_URL: str = os.getenv("RABBITMQ_URL", "amqp://guest:guest@rabbitmq:5672/")

    class Config:
        # This allows pydantic to load variables from a .env file
        env_file = ".env"
        env_file_encoding = 'utf-8'

settings = Settings()
