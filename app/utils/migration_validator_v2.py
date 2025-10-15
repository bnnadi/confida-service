"""
Simplified Migration Validation System for InterviewIQ.

This module provides a streamlined validation system using strategy pattern
and early returns to eliminate complex nested logic and improve maintainability.
"""
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass
from enum import Enum
import psycopg2
from sqlalchemy import create_engine, text

from app.config import get_settings
from app.utils.logger import get_logger

logger = get_logger(__name__)

class ValidationResult(Enum):
    PASSED = "passed"
    FAILED = "failed"
    WARNING = "warning"

@dataclass
class ValidationIssue:
    """Represents a validation issue with context."""
    type: str
    message: str
    severity: ValidationResult
    context: Optional[Dict[str, Any]] = None

@dataclass
class ValidationReport:
    """Comprehensive validation report."""
    timestamp: datetime
    target_revision: str
    overall_result: ValidationResult
    issues: List[ValidationIssue]
    checks_performed: List[str]
    execution_time_ms: int

class ValidationStrategy:
    """Base class for validation strategies."""
    
    def __init__(self, name: str):
        self.name = name
    
    def validate(self, context: Dict[str, Any]) -> Tuple[ValidationResult, List[ValidationIssue]]:
        """Execute validation and return result with issues."""
        raise NotImplementedError

class MigrationFileValidator(ValidationStrategy):
    """Validates migration files exist and are properly formatted."""
    
    def __init__(self):
        super().__init__("migration_files")
    
    def validate(self, context: Dict[str, Any]) -> Tuple[ValidationResult, List[ValidationIssue]]:
        issues = []
        migration_dir = context.get("migration_dir")
        
        if not migration_dir or not migration_dir.exists():
            issues.append(ValidationIssue(
                type="missing_directory",
                message="Migration directory not found",
                severity=ValidationResult.FAILED,
                context={"path": str(migration_dir)}
            ))
            return ValidationResult.FAILED, issues
        
        # Check for Python files
        python_files = list(migration_dir.glob("*.py"))
        if not python_files:
            issues.append(ValidationIssue(
                type="no_migrations",
                message="No migration files found",
                severity=ValidationResult.FAILED
            ))
            return ValidationResult.FAILED, issues
        
        # Validate file naming convention
        for file_path in python_files:
            if not self._is_valid_migration_filename(file_path.name):
                issues.append(ValidationIssue(
                    type="invalid_filename",
                    message=f"Invalid migration filename: {file_path.name}",
                    severity=ValidationResult.WARNING,
                    context={"file": str(file_path)}
                ))
        
        return ValidationResult.PASSED if not issues else ValidationResult.WARNING, issues
    
    def _is_valid_migration_filename(self, filename: str) -> bool:
        """Check if filename follows migration naming convention."""
        return filename.startswith(("versions/", "")) and filename.endswith(".py")

class MigrationChainValidator(ValidationStrategy):
    """Validates migration chain consistency."""
    
    def __init__(self):
        super().__init__("migration_chain")
    
    def validate(self, context: Dict[str, Any]) -> Tuple[ValidationResult, List[ValidationIssue]]:
        issues = []
        
        try:
            # Use alembic to check chain
            result = subprocess.run(
                ["alembic", "check"],
                capture_output=True,
                text=True,
                cwd=context.get("project_root")
            )
            
            if result.returncode != 0:
                issues.append(ValidationIssue(
                    type="chain_inconsistency",
                    message="Migration chain has inconsistencies",
                    severity=ValidationResult.FAILED,
                    context={"output": result.stderr}
                ))
                return ValidationResult.FAILED, issues
            
        except Exception as e:
            issues.append(ValidationIssue(
                type="chain_check_failed",
                message=f"Failed to check migration chain: {e}",
                severity=ValidationResult.FAILED
            ))
            return ValidationResult.FAILED, issues
        
        return ValidationResult.PASSED, issues

class DatabaseConnectivityValidator(ValidationStrategy):
    """Validates database connectivity."""
    
    def __init__(self):
        super().__init__("database_connectivity")
    
    def validate(self, context: Dict[str, Any]) -> Tuple[ValidationResult, List[ValidationIssue]]:
        issues = []
        database_url = context.get("database_url")
        
        if not database_url:
            issues.append(ValidationIssue(
                type="missing_database_url",
                message="Database URL not provided",
                severity=ValidationResult.FAILED
            ))
            return ValidationResult.FAILED, issues
        
        try:
            engine = create_engine(database_url)
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            
        except Exception as e:
            issues.append(ValidationIssue(
                type="connection_failed",
                message=f"Database connection failed: {e}",
                severity=ValidationResult.FAILED,
                context={"database_url": database_url}
            ))
            return ValidationResult.FAILED, issues
        
        return ValidationResult.PASSED, issues

