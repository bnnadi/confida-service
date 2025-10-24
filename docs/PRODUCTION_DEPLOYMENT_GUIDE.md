# Production Deployment Guide - Vector Database Integration

## 🚀 **Production Deployment Overview**

This guide covers deploying the Confida Vector Database Integration in a production environment with proper security, monitoring, and scalability considerations.

## 🏗️ **Production Architecture**

### **Recommended Production Setup**

```mermaid
graph TB
    subgraph "Load Balancer Layer"
        LB[Load Balancer/API Gateway]
    end
    
    subgraph "Application Layer"
        APP1[Confida App Instance 1]
        APP2[Confida App Instance 2]
        APP3[Confida App Instance N]
    end
    
    subgraph "Database Layer"
        PG[(PostgreSQL Primary)]
        PG_REPLICA[(PostgreSQL Replica)]
        QDRANT[(Qdrant Cluster)]
    end
    
    subgraph "Cache Layer"
        REDIS[(Redis Cluster)]
    end
    
    subgraph "Monitoring"
        PROM[Prometheus]
        GRAF[Grafana]
        ALERT[AlertManager]
    end
    
    LB --> APP1
    LB --> APP2
    LB --> APP3
    
    APP1 --> PG
    APP1 --> QDRANT
    APP1 --> REDIS
    
    APP2 --> PG_REPLICA
    APP2 --> QDRANT
    APP2 --> REDIS
    
    PG --> PG_REPLICA
    
    APP1 --> PROM
    APP2 --> PROM
    APP3 --> PROM
    
    PROM --> GRAF
    PROM --> ALERT
```

## 🔧 **Production Configuration**

### **1. Environment Variables**

Create a production `.env` file:

```bash
# Database Configuration
DATABASE_URL=postgresql://confida_prod:secure_password@postgres-primary:5432/confida_prod
DATABASE_REPLICA_URL=postgresql://confida_prod:secure_password@postgres-replica:5432/confida_prod

# Vector Database Configuration
QDRANT_URL=http://qdrant-cluster:6333
QDRANT_API_KEY=your_secure_qdrant_api_key

# OpenAI Configuration
OPENAI_API_KEY=your_production_openai_api_key
DEFAULT_EMBEDDING_MODEL=text-embedding-3-small

# Redis Configuration
REDIS_URL=redis://redis-cluster:6379/0

# Security
SECRET_KEY=your_very_secure_secret_key_256_bits
JWT_SECRET_KEY=your_jwt_secret_key
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
```

### **2. Docker Compose Production**

```yaml
# docker-compose.prod.yml
version: '3.8'

services:
  # PostgreSQL Primary
  postgres-primary:
    image: postgres:15-alpine
    environment:
      - POSTGRES_DB=confida_prod
      - POSTGRES_USER=confida_prod
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
    volumes:
      - postgres_primary_data:/var/lib/postgresql/data
      - ./scripts/init-db.sql:/docker-entrypoint-initdb.d/init-db.sql
    networks:
      - app-network
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U confida_prod -d confida_prod"]
      interval: 10s
      timeout: 5s
      retries: 5

  # PostgreSQL Replica
  postgres-replica:
    image: postgres:15-alpine
    environment:
      - POSTGRES_DB=confida_prod
      - POSTGRES_USER=confida_prod
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
      - PGUSER=postgres
    volumes:
      - postgres_replica_data:/var/lib/postgresql/data
    networks:
      - app-network
    depends_on:
      - postgres-primary

  # Qdrant Cluster
  qdrant-1:
    image: qdrant/qdrant:v1.7.0
    environment:
      - QDRANT__SERVICE__HTTP_PORT=6333
      - QDRANT__SERVICE__GRPC_PORT=6334
      - QDRANT__CLUSTER__ENABLED=true
      - QDRANT__CLUSTER__P2P_PORT=6335
    volumes:
      - qdrant_1_data:/qdrant/storage
    networks:
      - app-network
    ports:
      - "6333:6333"

  qdrant-2:
    image: qdrant/qdrant:v1.7.0
    environment:
      - QDRANT__SERVICE__HTTP_PORT=6333
      - QDRANT__SERVICE__GRPC_PORT=6334
      - QDRANT__CLUSTER__ENABLED=true
      - QDRANT__CLUSTER__P2P_PORT=6335
    volumes:
      - qdrant_2_data:/qdrant/storage
    networks:
      - app-network
    depends_on:
      - qdrant-1

  # Redis Cluster
  redis:
    image: redis:7-alpine
    command: redis-server --appendonly yes --requirepass ${REDIS_PASSWORD}
    volumes:
      - redis_data:/data
    networks:
      - app-network
    ports:
      - "6379:6379"

  # Application Instances
  app-1:
    build:
      context: .
      dockerfile: Dockerfile.prod
    environment:
      - DATABASE_URL=postgresql://confida_prod:${POSTGRES_PASSWORD}@postgres-primary:5432/confida_prod
      - QDRANT_URL=http://qdrant-1:6333
      - REDIS_URL=redis://:${REDIS_PASSWORD}@redis:6379/0
      - ENVIRONMENT=production
    networks:
      - app-network
    depends_on:
      - postgres-primary
      - qdrant-1
      - redis
    deploy:
      replicas: 2
      resources:
        limits:
          memory: 2G
          cpus: '1.0'
        reservations:
          memory: 1G
          cpus: '0.5'

  # Load Balancer
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf
      - ./nginx/ssl:/etc/nginx/ssl
    networks:
      - app-network
    depends_on:
      - app-1

  # Monitoring
  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    networks:
      - app-network

  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=${GRAFANA_PASSWORD}
    volumes:
      - grafana_data:/var/lib/grafana
      - ./monitoring/grafana/dashboards:/etc/grafana/provisioning/dashboards
    networks:
      - app-network

volumes:
  postgres_primary_data:
  postgres_replica_data:
  qdrant_1_data:
  qdrant_2_data:
  redis_data:
  prometheus_data:
  grafana_data:

networks:
  app-network:
    driver: bridge
```

