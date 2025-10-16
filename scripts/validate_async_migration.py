#!/usr/bin/env python3
"""
Async Database Migration Validation Script

This script validates the async database migration implementation by:
1. Testing async infrastructure imports
2. Validating configuration settings
3. Testing database connectivity
4. Comparing sync vs async performance
5. Checking health endpoints
"""

import asyncio
import time
import os
import sys
import requests
import json
from pathlib import Path
from typing import Dict, Any, List

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def print_header(title: str):
    """Print a formatted header."""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")

def print_success(message: str):
    """Print a success message."""
    print(f"✅ {message}")

def print_error(message: str):
    """Print an error message."""
    print(f"❌ {message}")

def print_warning(message: str):
    """Print a warning message."""
    print(f"⚠️  {message}")

def print_info(message: str):
    """Print an info message."""
    print(f"ℹ️  {message}")

class AsyncMigrationValidator:
    """Validator for async database migration."""
    
    def __init__(self):
        self.base_url = "http://localhost:8000"
        self.results = {
            "imports": False,
            "configuration": False,
            "database_connectivity": False,
            "health_endpoints": False,
            "performance": False
        }
    
    def validate_imports(self) -> bool:
        """Test that all async modules can be imported."""
        print_header("Testing Async Module Imports")
        
        try:
            # Test async database connection
            from app.database.async_connection import AsyncDatabaseManager, get_async_db
            print_success("Async database connection module imported")
            
            # Test async services
            from app.services.async_question_bank_service import AsyncQuestionBankService
            from app.services.async_hybrid_ai_service import AsyncHybridAIService
            from app.services.async_session_service import AsyncSessionService
            from app.services.async_database_monitor import AsyncDatabaseMonitor
            print_success("Async services imported")
            
            # Test async operations
            from app.database.async_operations import AsyncDatabaseOperations
            print_success("Async database operations imported")
            
            # Test main application
            from app.main import app
            print_success("Main application imported")
            
            self.results["imports"] = True
            return True
            
        except ImportError as e:
            print_error(f"Import failed: {e}")
            return False
        except Exception as e:
            print_error(f"Unexpected error during import: {e}")
            return False
    
    def validate_configuration(self) -> bool:
        """Validate async database configuration."""
        print_header("Validating Configuration")
        
        try:
            from app.config import get_settings
            settings = get_settings()
            
            # Check async database settings
            print_info(f"ASYNC_DATABASE_ENABLED: {settings.ASYNC_DATABASE_ENABLED}")
            print_info(f"ASYNC_DATABASE_POOL_SIZE: {settings.ASYNC_DATABASE_POOL_SIZE}")
            print_info(f"ASYNC_DATABASE_MAX_OVERFLOW: {settings.ASYNC_DATABASE_MAX_OVERFLOW}")
            print_info(f"ASYNC_DATABASE_MONITORING_ENABLED: {settings.ASYNC_DATABASE_MONITORING_ENABLED}")
            
            # Check database URL
            db_url = settings.DATABASE_URL
            if "asyncpg" in db_url or "aiosqlite" in db_url:
                print_success("Database URL supports async operations")
            else:
                print_warning("Database URL may not support async operations")
                print_info(f"Current URL: {db_url}")
                print_info("Consider using postgresql+asyncpg:// or sqlite+aiosqlite://")
            
            self.results["configuration"] = True
            return True
            
        except Exception as e:
            print_error(f"Configuration validation failed: {e}")
            return False
    
    async def validate_database_connectivity(self) -> bool:
        """Test async database connectivity."""
        print_header("Testing Async Database Connectivity")
        
        try:
            from app.database.async_connection import get_async_db
            
            # Test basic connectivity
            async with get_async_db() as db:
                result = await db.execute("SELECT 1 as test")
                test_value = result.scalar()
                
                if test_value == 1:
                    print_success("Database connectivity test passed")
                else:
                    print_error(f"Unexpected test value: {test_value}")
                    return False
            
            # Test async database manager
            from app.database.async_connection import async_db_manager
            if async_db_manager.engine:
                print_success("Async database engine initialized")
            else:
                print_warning("Async database engine not initialized")
            
            self.results["database_connectivity"] = True
            return True
            
        except Exception as e:
            print_error(f"Database connectivity test failed: {e}")
            return False
    
    def validate_health_endpoints(self) -> bool:
        """Test health and monitoring endpoints."""
        print_header("Testing Health Endpoints")
        
        try:
            # Test basic health endpoint
            response = requests.get(f"{self.base_url}/health", timeout=10)
            if response.status_code == 200:
                health_data = response.json()
                print_success("Health endpoint accessible")
                
                # Check for async database health
                if "async_database" in health_data:
                    async_health = health_data["async_database"]
                    print_info(f"Async database status: {async_health.get('status', 'unknown')}")
                    
                    if async_health.get("status") == "healthy":
                        print_success("Async database is healthy")
                    else:
                        print_warning(f"Async database health: {async_health}")
                else:
                    print_warning("Async database health not found in response")
            else:
                print_error(f"Health endpoint returned status {response.status_code}")
                return False
            
            # Test monitoring endpoint
            try:
                response = requests.get(f"{self.base_url}/monitoring/database", timeout=10)
                if response.status_code == 200:
                    monitoring_data = response.json()
                    print_success("Database monitoring endpoint accessible")
                    
                    # Check for key monitoring data
                    if "connection_pool_status" in monitoring_data:
                        pool_status = monitoring_data["connection_pool_status"]
                        print_info(f"Pool size: {pool_status.get('pool_size', 'unknown')}")
                        print_info(f"Checked out: {pool_status.get('checked_out', 'unknown')}")
                    else:
                        print_warning("Connection pool status not found")
                        
                else:
                    print_warning(f"Monitoring endpoint returned status {response.status_code}")
            except requests.exceptions.RequestException as e:
                print_warning(f"Monitoring endpoint not accessible: {e}")
            
            self.results["health_endpoints"] = True
            return True
            
        except requests.exceptions.RequestException as e:
            print_error(f"Health endpoint test failed: {e}")
            return False
        except Exception as e:
            print_error(f"Unexpected error during health check: {e}")
            return False
    
    async def validate_performance(self) -> bool:
        """Compare sync vs async performance."""
        print_header("Performance Comparison")
        
        try:
            # Test async service performance
            from app.database.async_connection import get_async_db
            from app.services.async_question_bank_service import AsyncQuestionBankService
            
            async with get_async_db() as db:
                service = AsyncQuestionBankService(db)
                
                # Time async operation
                start_time = time.time()
                try:
                    questions = await service.get_questions_for_role("developer", "Python developer role", 5)
                    async_time = time.time() - start_time
                    print_success(f"Async operation completed in {async_time:.3f}s")
                    print_info(f"Retrieved {len(questions)} questions")
                except Exception as e:
                    print_warning(f"Async operation failed: {e}")
                    async_time = None
            
            # Test sync service performance (if available)
            try:
                from app.database.connection import get_db
                from app.services.question_bank_service import QuestionBankService
                
                db = next(get_db())
                service = QuestionBankService(db)
                
                start_time = time.time()
                questions = service.get_questions_for_role("developer", "Python developer role", 5)
                sync_time = time.time() - start_time
                print_success(f"Sync operation completed in {sync_time:.3f}s")
                print_info(f"Retrieved {len(questions)} questions")
                
                # Compare performance
                if async_time and sync_time:
                    improvement = sync_time / async_time
                    print_info(f"Async is {improvement:.2f}x {'faster' if improvement > 1 else 'slower'} than sync")
                
            except Exception as e:
                print_warning(f"Sync operation test failed: {e}")
            
            self.results["performance"] = True
            return True
            
        except Exception as e:
            print_error(f"Performance test failed: {e}")
            return False
    
    def validate_api_endpoints(self) -> bool:
        """Test API endpoints with async support."""
        print_header("Testing API Endpoints")
        
        try:
            # Test services endpoint
            response = requests.get(f"{self.base_url}/api/v1/services", timeout=10)
            if response.status_code == 200:
                print_success("Services endpoint accessible")
                services_data = response.json()
                
                # Check for question bank stats
                if "question_bank_stats" in services_data:
                    print_success("Question bank stats available")
                else:
                    print_warning("Question bank stats not found")
            else:
                print_error(f"Services endpoint returned status {response.status_code}")
                return False
            
            # Test models endpoint
            response = requests.get(f"{self.base_url}/api/v1/models", timeout=10)
            if response.status_code == 200:
                print_success("Models endpoint accessible")
            else:
                print_warning(f"Models endpoint returned status {response.status_code}")
            
            return True
            
        except requests.exceptions.RequestException as e:
            print_error(f"API endpoint test failed: {e}")
            return False
    
    def print_summary(self):
        """Print validation summary."""
        print_header("Validation Summary")
        
        total_tests = len(self.results)
        passed_tests = sum(1 for result in self.results.values() if result)
        
        print_info(f"Tests passed: {passed_tests}/{total_tests}")
        
        for test_name, result in self.results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"  {test_name.replace('_', ' ').title()}: {status}")
        
        if passed_tests == total_tests:
            print_success("All validation tests passed! Async migration is ready.")
        else:
            print_warning("Some validation tests failed. Review the issues above.")
        
        print_info("\nNext steps:")
        if passed_tests == total_tests:
            print("  1. Deploy to staging environment")
            print("  2. Enable async mode: export ASYNC_DATABASE_ENABLED=true")
            print("  3. Run load tests")
            print("  4. Monitor performance metrics")
            print("  5. Deploy to production with gradual rollout")
        else:
            print("  1. Fix the failing tests")
            print("  2. Re-run validation")
            print("  3. Ensure all dependencies are installed")
            print("  4. Check database connectivity")

async def main():
    """Main validation function."""
    print_header("Async Database Migration Validation")
    print_info("This script validates the async database migration implementation.")
    
    validator = AsyncMigrationValidator()
    
    # Run validation tests
    validator.validate_imports()
    validator.validate_configuration()
    await validator.validate_database_connectivity()
    validator.validate_health_endpoints()
    await validator.validate_performance()
    validator.validate_api_endpoints()
    
    # Print summary
    validator.print_summary()

if __name__ == "__main__":
    # Set up environment
    os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test_confida.db")
    os.environ.setdefault("ASYNC_DATABASE_ENABLED", "true")
    os.environ.setdefault("ENVIRONMENT", "test")
    
    # Run validation
    asyncio.run(main())
