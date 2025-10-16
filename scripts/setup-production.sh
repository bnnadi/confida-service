#!/bin/bash

# Production Setup Script for Confida Vector Database Integration
# This script helps you set up the production environment

set -e

echo "🚀 Confida Production Setup"
echo "================================"

# Check if running as root
if [ "$EUID" -eq 0 ]; then
    echo "❌ Please don't run this script as root"
    exit 1
fi

# Check prerequisites
echo "🔍 Checking prerequisites..."

# Check Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    exit 1
fi

# Check Docker Compose
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3 first."
    exit 1
fi

echo "✅ Prerequisites check passed"

# Create production environment file
echo "📝 Creating production environment file..."

if [ ! -f .env.prod ]; then
    cat > .env.prod << EOF
# Production Environment Configuration
# ===================================

# Database Configuration
POSTGRES_DB=confida_prod
POSTGRES_USER=confida_prod
POSTGRES_PASSWORD=$(openssl rand -base64 32)
DATABASE_URL=postgresql://confida_prod:${POSTGRES_PASSWORD}@postgres-primary:5432/confida_prod

# Vector Database Configuration
QDRANT_URL=http://qdrant:6333
QDRANT_API_KEY=$(openssl rand -base64 32)

# OpenAI Configuration (REQUIRED)
OPENAI_API_KEY=your_openai_api_key_here
DEFAULT_EMBEDDING_MODEL=text-embedding-3-small

# Redis Configuration
REDIS_PASSWORD=$(openssl rand -base64 32)
REDIS_URL=redis://:${REDIS_PASSWORD}@redis:6379/0

# Security
SECRET_KEY=$(openssl rand -base64 64)
JWT_SECRET_KEY=$(openssl rand -base64 64)
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Application Configuration
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO

# Performance Tuning
ASYNC_DATABASE_ENABLED=true
ASYNC_DATABASE_POOL_SIZE=20
ASYNC_DATABASE_MAX_OVERFLOW=30
EMBEDDING_CACHE_SIZE=10000
EMBEDDING_CACHE_TTL=7200

# Monitoring
PROMETHEUS_ENABLED=true
PROMETHEUS_PORT=8001
GRAFANA_PASSWORD=$(openssl rand -base64 16)

# Ports
BACKEND_PORT=8000
POSTGRES_PORT=5432
QDRANT_PORT=6333
REDIS_PORT=6379
EOF

    echo "✅ Created .env.prod file"
    echo "⚠️  IMPORTANT: Please edit .env.prod and set your OpenAI API key!"
else
    echo "⚠️  .env.prod already exists, skipping creation"
fi

# Create production Docker Compose file
echo "📝 Creating production Docker Compose file..."

if [ ! -f docker-compose.prod.yml ]; then
    cat > docker-compose.prod.yml << 'EOF'
version: '3.8'

