#!/bin/bash

# Run database migrations for InterviewIQ
# This script loads environment variables and runs Alembic migrations

set -e  # Exit on any error

echo "🗄️  Running InterviewIQ Database Migrations"

# Load environment variables
if [ -f .env ]; then
    echo "📋 Loading environment variables from .env"
    export $(cat .env | grep -v '^#' | xargs)
else
    echo "⚠️  No .env file found, using system environment variables"
fi

# Check if DATABASE_URL is set
if [ -z "$DATABASE_URL" ]; then
    echo "❌ DATABASE_URL environment variable is not set!"
    echo "Please set DATABASE_URL or create a .env file with the database configuration."
    exit 1
fi

echo "🔗 Database URL: $DATABASE_URL"

# Run migrations
echo "🚀 Running Alembic migrations..."
alembic upgrade head

if [ $? -eq 0 ]; then
    echo "✅ Database migrations completed successfully!"
else
    echo "❌ Database migrations failed!"
    exit 1
fi