### **3. Production Dockerfile**

```dockerfile
# Dockerfile.prod
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
```

## 🔒 **Security Configuration**

### **1. SSL/TLS Configuration**

```nginx
# nginx/nginx.conf
upstream app_backend {
    server app-1:8000;
    server app-2:8000;
}

server {
    listen 80;
    server_name your-domain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com;

    ssl_certificate /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512;
    ssl_prefer_server_ciphers off;

    # Security headers
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains";

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
http {
    limit_req_zone $binary_remote_addr zone=vector_api:10m rate=10r/s;
}
```

### **2. Database Security**

```sql
-- scripts/init-db.sql
-- Create production database and user
CREATE DATABASE confida_prod;
CREATE USER confida_prod WITH ENCRYPTED PASSWORD 'secure_password';

-- Grant permissions
GRANT ALL PRIVILEGES ON DATABASE confida_prod TO confida_prod;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO confida_prod;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO confida_prod;

-- Enable row-level security
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE interview_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE questions ENABLE ROW LEVEL SECURITY;
ALTER TABLE answers ENABLE ROW LEVEL SECURITY;
```

## 📊 **Monitoring and Observability**

### **1. Prometheus Configuration**

```yaml
# monitoring/prometheus.yml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'confida-app'
    static_configs:
      - targets: ['app-1:8001', 'app-2:8001']
    metrics_path: '/metrics'
    scrape_interval: 5s

  - job_name: 'postgres'
    static_configs:
      - targets: ['postgres-exporter:9187']

  - job_name: 'redis'
    static_configs:
      - targets: ['redis-exporter:9121']

  - job_name: 'qdrant'
    static_configs:
      - targets: ['qdrant-1:6333']
    metrics_path: '/metrics'
```

### **2. Grafana Dashboards**

Create dashboards for:
- **Application Metrics**: Request rates, response times, error rates
- **Vector Database Metrics**: Collection sizes, search performance, embedding generation
- **Database Metrics**: Connection pools, query performance, replication lag
- **System Metrics**: CPU, memory, disk usage

### **3. Alerting Rules**

```yaml
# monitoring/alerts.yml
groups:
  - name: confida-alerts
    rules:
      - alert: HighErrorRate
        expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.1
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "High error rate detected"

      - alert: VectorSearchSlow
        expr: histogram_quantile(0.95, rate(vector_search_duration_seconds_bucket[5m])) > 2
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Vector search is slow"

      - alert: EmbeddingGenerationFailed
        expr: rate(embedding_generation_errors_total[5m]) > 0.05
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Embedding generation failing"
```

## 🚀 **Deployment Process**

### **1. Pre-deployment Checklist**