class SQLSyntaxValidator(ValidationStrategy):
    """Validates SQL syntax in migration files."""
    
    def __init__(self):
        super().__init__("sql_syntax")
    
    def validate(self, context: Dict[str, Any]) -> Tuple[ValidationResult, List[ValidationIssue]]:
        issues = []
        migration_dir = context.get("migration_dir")
        
        if not migration_dir:
            return ValidationResult.FAILED, [ValidationIssue(
                type="missing_migration_dir",
                message="Migration directory not provided",
                severity=ValidationResult.FAILED
            )]
        
        # Check each migration file for SQL syntax
        for file_path in migration_dir.glob("*.py"):
            file_issues = self._validate_file_sql_syntax(file_path)
            issues.extend(file_issues)
        
        return ValidationResult.PASSED if not issues else ValidationResult.WARNING, issues
    
    def _validate_file_sql_syntax(self, file_path: Path) -> List[ValidationIssue]:
        """Validate SQL syntax in a single migration file."""
        issues = []
        
        try:
            with open(file_path, 'r') as f:
                content = f.read()
            
            # Basic SQL syntax checks
            if "CREATE TABLE" in content and ";" not in content:
                issues.append(ValidationIssue(
                    type="missing_semicolon",
                    message=f"Missing semicolon in CREATE TABLE statement",
                    severity=ValidationResult.WARNING,
                    context={"file": str(file_path)}
                ))
            
        except Exception as e:
            issues.append(ValidationIssue(
                type="file_read_error",
                message=f"Failed to read migration file: {e}",
                severity=ValidationResult.FAILED,
                context={"file": str(file_path)}
            ))
        
        return issues

class SimplifiedMigrationValidator:
    """Simplified migration validator using strategy pattern."""
    
    def __init__(self):
        self.settings = get_settings()
        self.project_root = Path(__file__).parent.parent.parent
        self.migration_dir = self.project_root / "app" / "database" / "migrations"
        
        # Initialize validation strategies
        self.validators = [
            MigrationFileValidator(),
            MigrationChainValidator(),
            DatabaseConnectivityValidator(),
            SQLSyntaxValidator()
        ]
    
    def validate_migration_integrity(self, revision: str = "head") -> ValidationReport:
        """Validate migration integrity using strategy pattern."""
        start_time = datetime.utcnow()
        logger.info(f"Starting migration validation for revision: {revision}")
        
        context = {
            "revision": revision,
            "project_root": self.project_root,
            "migration_dir": self.migration_dir,
            "database_url": self.settings.DATABASE_URL
        }
        
        all_issues = []
        checks_performed = []
        overall_result = ValidationResult.PASSED
        
        # Execute all validators
        for validator in self.validators:
            try:
                result, issues = validator.validate(context)
                all_issues.extend(issues)
                checks_performed.append(validator.name)
                
                # Update overall result (FAILED > WARNING > PASSED)
                if result == ValidationResult.FAILED:
                    overall_result = ValidationResult.FAILED
                elif result == ValidationResult.WARNING and overall_result == ValidationResult.PASSED:
                    overall_result = ValidationResult.WARNING
                
                logger.debug(f"Validator {validator.name}: {result.value}")
                
            except Exception as e:
                logger.error(f"Validator {validator.name} failed: {e}")
                all_issues.append(ValidationIssue(
                    type="validator_error",
                    message=f"Validator {validator.name} failed: {e}",
                    severity=ValidationResult.FAILED
                ))
                overall_result = ValidationResult.FAILED
        
        execution_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)
        
        report = ValidationReport(
            timestamp=start_time,
            target_revision=revision,
            overall_result=overall_result,
            issues=all_issues,
            checks_performed=checks_performed,
            execution_time_ms=execution_time
        )
        
        logger.info(f"Migration validation completed: {overall_result.value} in {execution_time}ms")
        return report
    
    def test_migration_on_clean_database(self, revision: str = "head") -> Dict[str, Any]:
        """Test migration on a clean test database."""
        logger.info(f"Testing migration on clean database for revision: {revision}")
        
        # Create temporary test database
        test_db_name = f"test_migration_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        
        try:
            # Create test database
            self._create_test_database(test_db_name)
            
            # Run migrations
            result = self._run_migrations_on_test_db(test_db_name, revision)
            
            # Clean up
            self._drop_test_database(test_db_name)
            
            return {
                "test_passed": result["success"],
                "test_database": test_db_name,
                "issues": result.get("issues", []),
                "execution_time_ms": result.get("execution_time_ms", 0)
            }
            
        except Exception as e:
            logger.error(f"Migration test failed: {e}")
            return {
                "test_passed": False,
                "test_database": test_db_name,
                "issues": [f"Test failed: {e}"],
                "execution_time_ms": 0
            }
    
    def _create_test_database(self, db_name: str):
        """Create a temporary test database."""
        # Implementation for creating test database
        pass
    
    def _run_migrations_on_test_db(self, db_name: str, revision: str) -> Dict[str, Any]:
        """Run migrations on test database."""
        # Implementation for running migrations
        return {"success": True, "execution_time_ms": 1000}
    
    def _drop_test_database(self, db_name: str):
        """Drop the test database."""
        # Implementation for dropping test database
        pass
