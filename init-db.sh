#!/bin/bash

# Database initialization script for Confida development environment
set -e

echo "🚀 Initializing Confida database..."

# Check if DATABASE_URL is set
if [ -z "$DATABASE_URL" ]; then
    echo "❌ DATABASE_URL environment variable is not set!"
    exit 1
fi

echo "📊 Database URL: $DATABASE_URL"

# Wait for database to be ready
echo "⏳ Waiting for database to be ready..."
until python -c "
import psycopg2
import os
try:
    conn = psycopg2.connect(os.getenv('DATABASE_URL'))
    conn.close()
    print('✅ Database is ready!')
except Exception as e:
    print(f'⏳ Database not ready yet: {e}')
    exit(1)
" 2>/dev/null; do
    echo "⏳ Waiting for database..."
    sleep 2
done

# Run Alembic migrations
echo "🔄 Running database migrations..."
alembic upgrade head

if [ $? -eq 0 ]; then
    echo "✅ Database migrations completed successfully!"
else
    echo "❌ Database migrations failed!"
    exit 1
fi

# Optional: Seed initial data if needed
echo "🌱 Database initialization completed!"
echo "🎉 Confida database is ready for development!"
