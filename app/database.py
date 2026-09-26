from sqlalchemy import create_engine
from sqlalchemy.engine import URL
from sqlalchemy.orm import declarative_base, sessionmaker

from .config import settings

database_url = (
    URL.create(
        "mysql+pymysql",
        username=settings.database_user,
        password=settings.database_password,
        host=settings.database_host,
        port=settings.database_port,
        database=settings.database_name,
    )
    if settings.database_host
    else settings.database_url
)

engine = create_engine(
    database_url,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
