#!/bin/bash

echo "🗄️  Initializing InterviewIQ Database"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if DATABASE_URL is set
if [ -z "$DATABASE_URL" ]; then
    print_error "DATABASE_URL environment variable is not set!"
    exit 1
fi

print_status "Database URL: $DATABASE_URL"

# Wait for database to be ready
print_status "Waiting for database to be ready..."
sleep 5

# Run migrations
print_status "Running database migrations..."
if command -v alembic &> /dev/null; then
    alembic upgrade head
    if [ $? -eq 0 ]; then
        print_success "Database migrations completed!"
    else
        print_error "Database migrations failed!"
        exit 1
    fi
else
    print_warning "Alembic not found, trying setup script..."
    if [ -f "setup_database.py" ]; then
        python setup_database.py
        if [ $? -eq 0 ]; then
            print_success "Database setup completed!"
        else
            print_error "Database setup failed!"
            exit 1
        fi
    else
        print_error "No database setup method found!"
        exit 1
    fi
fi

print_success "Database initialization completed!"
