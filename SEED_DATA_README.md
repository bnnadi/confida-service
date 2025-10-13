# 🌱 Seed Data for InterviewIQ

This directory contains scripts to populate your development database with demo data for testing and development purposes.

## Quick Start

```bash
# Run the seed data script
python seed_data.py

# Or use the convenience script
python run_seed.py
```

## What Gets Created

### 👥 Demo Users (4 accounts)
- **demo@interviewiq.com** / `demo123456` - Main demo account
- **john.doe@example.com** / `password123` - Sample user 1  
- **jane.smith@example.com** / `password123` - Sample user 2
- **admin@interviewiq.com** / `admin123456` - Admin account

### 🎯 Interview Sessions (4 complete scenarios)
1. **Senior Software Engineer** - Technical architecture and coding questions
2. **Data Scientist** - Machine learning and data analysis questions  
3. **Product Manager** - Product strategy and user experience questions
4. **DevOps Engineer** - Infrastructure and deployment questions

### 📊 Sample Data
- **20+ Interview Questions** with varying difficulty levels
- **Sample Answers** with AI analysis results and scoring
- **Performance Tracking** data for analytics
- **Analytics Events** for user interaction tracking
- **Agent Configurations** for AI evaluation systems

## Prerequisites

Make sure you have:
1. ✅ PostgreSQL running locally
2. ✅ Database created (`interviewiq_dev`)
3. ✅ Migrations applied (`alembic upgrade head`)
4. ✅ Environment variables configured (`.env` file)

## Usage Examples

### Basic Usage
```bash
# Seed the database
python seed_data.py
```

### Reset and Reseed
```bash
# Drop and recreate database
dropdb interviewiq_dev
createdb interviewiq_dev
psql -d interviewiq_dev -c "CREATE USER interviewiq_dev WITH PASSWORD 'dev_password';"
psql -d interviewiq_dev -c "GRANT ALL PRIVILEGES ON DATABASE interviewiq_dev TO interviewiq_dev;"

# Run migrations
alembic upgrade head

# Seed with demo data
python seed_data.py
```

### Testing with Demo Data
```bash
# Start the application
uvicorn app.main:app --reload

# Test login with demo accounts
curl -X POST "http://localhost:8000/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email": "demo@interviewiq.com", "password": "demo123456"}'
```

## File Structure

```
seed_data.py          # Main seed data script
run_seed.py           # Convenience script to run seed data
SEED_DATA_README.md   # This documentation
```

## Customization

You can modify the seed data by editing the constants in `seed_data.py`:

- `DEMO_USERS` - Add/modify demo user accounts
- `SAMPLE_JOB_DESCRIPTIONS` - Add new job roles and descriptions
- `SAMPLE_QUESTIONS` - Add questions for specific job roles
- `SAMPLE_ANSWERS` - Add sample answers for testing

## Troubleshooting

### Common Issues

1. **Database Connection Error**
   ```
   Error: Could not connect to database
   ```
   - Make sure PostgreSQL is running
   - Check your `DATABASE_URL` in `.env` file
   - Verify database exists: `psql -l`

2. **User Already Exists**
   ```
   User demo@interviewiq.com already exists, skipping...
   ```
   - This is normal - the script skips existing users
   - To reset, drop and recreate the database

3. **Migration Error**
   ```
   Error: No such table 'users'
   ```
   - Run migrations first: `alembic upgrade head`
   - Check if database tables exist

### Getting Help

If you encounter issues:
1. Check the logs for specific error messages
2. Verify your database setup
3. Ensure all dependencies are installed
4. Check the main `DEVELOPMENT_SETUP.md` for detailed setup instructions

## Development Notes

- The seed data script is idempotent - you can run it multiple times safely
- Existing data is preserved (users, sessions, etc.)
- The script uses proper password hashing for security
- All timestamps are realistic for testing purposes
- JSONB fields contain realistic structured data for testing

## Production Warning

⚠️ **Never run this script in production!** This script is designed only for local development and testing. It creates predictable demo data that should never be used in a production environment.
