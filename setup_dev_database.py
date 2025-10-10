#!/usr/bin/env python3
"""
Development database setup script for InterviewIQ.
This script sets up a PostgreSQL database for development.
"""

import os
import sys
import subprocess
from sqlalchemy import create_engine, text
from app.config import get_settings

def check_postgresql():
    """Check if PostgreSQL is installed and running."""
    try:
        result = subprocess.run(['psql', '--version'], capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ PostgreSQL found: {result.stdout.strip()}")
            return True
        else:
            print("❌ PostgreSQL not found")
            return False
    except FileNotFoundError:
        print("❌ PostgreSQL not found. Please install PostgreSQL first.")
        print("   macOS: brew install postgresql")
        print("   Ubuntu: sudo apt-get install postgresql postgresql-contrib")
        return False

def create_dev_database():
    """Create development database and user."""
    db_name = "interviewiq_dev"
    db_user = "interviewiq_dev"
    db_password = "dev_password"
    
    try:
        # Create database
        result = subprocess.run(['createdb', db_name], capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ Database '{db_name}' created successfully")
        else:
            print(f"⚠️ Database '{db_name}' might already exist: {result.stderr}")
        
        # Create user and grant permissions
        psql_commands = [
            f"CREATE USER {db_user} WITH PASSWORD '{db_password}';",
            f"GRANT ALL PRIVILEGES ON DATABASE {db_name} TO {db_user};",
            f"ALTER USER {db_user} CREATEDB;"
        ]
        
        for command in psql_commands:
            result = subprocess.run(
                ['psql', '-d', db_name, '-c', command],
                capture_output=True, text=True
            )
            if result.returncode == 0:
                print(f"✅ Command executed: {command}")
            else:
                print(f"⚠️ Command might have failed: {result.stderr}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error creating database: {e}")
        return False

def test_connection():
    """Test database connection."""
    try:
        db_url = "postgresql://interviewiq_dev:dev_password@localhost:5432/interviewiq_dev"
        engine = create_engine(db_url)
        
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            if result.fetchone():
                print("✅ Database connection successful")
                return True
            else:
                print("❌ Database connection failed")
                return False
                
    except Exception as e:
        print(f"❌ Database connection test failed: {e}")
        return False

def create_env_file():
    """Create .env file with development configuration."""
    env_content = """# Development Database Configuration
DATABASE_URL=postgresql://interviewiq_dev:dev_password@localhost:5432/interviewiq_dev

# JWT Configuration
SECRET_KEY=dev-secret-key-not-for-production
ACCESS_TOKEN_EXPIRE_MINUTES=30

# AI Service Configuration (optional for development)
OPENAI_API_KEY=your-openai-api-key
ANTHROPIC_API_KEY=your-anthropic-api-key
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama2

# Application Configuration
MAX_TOKENS=2000
TEMPERATURE=0.7
"""
    
    try:
        with open('.env', 'w') as f:
            f.write(env_content)
        print("✅ .env file created with development configuration")
        return True
    except Exception as e:
        print(f"❌ Error creating .env file: {e}")
        return False

def main():
    """Main setup function."""
    print("🚀 Setting up InterviewIQ development database...")
    print("📋 This will set up PostgreSQL as the default development database")
    print("   Database: interviewiq_dev")
    print("   User: interviewiq_dev")
    print("   Password: dev_password")
    print()
    
    # Check PostgreSQL
    if not check_postgresql():
        print("\n❌ Please install PostgreSQL first and try again.")
        print("\nInstallation instructions:")
        print("  macOS: brew install postgresql && brew services start postgresql")
        print("  Ubuntu: sudo apt-get install postgresql postgresql-contrib")
        print("  CentOS: sudo yum install postgresql postgresql-server")
        sys.exit(1)
    
    # Create database
    if not create_dev_database():
        print("\n❌ Database setup failed")
        print("\n💡 Troubleshooting:")
        print("1. Make sure PostgreSQL is running: brew services start postgresql")
        print("2. Check if you have permission to create databases")
        print("3. Try running: createdb interviewiq_dev manually")
        sys.exit(1)
    
    # Test connection
    if not test_connection():
        print("\n❌ Database connection test failed")
        print("\n💡 Check your PostgreSQL configuration and try again")
        sys.exit(1)
    
    # Create .env file
    if not create_env_file():
        print("\n❌ Environment file creation failed")
        sys.exit(1)
    
    print("\n✅ Development database setup completed successfully!")
    print("\nNext steps:")
    print("1. Run: alembic revision --autogenerate -m 'Initial migration'")
    print("2. Run: alembic upgrade head")
    print("3. Run: uvicorn app.main:app --reload")
    print("\n🎉 Your PostgreSQL development environment is ready!")
    print("\n📚 For more information, see DEVELOPMENT_SETUP.md")

if __name__ == "__main__":
    main()