services:
  # PostgreSQL Database
  postgres:
    image: postgres:15-alpine
    container_name: confida-postgres
    environment:
      - POSTGRES_DB=${POSTGRES_DB}
      - POSTGRES_USER=${POSTGRES_USER}
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
    ports:
      - "${POSTGRES_PORT:-5432}:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    networks:
      - confida-network
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER} -d ${POSTGRES_DB}"]
      interval: 10s
      timeout: 5s
      retries: 5

  # Qdrant Vector Database
  qdrant:
    image: qdrant/qdrant:v1.7.0
    container_name: confida-qdrant
    ports:
      - "${QDRANT_PORT:-6333}:6333"
      - "6334:6334"
    volumes:
      - qdrant_data:/qdrant/storage
    networks:
      - confida-network
    environment:
      - QDRANT__SERVICE__HTTP_PORT=6333
      - QDRANT__SERVICE__GRPC_PORT=6334
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:6333/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  # Redis Cache
  redis:
    image: redis:7-alpine
    container_name: confida-redis
    command: redis-server --appendonly yes --requirepass ${REDIS_PASSWORD}
    ports:
      - "${REDIS_PORT:-6379}:6379"
    volumes:
      - redis_data:/data
    networks:
      - confida-network
    healthcheck:
      test: ["CMD", "redis-cli", "--raw", "incr", "ping"]
      interval: 10s
      timeout: 3s
      retries: 5

  # Application
  app:
    build:
      context: .
      dockerfile: Dockerfile.prod
    container_name: confida-app
    ports:
      - "${BACKEND_PORT:-8000}:8000"
    environment:
      - PYTHONPATH=/app
      - DATABASE_URL=${DATABASE_URL}
      - QDRANT_URL=${QDRANT_URL}
      - QDRANT_API_KEY=${QDRANT_API_KEY}
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - REDIS_URL=${REDIS_URL}
      - SECRET_KEY=${SECRET_KEY}
      - JWT_SECRET_KEY=${JWT_SECRET_KEY}
      - ACCESS_TOKEN_EXPIRE_MINUTES=${ACCESS_TOKEN_EXPIRE_MINUTES}
      - ENVIRONMENT=${ENVIRONMENT}
      - DEBUG=${DEBUG}
      - LOG_LEVEL=${LOG_LEVEL}
      - ASYNC_DATABASE_ENABLED=${ASYNC_DATABASE_ENABLED}
      - ASYNC_DATABASE_POOL_SIZE=${ASYNC_DATABASE_POOL_SIZE}
      - ASYNC_DATABASE_MAX_OVERFLOW=${ASYNC_DATABASE_MAX_OVERFLOW}
      - EMBEDDING_CACHE_SIZE=${EMBEDDING_CACHE_SIZE}
      - EMBEDDING_CACHE_TTL=${EMBEDDING_CACHE_TTL}
      - PROMETHEUS_ENABLED=${PROMETHEUS_ENABLED}
      - PROMETHEUS_PORT=${PROMETHEUS_PORT}
    volumes:
      - .:/app
    networks:
      - confida-network
    depends_on:
      postgres:
        condition: service_healthy
      qdrant:
        condition: service_healthy
      redis:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  # Nginx Load Balancer
  nginx:
    image: nginx:alpine
    container_name: confida-nginx
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
    networks:
      - confida-network
    depends_on:
      - app

volumes:
  postgres_data:
  qdrant_data:
  redis_data:

networks:
  confida-network:
    driver: bridge
EOF

    echo "✅ Created docker-compose.prod.yml"
else
    echo "⚠️  docker-compose.prod.yml already exists, skipping creation"
fi

# Create production Dockerfile
echo "📝 Creating production Dockerfile..."

if [ ! -f Dockerfile.prod ]; then
    cat > Dockerfile.prod << 'EOF'
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create non-root user
RUN useradd --create-home --shell /bin/bash app \
    && chown -R app:app /app
USER app

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Expose port
EXPOSE 8000

# Start application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
EOF

    echo "✅ Created Dockerfile.prod"
else
    echo "⚠️  Dockerfile.prod already exists, skipping creation"
fi

# Create nginx configuration
echo "📝 Creating nginx configuration..."

mkdir -p nginx

if [ ! -f nginx/nginx.conf ]; then
    cat > nginx/nginx.conf << 'EOF'
events {
    worker_connections 1024;
}

http {
    upstream app_backend {
        server app:8000;
    }

    server {
        listen 80;
        server_name localhost;

        # Security headers
        add_header X-Frame-Options DENY;
        add_header X-Content-Type-Options nosniff;
        add_header X-XSS-Protection "1; mode=block";

        location / {
            proxy_pass http://app_backend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        location /api/v1/vector/ {
            # Rate limiting for vector endpoints
            limit_req zone=vector_api burst=10 nodelay;
            proxy_pass http://app_backend;
        }
    }

    # Rate limiting zones
    limit_req_zone $binary_remote_addr zone=vector_api:10m rate=10r/s;
}
EOF

    echo "✅ Created nginx configuration"
else
    echo "⚠️  nginx.conf already exists, skipping creation"
fi

