#!/usr/bin/env python3
"""
Simple database setup script for InterviewIQ
Creates tables if they don't exist
"""

import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

def setup_database():
    """Set up the database by creating tables if they don't exist"""
    
    # Get database URL from environment
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("❌ DATABASE_URL environment variable not set!")
        return False
    
    print(f"🗄️  Setting up database: {database_url}")
    
    try:
        # Create engine
        engine = create_engine(database_url)
        
        # Test connection
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            print("✅ Database connection successful")
        
        # Create tables using SQLAlchemy metadata
        # This will create tables if they don't exist
        print("📋 Creating tables...")
        
        # Import models to register them with SQLAlchemy
        try:
            from app.models.schemas import Base
            Base.metadata.create_all(engine)
            print("✅ Tables created successfully")
        except ImportError as e:
            print(f"⚠️  Could not import models: {e}")
            print("📋 Creating basic tables manually...")
            
            # Create basic tables manually
            with engine.connect() as conn:
                # Create a simple users table as an example
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS users (
                        id SERIAL PRIMARY KEY,
                        email VARCHAR(255) UNIQUE NOT NULL,
                        name VARCHAR(255),
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """))
                
                # Create a simple interviews table
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS interviews (
                        id SERIAL PRIMARY KEY,
                        user_id INTEGER REFERENCES users(id),
                        title VARCHAR(255),
                        status VARCHAR(50) DEFAULT 'draft',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """))
                
                conn.commit()
                print("✅ Basic tables created successfully")
        
        return True
        
    except SQLAlchemyError as e:
        print(f"❌ Database setup failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

if __name__ == "__main__":
    success = setup_database()
    sys.exit(0 if success else 1)
