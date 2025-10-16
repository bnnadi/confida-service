# Environment Variables Configuration

This document describes the environment variables used to configure the Confida API for different environments (development, staging, production).

## 🔧 Route Control Variables

### `ENABLE_DEBUG_ROUTES`
- **Default**: `false`
- **Description**: Controls debug-specific routes (not implemented yet)
- **Production**: Should be `false`
- **Development**: Can be `true` for debugging

### `ENABLE_SECURITY_ROUTES`
- **Default**: `false`
- **Description**: Controls security testing and audit endpoints
- **Production**: Should be `false` (security risk)
- **Development**: Can be `true` for testing security headers

**Security Routes:**
- `GET /api/v1/security/headers` - View security configuration
- `GET /api/v1/security/test` - Test security headers
- `POST /api/v1/security/validate` - Validate request security
- `GET /api/v1/security/audit` - Security audit report
- `POST /api/v1/security/sanitize` - Input sanitization

### `ENABLE_ADMIN_ROUTES`
- **Default**: `true`
- **Description**: Controls administrative endpoints
- **Production**: Can be `true` (useful for monitoring)
- **Development**: Should be `true`

**Admin Routes:**
- `GET /api/v1/admin/health` - Health check
- `GET /api/v1/admin/services` - AI service status
- `GET /api/v1/admin/models` - Available AI models
- `GET /api/v1/admin/rate-limits` - Rate limiting configuration
- `GET /api/v1/admin/rate-limits/status/{client_id}` - Client rate limit status
- `POST /api/v1/admin/rate-limits/reset/{client_id}` - Reset client rate limits

## 🛡️ Security Configuration

### `SECURITY_HEADERS_ENABLED`
- **Default**: `true`
- **Description**: Enables security headers middleware
- **Production**: Should be `true`
- **Development**: Can be `true` or `false`

### `CORS_ORIGINS`
- **Default**: `https://localhost:3000,https://127.0.0.1:3000,https://confida.com`
- **Description**: Allowed CORS origins (comma-separated)
- **Production**: Set to your actual frontend domains
- **Development**: Can include localhost origins

### `CORS_METHODS`
- **Default**: `GET,POST,PUT,DELETE,OPTIONS,PATCH`
- **Description**: Allowed HTTP methods for CORS
- **Production**: Should match your API usage
- **Development**: Can be more permissive

### `CORS_HEADERS`
- **Default**: `Content-Type,Authorization,API-Version,X-Requested-With`
- **Description**: Allowed headers for CORS
- **Production**: Should match your frontend needs
- **Development**: Can be more permissive

## 🚀 Rate Limiting Configuration

### `RATE_LIMIT_ENABLED`
- **Default**: `true`
- **Description**: Enables rate limiting middleware
- **Production**: Should be `true`
- **Development**: Can be `false` for easier testing

### `RATE_LIMIT_BACKEND`
- **Default**: `memory`
- **Description**: Rate limiting backend (`memory` or `redis`)
- **Production**: Should be `redis` for scalability
- **Development**: Can be `memory`

### `RATE_LIMIT_REDIS_URL`
- **Default**: `redis://localhost:6379`
- **Description**: Redis URL for rate limiting
- **Production**: Set to your Redis instance
- **Development**: Can be localhost

## 🔑 AI Service Configuration

### `OPENAI_API_KEY`
- **Default**: `""`
- **Description**: OpenAI API key
- **Production**: Set to your production key
- **Development**: Can be empty or test key

### `ANTHROPIC_API_KEY`
- **Default**: `""`
- **Description**: Anthropic API key
- **Production**: Set to your production key
- **Development**: Can be empty or test key

### `OLLAMA_BASE_URL`
- **Default**: `http://localhost:11434`
- **Description**: Ollama service URL
- **Production**: Set to your Ollama instance
- **Development**: Can be localhost

## 🗄️ Database Configuration

### `DATABASE_URL`
- **Default**: `postgresql://confida_dev:dev_password@localhost:5432/confida_dev`
- **Description**: Database connection URL
- **Production**: Set to your production database
- **Development**: Can be localhost

## 📝 Environment-Specific Configurations

### Development Environment
```bash
ENVIRONMENT=development
ENABLE_DEBUG_ROUTES=true
ENABLE_SECURITY_ROUTES=true
ENABLE_ADMIN_ROUTES=true
SECURITY_HEADERS_ENABLED=true
RATE_LIMIT_ENABLED=false
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
```

### Staging Environment
```bash
ENVIRONMENT=staging
ENABLE_DEBUG_ROUTES=false
ENABLE_SECURITY_ROUTES=true
ENABLE_ADMIN_ROUTES=true
SECURITY_HEADERS_ENABLED=true
RATE_LIMIT_ENABLED=true
RATE_LIMIT_BACKEND=redis
CORS_ORIGINS=https://staging.confida.com
```

### Production Environment
```bash
ENVIRONMENT=production
ENABLE_DEBUG_ROUTES=false
ENABLE_SECURITY_ROUTES=false
ENABLE_ADMIN_ROUTES=true
SECURITY_HEADERS_ENABLED=true
RATE_LIMIT_ENABLED=true
RATE_LIMIT_BACKEND=redis
CORS_ORIGINS=https://confida.com,https://www.confida.com
```

## 🔍 Environment Status Check

The application logs its environment configuration on startup. Look for:

```
🔧 Environment Configuration:
   Environment: production
   Debug routes: ❌
   Security routes: ❌
   Admin routes: ✅
   Security headers: ✅
   Rate limiting: ✅
   CORS origins: 2 configured
   Production ready: ✅
```

## ⚠️ Security Considerations

1. **Never enable debug routes in production**
2. **Never enable security routes in production** (exposes internal configuration)
3. **Use HTTPS origins in production CORS configuration**
4. **Use Redis for rate limiting in production**
5. **Set strong API keys for production**
6. **Use production database URLs**

## 🚀 Deployment Examples

### Docker Compose (Development)
```yaml
environment:
  - ENABLE_DEBUG_ROUTES=true
  - ENABLE_SECURITY_ROUTES=true
  - ENABLE_ADMIN_ROUTES=true
  - RATE_LIMIT_ENABLED=false
```

### Docker Compose (Production)
```yaml
environment:
  - ENABLE_DEBUG_ROUTES=false
  - ENABLE_SECURITY_ROUTES=false
  - ENABLE_ADMIN_ROUTES=true
  - RATE_LIMIT_ENABLED=true
  - RATE_LIMIT_BACKEND=redis
  - CORS_ORIGINS=https://confida.com
```

### Kubernetes ConfigMap
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: confida-config
data:
  ENABLE_DEBUG_ROUTES: "false"
  ENABLE_SECURITY_ROUTES: "false"
  ENABLE_ADMIN_ROUTES: "true"
  RATE_LIMIT_ENABLED: "true"
  RATE_LIMIT_BACKEND: "redis"
  CORS_ORIGINS: "https://confida.com"
```
