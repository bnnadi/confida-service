from sqlalchemy import create_engine
from app.database import Base, engine
from app.database.models import User
from app.config import get_settings

def create_tables():
    """Create all database tables."""
    Base.metadata.create_all(bind=engine)
    print("✅ Database tables created successfully")

def drop_tables():
    """Drop all database tables."""
    Base.metadata.drop_all(bind=engine)
    print("✅ Database tables dropped successfully")

def init_database():
    """Initialize database with tables."""
    try:
        create_tables()
        print("Database initialization completed successfully")
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        raise

if __name__ == "__main__":
    init_database()