# Create deployment script
echo "📝 Creating deployment script..."

if [ ! -f scripts/deploy-production.sh ]; then
    cat > scripts/deploy-production.sh << 'EOF'
#!/bin/bash

# Production Deployment Script
set -e

echo "🚀 Starting production deployment..."

# Load environment variables
if [ -f .env.prod ]; then
    export $(cat .env.prod | grep -v '^#' | xargs)
    echo "✅ Loaded production environment variables"
else
    echo "❌ .env.prod file not found. Please run setup-production.sh first."
    exit 1
fi

# Check OpenAI API key
if [ "$OPENAI_API_KEY" = "your_openai_api_key_here" ]; then
    echo "❌ Please set your OpenAI API key in .env.prod"
    exit 1
fi

# Build application image
echo "📦 Building application image..."
docker build -f Dockerfile.prod -t confida:latest .

# Start services
echo "🚀 Starting services..."
docker-compose -f docker-compose.prod.yml up -d

# Wait for services to be healthy
echo "⏳ Waiting for services to be healthy..."
sleep 30

# Run database migrations
echo "🗄️ Running database migrations..."
docker-compose -f docker-compose.prod.yml exec app python -m alembic upgrade head

# Initialize vector collections
echo "🔍 Initializing vector collections..."
docker-compose -f docker-compose.prod.yml exec app python -c "
from app.services.vector_service import vector_service
import asyncio
asyncio.run(vector_service.initialize_collections())
print('✅ Vector collections initialized')
"

# Health check
echo "🔍 Running health checks..."
if curl -f http://localhost/health; then
    echo "✅ Health check passed"
else
    echo "❌ Health check failed"
    exit 1
fi

echo "✅ Production deployment completed successfully!"
echo ""
echo "🌐 Application is available at: http://localhost"
echo "📊 API Documentation: http://localhost/docs"
echo "🔍 Health Check: http://localhost/health"
echo "🔍 Vector Health: http://localhost/api/v1/vector/health"
EOF

    chmod +x scripts/deploy-production.sh
    echo "✅ Created deployment script"
else
    echo "⚠️  deploy-production.sh already exists, skipping creation"
fi

# Create monitoring script
echo "📝 Creating monitoring script..."

if [ ! -f scripts/monitor-production.sh ]; then
    cat > scripts/monitor-production.sh << 'EOF'
#!/bin/bash

# Production Monitoring Script
echo "📊 Confida Production Monitoring"
echo "===================================="

# Check service status
echo "🔍 Service Status:"
docker-compose -f docker-compose.prod.yml ps

echo ""
echo "🔍 Health Checks:"
echo "Application: $(curl -s -o /dev/null -w "%{http_code}" http://localhost/health)"
echo "Vector DB: $(curl -s -o /dev/null -w "%{http_code}" http://localhost/api/v1/vector/health)"

echo ""
echo "🔍 Resource Usage:"
docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}\t{{.BlockIO}}"

echo ""
echo "🔍 Logs (last 10 lines):"
docker-compose -f docker-compose.prod.yml logs --tail=10 app
EOF

    chmod +x scripts/monitor-production.sh
    echo "✅ Created monitoring script"
else
    echo "⚠️  monitor-production.sh already exists, skipping creation"
fi

echo ""
echo "🎉 Production setup completed!"
echo ""
echo "📋 Next steps:"
echo "1. Edit .env.prod and set your OpenAI API key"
echo "2. Run: ./scripts/deploy-production.sh"
echo "3. Monitor with: ./scripts/monitor-production.sh"
echo ""
echo "📚 Documentation:"
echo "- Production Guide: docs/PRODUCTION_DEPLOYMENT_GUIDE.md"
echo "- Vector Database Guide: docs/VECTOR_DATABASE_GUIDE.md"
echo ""
echo "🔗 URLs (after deployment):"
echo "- Application: http://localhost"
echo "- API Docs: http://localhost/docs"
echo "- Health Check: http://localhost/health"
echo "- Vector Health: http://localhost/api/v1/vector/health"
