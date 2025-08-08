import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base

# Get database URL from environment variable or use default
DATABASE_URL = os.getenv('DATABASE_URL')

if not DATABASE_URL:
    raise RuntimeError('DATABASE_URL environment variable is not set. Please configure it (see .env.example).')

# Single database engine and session factory for the entire app
engine = create_engine(DATABASE_URL, echo=True)
SessionLocal = sessionmaker(bind=engine)

def get_db_session():
    """Get a database session with proper cleanup"""
    return SessionLocal()
