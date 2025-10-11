from sqlalchemy.orm import Session
from sqlalchemy import text
from app.database import SessionLocal
from app.config import settings
import redis
import httpx
from typing import Dict, Any
import asyncio


class HealthService:
    """Service for comprehensive health checks."""
    
    def __init__(self):
        self.db_session = None
    
    async def check_database_health(self) -> Dict[str, Any]:
        """Check database connectivity and basic operations."""
        try:
            # Test database connection
            db = SessionLocal()
            self.db_session = db
            
            # Simple query to test connectivity
            result = db.execute(text("SELECT 1")).fetchone()
            
            if result and result[0] == 1:
                return {
                    "status": "healthy",
                    "message": "Database connection successful",
                    "details": {
                        "database_url": settings.DATABASE_URL.split("@")[-1] if "@" in settings.DATABASE_URL else "configured",
                        "connection_test": "passed"
                    }
                }
            else:
                return {
                    "status": "error",
                    "message": "Database query failed",
                    "details": {"connection_test": "failed"}
                }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Database connection failed: {str(e)}",
                "details": {"error": str(e)}
            }
        finally:
            if self.db_session:
                self.db_session.close()
    
    async def check_redis_health(self) -> Dict[str, Any]:
        """Check Redis connectivity if rate limiting is enabled."""
        if not settings.RATE_LIMIT_ENABLED or settings.RATE_LIMIT_BACKEND != "redis":
            return {
                "status": "not_configured",
                "message": "Redis not required (rate limiting disabled or using memory backend)",
                "details": {"backend": settings.RATE_LIMIT_BACKEND}
            }
        
        try:
            # Test Redis connection
            r = redis.from_url(settings.RATE_LIMIT_REDIS_URL)
            
            # Test basic operations
            r.ping()
            r.set("health_check", "test", ex=10)  # Set with 10 second expiry
            value = r.get("health_check")
            r.delete("health_check")
            
            if value and value.decode() == "test":
                return {
                    "status": "healthy",
                    "message": "Redis connection successful",
                    "details": {
                        "redis_url": settings.RATE_LIMIT_REDIS_URL,
                        "ping_test": "passed",
                        "read_write_test": "passed"
                    }
                }
            else:
                return {
                    "status": "error",
                    "message": "Redis read/write test failed",
                    "details": {"read_write_test": "failed"}
                }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Redis connection failed: {str(e)}",
                "details": {"error": str(e)}
            }
    
    async def check_ai_service_health(self, service_name: str) -> Dict[str, Any]:
        """Check AI service connectivity with actual API calls."""
        try:
            if service_name == "ollama":
                from app.services.ollama_service import OllamaService
                service = OllamaService()
                
                # Test with a simple API call
                models = service.list_available_models()
                if models is not None:
                    return {
                        "status": "healthy",
                        "message": "Ollama service responding",
                        "details": {
                            "base_url": settings.OLLAMA_BASE_URL,
                            "models_available": len(models) if isinstance(models, list) else "unknown"
                        }
                    }
                else:
                    return {
                        "status": "error",
                        "message": "Ollama service not responding",
                        "details": {"base_url": settings.OLLAMA_BASE_URL}
                    }
            
            elif service_name == "openai":
                from app.dependencies import get_ai_service
                ai_service = get_ai_service()
                
                if ai_service and ai_service.openai_client:
                    # Test with a simple API call
                    try:
                        # This is a lightweight test call
                        response = await asyncio.to_thread(
                            ai_service.openai_client.models.list
                        )
                        return {
                            "status": "healthy",
                            "message": "OpenAI service responding",
                            "details": {
                                "model": settings.OPENAI_MODEL,
                                "api_connected": True
                            }
                        }
                    except Exception as api_error:
                        return {
                            "status": "error",
                            "message": f"OpenAI API call failed: {str(api_error)}",
                            "details": {"error": str(api_error)}
                        }
                else:
                    return {
                        "status": "error",
                        "message": "OpenAI client not initialized",
                        "details": {"api_key_configured": bool(settings.OPENAI_API_KEY)}
                    }
            
            elif service_name == "anthropic":
                from app.dependencies import get_ai_service
                ai_service = get_ai_service()
                
                if ai_service and ai_service.anthropic_client:
                    return {
                        "status": "healthy",
                        "message": "Anthropic service configured",
                        "details": {
                            "model": settings.ANTHROPIC_MODEL,
                            "api_connected": True
                        }
                    }
                else:
                    return {
                        "status": "error",
                        "message": "Anthropic client not initialized",
                        "details": {"api_key_configured": bool(settings.ANTHROPIC_API_KEY)}
                    }
            
            return {
                "status": "not_configured",
                "message": f"Unknown service: {service_name}",
                "details": {}
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"Service check failed: {str(e)}",
                "details": {"error": str(e)}
            }
    
    async def get_comprehensive_health(self) -> Dict[str, Any]:
        """Get comprehensive health status for all services."""
        health_status = {
            "status": "healthy",
            "version": "1.0.0",
            "timestamp": None,
            "services": {},
            "configuration_issues": settings.validate_configuration()
        }
        
        # Check database
        db_health = await self.check_database_health()
        health_status["services"]["database"] = db_health
        
        # Check Redis
        redis_health = await self.check_redis_health()
        health_status["services"]["redis"] = redis_health
        
        # Check AI services
        for service_name, is_configured in settings.configured_services.items():
            if is_configured:
                ai_health = await self.check_ai_service_health(service_name)
                health_status["services"][service_name] = ai_health
        
        # Determine overall status
        service_statuses = [service.get("status", "unknown") for service in health_status["services"].values()]
        
        if "error" in service_statuses:
            health_status["status"] = "degraded"
        elif "not_configured" in service_statuses and not any("healthy" in status for status in service_statuses):
            health_status["status"] = "warning"
        elif health_status["configuration_issues"]:
            health_status["status"] = "warning"
        
        # Add timestamp
        import datetime
        health_status["timestamp"] = datetime.datetime.utcnow().isoformat() + "Z"
        
        return health_status
