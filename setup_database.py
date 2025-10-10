#!/usr/bin/env python3
"""
Database setup script for InterviewIQ.
This script will create the database and run initial migrations.
"""

import os
import sys
from sqlalchemy import create_engine, text
from app.database import Base, engine
from app.config import get_settings

def create_database():
    """Create the database if it doesn't exist."""
    settings = get_settings()
    
    # Extract database name from URL
    db_url = settings.DATABASE_URL
    if db_url.startswith("postgresql://"):
        # For PostgreSQL, we need to connect to the default database first
        base_url = db_url.rsplit('/', 1)[0] + '/postgres'
        db_name = db_url.split('/')[-1]
        
        try:
            # Connect to PostgreSQL server
            engine_temp = create_engine(base_url)
            with engine_temp.connect() as conn:
                # Check if database exists
                result = conn.execute(text(f"SELECT 1 FROM pg_database WHERE datname = '{db_name}'"))
                if not result.fetchone():
                    # Create database
                    conn.execute(text(f"CREATE DATABASE {db_name}"))
                    print(f"✅ Database '{db_name}' created successfully")
                else:
                    print(f"✅ Database '{db_name}' already exists")
        except Exception as e:
            print(f"❌ Error creating database: {e}")
            print("💡 Make sure PostgreSQL is running and accessible")
            print("   macOS: brew services start postgresql")
            print("   Linux: sudo systemctl start postgresql")
            return False
    else:
        print(f"ℹ️  Using non-PostgreSQL database: {db_url}")
    
    return True

def run_migrations():
    """Run database migrations."""
    try:
        # Create all tables
        Base.metadata.create_all(bind=engine)
        print("✅ Database tables created successfully")
        return True
    except Exception as e:
        print(f"❌ Error running migrations: {e}")
        return False

def main():
    """Main setup function."""
    print("🚀 Setting up InterviewIQ database...")
    print("📋 Default configuration: PostgreSQL for development")
    print("   Database: interviewiq_dev")
    print("   User: interviewiq_dev")
    print("   Password: dev_password")
    print()
    
    # Create database
    if not create_database():
        print("❌ Database setup failed")
        print("\n💡 Troubleshooting:")
        print("1. Make sure PostgreSQL is installed and running")
        print("2. Check if the database user exists")
        print("3. Verify connection permissions")
        print("4. Run: python setup_dev_database.py for automated setup")
        sys.exit(1)
    
    # Run migrations
    if not run_migrations():
        print("❌ Migration setup failed")
        sys.exit(1)
    
    print("✅ Database setup completed successfully!")
    print("\nNext steps:")
    print("1. Run: alembic revision --autogenerate -m 'Initial migration'")
    print("2. Run: alembic upgrade head")
    print("3. Run: uvicorn app.main:app --reload")
    print("\n🎉 Your development environment is ready!")

if __name__ == "__main__":
    main()