```bash
#!/bin/bash
# scripts/pre-deployment-check.sh

echo "🔍 Running pre-deployment checks..."

# Check environment variables
required_vars=("DATABASE_URL" "QDRANT_URL" "OPENAI_API_KEY" "SECRET_KEY")
for var in "${required_vars[@]}"; do
    if [ -z "${!var}" ]; then
        echo "❌ Missing required environment variable: $var"
        exit 1
    fi
done

# Check database connectivity
echo "🔍 Checking database connectivity..."
python -c "
import psycopg2
import os
try:
    conn = psycopg2.connect(os.getenv('DATABASE_URL'))
    conn.close()
    print('✅ Database connection successful')
except Exception as e:
    print(f'❌ Database connection failed: {e}')
    exit(1)
"

# Check Qdrant connectivity
echo "🔍 Checking Qdrant connectivity..."
python -c "
import requests
import os
try:
    response = requests.get(f\"{os.getenv('QDRANT_URL')}/health\")
    if response.status_code == 200:
        print('✅ Qdrant connection successful')
    else:
        print(f'❌ Qdrant connection failed: {response.status_code}')
        exit(1)
except Exception as e:
    print(f'❌ Qdrant connection failed: {e}')
    exit(1)
"

# Run tests
echo "🔍 Running tests..."
pytest tests/ --tb=short

echo "✅ Pre-deployment checks passed!"
```

### **2. Deployment Script**

```bash
#!/bin/bash
# scripts/deploy.sh

set -e

echo "🚀 Starting production deployment..."

# Build and push images
echo "📦 Building application image..."
docker build -f Dockerfile.prod -t confida:latest .

# Run database migrations
echo "🗄️ Running database migrations..."
docker-compose -f docker-compose.prod.yml run --rm app-1 python -m alembic upgrade head

# Initialize vector collections
echo "🔍 Initializing vector collections..."
docker-compose -f docker-compose.prod.yml run --rm app-1 python -c "
from app.services.vector_service import vector_service
import asyncio
asyncio.run(vector_service.initialize_collections())
print('✅ Vector collections initialized')
"

# Deploy services
echo "🚀 Deploying services..."
docker-compose -f docker-compose.prod.yml up -d

# Wait for services to be healthy
echo "⏳ Waiting for services to be healthy..."
sleep 30

# Health check
echo "🔍 Running health checks..."
curl -f http://localhost/health || {
    echo "❌ Health check failed"
    exit 1
}

echo "✅ Deployment completed successfully!"
```

### **3. Rollback Script**

```bash
#!/bin/bash
# scripts/rollback.sh

echo "🔄 Rolling back deployment..."

# Stop current services
docker-compose -f docker-compose.prod.yml down

# Restore from backup (if needed)
# docker-compose -f docker-compose.prod.yml up -d postgres-primary
# pg_restore -h localhost -U confida_prod -d confida_prod backup.sql

# Start previous version
docker-compose -f docker-compose.prod.yml up -d

echo "✅ Rollback completed!"
```

## 📈 **Performance Optimization**

### **1. Application Tuning**

```python
# app/config.py - Production settings
class ProductionSettings(Settings):
    # Database connection pooling
    ASYNC_DATABASE_POOL_SIZE = 20
    ASYNC_DATABASE_MAX_OVERFLOW = 30
    ASYNC_DATABASE_POOL_TIMEOUT = 30
    ASYNC_DATABASE_POOL_RECYCLE = 3600
    
    # Embedding cache
    EMBEDDING_CACHE_SIZE = 10000
    EMBEDDING_CACHE_TTL = 7200
    
    # Vector search
    VECTOR_SEARCH_BATCH_SIZE = 100
    VECTOR_SEARCH_TIMEOUT = 30
    
    # Rate limiting
    RATE_LIMIT_REQUESTS = 1000
    RATE_LIMIT_WINDOW = 3600
```

### **2. Database Optimization**

```sql
-- Database indexes for vector operations
CREATE INDEX CONCURRENTLY idx_questions_category_difficulty 
ON questions(category, difficulty_level);

CREATE INDEX CONCURRENTLY idx_questions_skills 
ON questions USING GIN(required_skills);

CREATE INDEX CONCURRENTLY idx_questions_roles 
ON questions USING GIN(compatible_roles);

-- Partitioning for large tables
CREATE TABLE answers_2024 PARTITION OF answers
FOR VALUES FROM ('2024-01-01') TO ('2025-01-01');
```

### **3. Qdrant Optimization**

```python
# Qdrant collection optimization
COLLECTION_CONFIG = {
    "job_descriptions": {
        "vector_size": 1536,
        "distance": "Cosine",
        "hnsw_config": {
            "m": 16,
            "ef_construct": 100,
            "full_scan_threshold": 10000
        },
        "optimizer_config": {
            "default_segment_number": 2,
            "max_segment_size": 200000,
            "memmap_threshold": 50000,
            "indexing_threshold": 20000
        }
    }
}
```

