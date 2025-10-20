"""
Database Operation Handler for unified async/sync database operations.
Eliminates duplicate code paths and simplifies database interaction patterns.
"""

from typing import Dict, Any, Optional, Callable
from fastapi import HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.connection import get_db
from app.database.async_connection import get_async_db
from app.dependencies import get_ai_service, get_async_ai_service
from app.config import get_settings
from app.utils.logger import get_logger

logger = get_logger(__name__)

class DatabaseOperationHandler:
    """Unified handler for database operations with automatic async/sync detection."""
    
    def __init__(self, use_async: Optional[bool] = None):
        self.settings = get_settings()
        self.use_async = use_async if use_async is not None else self.settings.ASYNC_DATABASE_ENABLED
    
    async def handle_operation(self, operation_type: str, **kwargs) -> Any:
        """Handle database operation with direct method calls."""
        # Direct method mapping for better performance
        handlers = {
            "parse_jd": self._handle_parse_jd_operation,
            "analyze_answer": self._handle_analyze_answer_operation,
            "get_services": self._handle_get_services_operation,
            "list_models": self._handle_list_models_operation,
            "pull_model": self._handle_pull_model_operation
        }
        
        handler = handlers.get(operation_type)
        if not handler:
            raise HTTPException(status_code=400, detail=f"Unknown operation: {operation_type}")
        
        return await self._call_service_method(handler, **kwargs)
    
    async def _call_service_method(self, method: Callable, **kwargs) -> Any:
        """Call service method with automatic async/sync detection."""
        if self.use_async:
            return await self._execute_async(method, **kwargs)
        else:
            return await self._execute_sync(method, **kwargs)
    
    
    async def _execute_async(self, handler: Callable, **kwargs) -> Any:
        """Execute operation using async database."""
        try:
            async with get_async_db() as db:
                ai_service = await get_async_ai_service(db)
                if not ai_service:
                    raise HTTPException(status_code=500, detail="AI service not available")
                
                return await handler(ai_service=ai_service, db=db, **kwargs)
                
        except Exception as e:
            logger.error(f"Error in async operation: {e}")
            raise HTTPException(status_code=500, detail=f"Database operation failed: {str(e)}")
    
    async def _execute_sync(self, handler: Callable, **kwargs) -> Any:
        """Execute operation using sync database."""
        try:
            db = next(get_db())
            ai_service = get_ai_service(db)
            if not ai_service:
                raise HTTPException(status_code=500, detail="AI service not available")
            
            return await handler(ai_service=ai_service, db=db, **kwargs)
            
        except Exception as e:
            logger.error(f"Error in sync operation: {e}")
            raise HTTPException(status_code=500, detail=f"Database operation failed: {str(e)}")
    
    async def _handle_parse_jd_operation(self, ai_service: Any, db: Any, **kwargs) -> Any:
        """Handle parse job description operation with unified logic."""
        request = kwargs.get('request')
        validated_service = kwargs.get('validated_service')
        current_user = kwargs.get('current_user')
        
        if not all([request, validated_service, current_user]):
            raise HTTPException(status_code=400, detail="Missing required parameters for parse_jd operation")
        
        # Unified service call that works for both async and sync
        return await self._call_service_method(
            ai_service, 'generate_interview_questions',
            role=request.role,
            job_description=request.job_description,
            preferred_service=validated_service
        )
    
    async def _handle_analyze_answer_operation(self, ai_service: Any, db: Any, **kwargs) -> Any:
        """Handle analyze answer operation with unified logic."""
        request = kwargs.get('request')
        validated_service = kwargs.get('validated_service')
        question_id = kwargs.get('question_id')
        current_user = kwargs.get('current_user')
        
        if not all([request, validated_service, question_id, current_user]):
            raise HTTPException(status_code=400, detail="Missing required parameters for analyze_answer operation")
        
        # Unified service call that works for both async and sync
        return await self._call_service_method(
            ai_service, 'analyze_answer',
            job_description=request.job_description,
            question=request.question,
            answer=request.answer,
            preferred_service=validated_service
        )
    
    async def _handle_get_services_operation(self, ai_service: Any, db: Any, **kwargs) -> Any:
        """Handle get available services operation with unified logic."""
        services = await self._call_service_method(ai_service, 'get_available_services')
        
        # Return consistent format for both async and sync
        return {
            "available_services": services,
            "service_priority": await self._call_service_method(ai_service, 'get_service_priority'),
            "question_bank_stats": await self._call_service_method(ai_service, 'get_question_bank_stats')
        }
    
    async def _handle_list_models_operation(self, ai_service: Any, db: Any, **kwargs) -> Any:
        """Handle list models operation with unified logic."""
        models = await self._call_service_method(ai_service, 'list_models', "ollama")
        return {"models": models}
    
    async def _handle_pull_model_operation(self, ai_service: Any, db: Any, **kwargs) -> Any:
        """Handle pull model operation with unified logic."""
        model_name = kwargs.get('model_name')
        if not model_name:
            raise HTTPException(status_code=400, detail="Model name is required")
        
        result = await self._call_service_method(ai_service, 'pull_model', "ollama", model_name)
        return {"message": f"Model {model_name} pulled successfully", "result": result}
    
    async def _call_service_method(self, ai_service: Any, method_name: str, *args, **kwargs) -> Any:
        """Unified method to call service methods for both async and sync services."""
        method = getattr(ai_service, method_name)
        
        # Check if method is async and call accordingly
        import asyncio
        if asyncio.iscoroutinefunction(method):
            return await method(*args, **kwargs)
        else:
            return method(*args, **kwargs)
