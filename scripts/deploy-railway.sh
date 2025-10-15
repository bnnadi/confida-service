#!/bin/bash

# Railway Deployment Script
# This script helps you deploy to Railway with zero configuration

echo "🚀 Railway Deployment for InterviewIQ Vector Database"
echo "====================================================="

# Check if Railway CLI is installed
if ! command -v railway &> /dev/null; then
    echo "📦 Installing Railway CLI..."
    
    # Install Railway CLI
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        brew install railway
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        # Linux
        curl -fsSL https://railway.app/install.sh | sh
    else
        echo "❌ Please install Railway CLI manually: https://docs.railway.app/develop/cli"
        exit 1
    fi
fi

echo "✅ Railway CLI installed"

# Login to Railway
echo "🔐 Logging into Railway..."
railway login

# Create new project
echo "🏗️ Creating Railway project..."
railway init

# Add PostgreSQL database
echo "🗄️ Adding PostgreSQL database..."
railway add postgresql

# Add Redis cache
echo "🔴 Adding Redis cache..."
railway add redis

# Add Qdrant vector database
echo "🔍 Adding Qdrant vector database..."
railway add qdrant

# Set environment variables
echo "⚙️ Setting environment variables..."

# Get database URL
DB_URL=$(railway variables --service postgresql | grep DATABASE_URL | cut -d'=' -f2)
REDIS_URL=$(railway variables --service redis | grep REDIS_URL | cut -d'=' -f2)
QDRANT_URL=$(railway variables --service qdrant | grep QDRANT_URL | cut -d'=' -f2)

# Set application variables
railway variables set DATABASE_URL="$DB_URL"
railway variables set REDIS_URL="$REDIS_URL"
railway variables set QDRANT_URL="$QDRANT_URL"
railway variables set ENVIRONMENT=production
railway variables set DEBUG=false
railway variables set LOG_LEVEL=INFO
railway variables set ASYNC_DATABASE_ENABLED=true
railway variables set EMBEDDING_CACHE_SIZE=10000
railway variables set EMBEDDING_CACHE_TTL=7200

echo "⚠️  IMPORTANT: Set your OpenAI API key:"
echo "railway variables set OPENAI_API_KEY=your_openai_api_key_here"
echo ""

# Deploy application
echo "🚀 Deploying application..."
railway up

# Get deployment URL
echo "🌐 Getting deployment URL..."
DEPLOY_URL=$(railway domain)

echo ""
echo "🎉 Deployment completed!"
echo "========================="
echo "🌐 Your app is live at: https://$DEPLOY_URL"
echo "📊 API Documentation: https://$DEPLOY_URL/docs"
echo "🔍 Health Check: https://$DEPLOY_URL/health"
echo "🔍 Vector Health: https://$DEPLOY_URL/api/v1/vector/health"
echo ""
echo "📋 Next steps:"
echo "1. Set your OpenAI API key: railway variables set OPENAI_API_KEY=your_key"
echo "2. Initialize vector collections: curl https://$DEPLOY_URL/api/v1/vector/collections/initialize"
echo "3. Test your API: https://$DEPLOY_URL/docs"
echo ""
echo "🔧 Manage your deployment:"
echo "- View logs: railway logs"
echo "- Open dashboard: railway open"
echo "- Update variables: railway variables"
echo "- Redeploy: railway up"