## 🔄 **Backup and Recovery**

### **1. Database Backup**

```bash
#!/bin/bash
# scripts/backup-db.sh

BACKUP_DIR="/backups/$(date +%Y%m%d_%H%M%S)"
mkdir -p $BACKUP_DIR

# PostgreSQL backup
pg_dump $DATABASE_URL > $BACKUP_DIR/postgres_backup.sql

# Qdrant backup
curl -X POST "http://localhost:6333/collections/job_descriptions/snapshots"
curl -X POST "http://localhost:6333/collections/questions/snapshots"
curl -X POST "http://localhost:6333/collections/answers/snapshots"
curl -X POST "http://localhost:6333/collections/user_patterns/snapshots"

echo "✅ Backup completed: $BACKUP_DIR"
```

### **2. Recovery Process**

```bash
#!/bin/bash
# scripts/restore-db.sh

BACKUP_DIR=$1

if [ -z "$BACKUP_DIR" ]; then
    echo "Usage: $0 <backup_directory>"
    exit 1
fi

# Restore PostgreSQL
psql $DATABASE_URL < $BACKUP_DIR/postgres_backup.sql

# Restore Qdrant (manual process)
echo "Please restore Qdrant snapshots manually from: $BACKUP_DIR"

echo "✅ Database restore completed"
```

## 🎯 **Production Usage Examples**

### **1. Question Generation with Vector Search**

```python
# Production usage example
import requests
import asyncio
from app.services.vector_service import vector_service
from app.services.semantic_search_service import semantic_search_service

async def generate_interview_questions(job_description: str, role: str):
    """Generate interview questions using vector search."""
    
    # Store job description in vector database
    job_id = await vector_service.store_job_description(
        job_description=job_description,
        role=role,
        metadata={"source": "api", "timestamp": "2024-01-15"}
    )
    
    # Get question suggestions
    suggestions = await semantic_search_service.get_question_suggestions(
        job_description=job_description,
        role=role,
        difficulty="medium",
        count=10
    )
    
    return {
        "job_id": job_id,
        "suggestions": suggestions,
        "total_questions": len(suggestions)
    }

# Usage
questions = asyncio.run(generate_interview_questions(
    job_description="Senior Python Developer with FastAPI experience...",
    role="python_developer"
))
```

### **2. User Recommendation System**

```python
async def get_user_recommendations(user_id: str, user_profile: dict):
    """Get personalized recommendations for a user."""
    
    # Store user pattern
    pattern_id = await vector_service.store_user_pattern(
        user_id=user_id,
        pattern_data=user_profile
    )
    
    # Get recommendations
    recommendations = await semantic_search_service.get_content_recommendations(
        user_id=user_id,
        content_type="questions",
        user_profile=user_profile,
        limit=20
    )
    
    return {
        "pattern_id": pattern_id,
        "recommendations": recommendations,
        "total_recommendations": len(recommendations)
    }
```

### **3. Analytics and Monitoring**

```python
# Production monitoring example
async def get_production_metrics():
    """Get production metrics for monitoring."""
    
    # Vector database health
    vector_health = await vector_service.health_check()
    
    # Collection statistics
    collection_stats = await vector_service.get_collection_stats()
    
    # Embedding service status
    embedding_models = embedding_service.get_available_models()
    
    return {
        "vector_database": vector_health,
        "collections": collection_stats,
        "embedding_models": embedding_models,
        "timestamp": datetime.utcnow().isoformat()
    }
```

## 🚨 **Production Troubleshooting**

### **Common Issues and Solutions**

1. **High Memory Usage**
   - Reduce embedding cache size
   - Use connection pooling
   - Monitor Qdrant memory usage

2. **Slow Vector Searches**
   - Optimize collection parameters
   - Use appropriate batch sizes
   - Monitor Qdrant performance

3. **Embedding Generation Failures**
   - Check OpenAI API limits
   - Implement retry logic
   - Use local models as fallback

4. **Database Connection Issues**
   - Check connection pool settings
   - Monitor database performance
   - Implement connection retry logic

### **Emergency Procedures**

```bash
# Emergency restart
docker-compose -f docker-compose.prod.yml restart

# Emergency scale up
docker-compose -f docker-compose.prod.yml up -d --scale app-1=5

# Emergency maintenance mode
docker-compose -f docker-compose.prod.yml exec nginx nginx -s reload
```

---

**This production deployment guide ensures your Vector Database Integration runs reliably, securely, and efficiently in a production environment with proper monitoring, backup, and scaling capabilities.**
