#!/bin/bash

echo "🗄️  Setting up Confida Service Database"

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

# Check if environment is specified
ENVIRONMENT=${1:-development}

print_status "Setting up database for $ENVIRONMENT environment..."

if [ "$ENVIRONMENT" = "development" ]; then
    print_status "Starting development database with Docker..."
    
    # Start only the database service
    docker-compose up -d database
    
    # Wait for database to be ready
    print_status "Waiting for database to be ready..."
    sleep 10
    
    # Check if database is ready
    if docker-compose exec database pg_isready -U ${POSTGRES_USER:-confida} -d ${POSTGRES_DB:-confida_dev}; then
        print_success "Database is ready!"
    else
        print_error "Database failed to start"
        exit 1
    fi
    
    # Run migrations
    print_status "Running database migrations..."
    
    # Set environment variables for development
    export DATABASE_URL="postgresql://${POSTGRES_USER:-confida}:${POSTGRES_PASSWORD:-password}@localhost:${POSTGRES_PORT:-5432}/${POSTGRES_DB:-confida_dev}"
    
    # Run Alembic migrations
    if command -v alembic &> /dev/null; then
        alembic upgrade head
        print_success "Migrations completed!"
    else
        print_warning "Alembic not found, running setup script instead..."
        python scripts/setup/setup_database.py
    fi
    
elif [ "$ENVIRONMENT" = "production" ]; then
    print_status "Setting up production database with external service..."
    
    # Check if DATABASE_URL is set
    if [ -z "$DATABASE_URL" ]; then
        print_error "DATABASE_URL environment variable is not set!"
        print_status "Please set your database connection string:"
        print_status "export DATABASE_URL='postgresql://user:password@host:port/database'"
        exit 1
    fi
    
    # Run migrations
    print_status "Running production database migrations..."
    
    # Run Alembic migrations
    if command -v alembic &> /dev/null; then
        alembic upgrade head
        print_success "Production migrations completed!"
    else
        print_warning "Alembic not found, running setup script instead..."
        python scripts/setup/setup_database.py
    fi
    
else
    print_error "Invalid environment. Use 'development' or 'production'"
    exit 1
fi

print_success "Database setup completed for $ENVIRONMENT environment!"
print_status "Next steps:"
if [ "$ENVIRONMENT" = "development" ]; then
    print_status "1. Start the service: docker-compose up"
    print_status "2. Or start in background: docker-compose up -d"
else
    print_status "1. Deploy to production: docker-compose -f docker-compose.prod.yml up -d"
    print_status "2. Monitor logs: docker-compose -f docker-compose.prod.yml logs -f"
fi
