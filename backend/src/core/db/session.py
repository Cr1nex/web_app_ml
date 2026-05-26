from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from core.configs.settings import settings

engine = create_engine(settings.db_url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
