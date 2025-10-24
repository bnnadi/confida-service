"""
Unified Response Formatter for Confida

This module consolidates all response formatting logic into a single,
comprehensive response formatter that eliminates redundancy and provides
consistent response formatting across the entire application.
"""
from typing import Any, Dict, List, Optional, Union
from datetime import datetime
from fastapi import HTTPException
from app.utils.logger import get_logger

logger = get_logger(__name__)

class ResponseFormatter:
    """Unified response formatter for consistent API responses."""
    
    def __init__(self):
        self.default_success_code = 200
        self.default_error_code = 400
    
    def format_success_response(
        self, 
        data: Any = None, 
        message: str = "Success", 
        status_code: int = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Format a successful response."""
        response = {
            "success": True,
            "message": message,
            "timestamp": datetime.now().isoformat(),
            "status_code": status_code or self.default_success_code
        }
        
        if data is not None:
            response["data"] = data
        
        if metadata:
            response["metadata"] = metadata
        
        return response
    
    def format_error_response(
        self, 
        error: Union[str, Exception], 
        status_code: int = None,
        details: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Format an error response."""
        error_message = str(error) if isinstance(error, Exception) else error
        
        response = {
            "success": False,
            "error": error_message,
            "timestamp": datetime.now().isoformat(),
            "status_code": status_code or self.default_error_code
        }
        
        if details:
            response["details"] = details
        
        return response
    
    def format_pagination_response(
        self,
        data: List[Any],
        page: int,
        page_size: int,
        total: int,
        message: str = "Success"
    ) -> Dict[str, Any]:
        """Format a paginated response."""
        total_pages = (total + page_size - 1) // page_size
        
        return {
            "success": True,
            "message": message,
            "data": data,
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total": total,
                "total_pages": total_pages,
                "has_next": page < total_pages,
                "has_prev": page > 1
            },
            "timestamp": datetime.now().isoformat(),
            "status_code": 200
        }
    
    def format_analysis_response(
        self,
        analysis: Any,
        score: Optional[Dict[str, float]] = None,
        suggestions: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Format an analysis response."""
        response = {
            "success": True,
            "message": "Analysis completed successfully",
            "analysis": analysis,
            "timestamp": datetime.now().isoformat(),
            "status_code": 200
        }
        
        if score:
            response["score"] = score
        
        if suggestions:
            response["suggestions"] = suggestions
        
        if metadata:
            response["metadata"] = metadata
        
        return response
    
    def format_question_response(
        self,
        questions: List[str],
        role: str,
        job_description: str,
        service_used: str,
        question_bank_count: int = 0,
        ai_generated_count: int = 0,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Format a question generation response."""
        response = {
            "success": True,
            "message": "Questions generated successfully",
            "questions": questions,
            "role": role,
            "job_description": job_description,
            "service_used": service_used,
            "question_counts": {
                "total": len(questions),
                "from_database": question_bank_count,
                "ai_generated": ai_generated_count
            },
            "timestamp": datetime.now().isoformat(),
            "status_code": 200
        }
        
        if metadata:
            response["metadata"] = metadata
        
        return response
    
    def format_file_response(
        self,
        file_info: Dict[str, Any],
        message: str = "File operation completed successfully"
    ) -> Dict[str, Any]:
        """Format a file operation response."""
        return {
            "success": True,
            "message": message,
            "file": file_info,
            "timestamp": datetime.now().isoformat(),
            "status_code": 200
        }
    
    def format_health_response(
        self,
        health_data: Dict[str, Any],
        message: str = "Health check completed"
    ) -> Dict[str, Any]:
        """Format a health check response."""
        return {
            "success": True,
            "message": message,
            "health": health_data,
            "timestamp": datetime.now().isoformat(),
            "status_code": 200
        }
    
    def format_validation_response(
        self,
        is_valid: bool,
        errors: Optional[List[str]] = None,
        warnings: Optional[List[str]] = None,
        data: Optional[Any] = None
    ) -> Dict[str, Any]:
        """Format a validation response."""
        response = {
            "success": is_valid,
            "message": "Validation completed",
            "is_valid": is_valid,
            "timestamp": datetime.now().isoformat(),
            "status_code": 200 if is_valid else 400
        }
        
        if errors:
            response["errors"] = errors
        
        if warnings:
            response["warnings"] = warnings
        
        if data is not None:
            response["data"] = data
        
        return response
    
    def format_service_response(
        self,
        service_name: str,
        operation: str,
        result: Any,
        execution_time: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Format a service operation response."""
        response = {
            "success": True,
            "message": f"{service_name} {operation} completed successfully",
            "service": service_name,
            "operation": operation,
            "result": result,
            "timestamp": datetime.now().isoformat(),
            "status_code": 200
        }
        
        if execution_time is not None:
            response["execution_time"] = execution_time
        
        if metadata:
            response["metadata"] = metadata
        
        return response
    
    def format_fallback_response(
        self,
        operation: str,
        fallback_data: Any,
        reason: str = "Service unavailable"
    ) -> Dict[str, Any]:
        """Format a fallback response."""
        return {
            "success": True,
            "message": f"Fallback response for {operation}",
            "fallback": True,
            "reason": reason,
            "data": fallback_data,
            "timestamp": datetime.now().isoformat(),
            "status_code": 200
        }

# Global response formatter instance
response_formatter = ResponseFormatter()

# Convenience functions
def format_success(data: Any = None, message: str = "Success", **kwargs) -> Dict[str, Any]:
    """Format a successful response."""
    return response_formatter.format_success_response(data, message, **kwargs)

def format_error(error: Union[str, Exception], **kwargs) -> Dict[str, Any]:
    """Format an error response."""
    return response_formatter.format_error_response(error, **kwargs)

def format_pagination(data: List[Any], page: int, page_size: int, total: int, **kwargs) -> Dict[str, Any]:
    """Format a paginated response."""
    return response_formatter.format_pagination_response(data, page, page_size, total, **kwargs)

def format_analysis(analysis: Any, **kwargs) -> Dict[str, Any]:
    """Format an analysis response."""
    return response_formatter.format_analysis_response(analysis, **kwargs)

def format_questions(questions: List[str], role: str, job_description: str, service_used: str, **kwargs) -> Dict[str, Any]:
    """Format a question generation response."""
    return response_formatter.format_question_response(questions, role, job_description, service_used, **kwargs)

def format_file(file_info: Dict[str, Any], **kwargs) -> Dict[str, Any]:
    """Format a file operation response."""
    return response_formatter.format_file_response(file_info, **kwargs)

def format_health(health_data: Dict[str, Any], **kwargs) -> Dict[str, Any]:
    """Format a health check response."""
    return response_formatter.format_health_response(health_data, **kwargs)

def format_validation(is_valid: bool, **kwargs) -> Dict[str, Any]:
    """Format a validation response."""
    return response_formatter.format_validation_response(is_valid, **kwargs)

def format_service(service_name: str, operation: str, result: Any, **kwargs) -> Dict[str, Any]:
    """Format a service operation response."""
    return response_formatter.format_service_response(service_name, operation, result, **kwargs)

def format_fallback(operation: str, fallback_data: Any, **kwargs) -> Dict[str, Any]:
    """Format a fallback response."""
    return response_formatter.format_fallback_response(operation, fallback_data, **kwargs)
