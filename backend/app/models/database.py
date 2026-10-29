import os
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

logger = logging.getLogger("visionguard.database")

# Fetch DATABASE_URL from environment or fallback to local SQLite for seamless setup
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./visionguard.db")

# Force sqlite fallback if PostgreSQL connects fail or if sqlite is specified
def get_engine(db_url: str):
    if db_url.startswith("sqlite"):
        return create_engine(db_url, connect_args={"check_same_thread": False})
    try:
        engine = create_engine(db_url, pool_pre_ping=True)
        # Test connection
        with engine.connect() as conn:
            pass
        logger.info(f"Connected to database: {db_url.split('@')[-1]}")
        return engine
    except Exception as e:
        logger.warning(f"Could not connect to PostgreSQL ({e}). Falling back to SQLite database.")
        sqlite_url = "sqlite:///./visionguard.db"
        return create_engine(sqlite_url, connect_args={"check_same_thread": False})

engine = get_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    Base.metadata.create_all(bind=engine)
