from sqlalchemy import create_engine
from channel_app.core import settings


class DatabaseService:
    def create_engine(self):
        DATABASE_URL = f"postgresql+psycopg2://{settings.DB_USER}:{settings.DB_PASSWORD}@{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}"
        engine = create_engine(DATABASE_URL, echo=False)
        return engine