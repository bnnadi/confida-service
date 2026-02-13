# Database Setup Guide

This guide explains how to set up the database for the Confida service.

## Overview

The Confida service uses PostgreSQL as the primary database with SQLAlchemy as the ORM and Alembic for database migrations.

## Prerequisites

- Python 3.8+
- PostgreSQL 12+ (for production)
- SQLite (for development/testing)

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Environment Configuration

Copy the example environment file and update with your settings:

```bash
cp env.example .env
```

Edit `.env` with your database credentials:

```env
DATABASE_URL=postgresql://confida:password@localhost:5432/confida_db
SECRET_KEY=your-super-secret-key-change-this-in-production
```

### 3. Database Setup

#### Option A: PostgreSQL (Production)

1. **Install PostgreSQL:**
   ```bash
   # macOS with Homebrew
   brew install postgresql
   brew services start postgresql
   
   # Ubuntu/Debian
   sudo apt-get install postgresql postgresql-contrib
   sudo systemctl start postgresql
   ```

2. **Create Database and User:**
   ```bash
   createdb confida_db
   psql -d confida_db -c "CREATE USER confida WITH PASSWORD 'password';"
   psql -d confida_db -c "GRANT ALL PRIVILEGES ON DATABASE confida_db TO confida;"
   ```

3. **Run Migrations:**
   ```bash
   alembic revision --autogenerate -m "Initial migration"
   alembic upgrade head
   ```

#### Option B: SQLite (Development/Testing)

For development and testing, you can use SQLite by updating your `.env`:

```env
DATABASE_URL=sqlite:///./confida.db
```

Then run the setup script (from project root):

```bash
python scripts/setup/setup_database.py
```

## Database Schema

### Users Table

The `users` table stores user account information:

| Column | Type | Description |
|--------|------|-------------|
| id | Integer | Primary key |
| email | String(255) | Unique email address |
| hashed_password | String(255) | Bcrypt hashed password |
| first_name | String(255) | User's first name |
| last_name | String(255) | User's last name |
| is_active | Boolean | Account active status |
| is_verified | Boolean | Email verification status |
| created_at | DateTime | Account creation timestamp |
| updated_at | DateTime | Last update timestamp |
| last_login | DateTime | Last login timestamp |
| bio | Text | User biography |
| experience_level | String(50) | Experience level (junior, mid, senior, executive) |
| preferred_industries | Text | JSON string of preferred industries |
| skills | Text | JSON string of user skills |

## Migration Commands

### Create a New Migration

```bash
alembic revision --autogenerate -m "Description of changes"
```

### Apply Migrations

```bash
alembic upgrade head
```

### Rollback Migration

```bash
alembic downgrade -1
```

### Check Migration Status

```bash
alembic current
alembic history
```

## Testing

Run the database tests to verify everything is working:

```bash
python -c "from app.database.connection import engine; print('✅ Database connection successful!' if engine else '❌ Connection failed')"
```

## Troubleshooting

### Common Issues

1. **Connection Refused:**
   - Ensure PostgreSQL is running
   - Check if the port (5432) is correct
   - Verify firewall settings

2. **Authentication Failed:**
   - Check username and password
   - Ensure user has proper permissions
   - Verify database exists

3. **Import Errors:**
   - Install missing dependencies: `pip install -r requirements.txt`
   - Check Python path and virtual environment

### Debug Mode

Enable SQLAlchemy logging for debugging:

```python
import logging
logging.basicConfig()
logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)
```

## Production Considerations

1. **Security:**
   - Use strong passwords
   - Enable SSL connections
   - Restrict database access

2. **Performance:**
   - Configure connection pooling
   - Add database indexes
   - Monitor query performance

3. **Backup:**
   - Set up regular backups
   - Test restore procedures
   - Document recovery process

## File Structure

```
├── alembic/                 # Migration files
│   ├── versions/           # Migration scripts
│   └── env.py             # Alembic environment
├── alembic.ini            # Alembic configuration
├── app/
│   ├── database.py        # Database connection
│   ├── models/
│   │   ├── user.py        # User model
│   │   └── auth.py        # Auth schemas
│   └── config.py          # Configuration
├── scripts/setup/
│   ├── setup_database.py      # Database setup script
│   └── setup_dev_database.py  # Development database setup
└── env.example           # Environment template
```

## Next Steps

After setting up the database, you can proceed with:

1. **Authentication Implementation** - JWT tokens, login/logout
2. **User Management** - Registration, profile management
3. **Protected Routes** - Secure API endpoints
4. **Session Management** - User session handling

For more information, see the main README.md file.
