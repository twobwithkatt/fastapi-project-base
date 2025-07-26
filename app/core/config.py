import os
from dotenv import load_dotenv
from pydantic_settings import BaseSettings
from sqlalchemy.engine import URL
import urllib.parse


import os
from pydantic_settings import BaseSettings
from sqlalchemy.engine import URL


BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../'))


class Settings(BaseSettings):
    POSTGRES_USER: str = 'postgres'
    POSTGRES_PASSWORD: str = 'postgres'
    POSTGRES_DB: str = 'postgres'
    POSTGRES_HOST: str = 'localhost'
    POSTGRES_PORT: int = 5432

    REDIS_HOST: str = 'localhost'
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: str = ''

    HOST: str = 'localhost'
    PORT: int = 8002

    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = 'HS256'
    JWT_EXPIRE_MINUTES: int = 60 * 24 * 1
    ADMIN_PASSWORD: str 
    
    
    class Config:
        env_file = os.path.join(BASE_DIR, '.env')
        env_file_encoding = 'utf-8'


settings = Settings()

def build_db_url() -> URL:
    return URL.create(
        drivername='postgresql+psycopg2',
        username=settings.POSTGRES_USER,
        password=settings.POSTGRES_PASSWORD,
        host=settings.POSTGRES_HOST,
        port=settings.POSTGRES_PORT,
        database=settings.POSTGRES_DB,
    )
