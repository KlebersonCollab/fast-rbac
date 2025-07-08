import logging
import os
import sqlite3
from typing import Generator

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import Session, declarative_base, sessionmaker
from sqlalchemy.pool import StaticPool

from app.config.settings import settings

logger = logging.getLogger(__name__)


# Engine configuration based on database type
def get_engine_config():
    """Get database engine configuration based on database type"""
    config = {
        "echo": settings.debug,
        "future": True,
    }

    if settings.database_type == "postgresql":
        # PostgreSQL optimizations
        config.update(
            {
                "pool_size": 10,
                "max_overflow": 20,
                "pool_pre_ping": True,
                "pool_recycle": 3600,  # 1 hour
            }
        )
    elif settings.database_type == "sqlite":
        # SQLite specific configurations
        config.update(
            {
                "connect_args": {
                    "check_same_thread": False,
                    "timeout": 30,
                },
                "poolclass": StaticPool,
            }
        )

    return config


# Create SQLAlchemy engine with optimized settings
engine = create_engine(settings.database_url, **get_engine_config())

# Configure SQLite for better performance and concurrency
if settings.database_type == "sqlite":

    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        """Set SQLite pragmas for better performance"""
        cursor = dbapi_connection.cursor()

        # Performance optimizations
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.execute("PRAGMA cache_size=10000")
        cursor.execute("PRAGMA temp_store=MEMORY")
        cursor.execute("PRAGMA mmap_size=268435456")  # 256MB

        # Foreign key constraints
        cursor.execute("PRAGMA foreign_keys=ON")

        cursor.close()


# Create session factory with optimized settings
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    expire_on_commit=False,  # Keep objects alive after commit
)

# Create base class for models
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """Dependency to get database session with proper error handling"""
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        logger.error(f"Database session error: {e}")
        db.rollback()
        raise
    finally:
        db.close()


def create_tables():
    """Create all database tables"""
    try:
        logger.info(f"Creating tables for {settings.database_type} database...")
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Error creating database tables: {e}")
        raise


def check_database_connection():
    """Check if database connection is working"""
    try:
        with engine.connect() as conn:
            # Use text() for raw SQL in SQLAlchemy 2.0+
            result = conn.execute(text("SELECT 1"))
            result.fetchone()
        logger.info(f"Database connection successful ({settings.database_type})")
        return True
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        return False


def get_database_info():
    """Get database information for monitoring"""
    info = {
        "type": settings.database_type,
        "url": (
            settings.database_url.split("@")[-1]
            if "@" in settings.database_url
            else settings.database_url
        ),
        "pool_size": getattr(engine.pool, "size", "N/A"),
        "checked_out": getattr(engine.pool, "checkedout", "N/A"),
        "overflow": getattr(engine.pool, "overflow", "N/A"),
        "is_connected": check_database_connection(),
    }
    return info
