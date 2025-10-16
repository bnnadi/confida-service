"""
Enhanced Migration Validation System for InterviewIQ

This module provides a comprehensive validation system that combines the best features
of both the original and v2 migration validators with improved error handling and reporting.
"""
import os
import sys
import subprocess
import tempfile
import shutil
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass
from enum import Enum
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.config import get_settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


class ValidationResult(Enum):
    PASSED = "passed"
    FAILED = "failed"
    WARNING = "warning"
    SKIPPED = "skipped"


@dataclass
class ValidationIssue:
    """Represents a validation issue with context."""
    type: str
    message: str
    severity: ValidationResult
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    suggestion: Optional[str] = None


@dataclass
class ValidationReport:
    """Comprehensive validation report."""
    timestamp: datetime
    total_checks: int
    passed: int
    failed: int
    warnings: int
    skipped: int
    issues: List[ValidationIssue]
    summary: str
    recommendations: List[str]


class MigrationValidator:
    """Enhanced migration validation and testing system."""
    
    def __init__(self):
        self.settings = get_settings()
        self.project_root = Path(__file__).parent.parent.parent
        self.migrations_dir = self.project_root / "app" / "database" / "migrations" / "versions"
        self.validation_issues = []
        self.validation_warnings = []
        
        # Validation configuration
        self.config = {
            'database': {
                'test_db_name': 'interviewiq_test_validation',
                'timeout': 30,
                'max_retries': 3
            },
            'migrations': {
                'max_file_size': 1024 * 1024,  # 1MB
                'required_imports': ['alembic', 'sqlalchemy'],
                'forbidden_patterns': [
                    r'DROP\s+TABLE\s+IF\s+EXISTS',
                    r'TRUNCATE\s+TABLE',
                    r'DELETE\s+FROM\s+\w+\s+WHERE\s+1=1'
                ]
            },
            'validation': {
                'check_syntax': True,
                'check_imports': True,
                'check_database_connectivity': True,
                'check_migration_order': True,
                'check_rollback_safety': True
            }
        }
    
    def validate_all(self) -> ValidationReport:
        """Run comprehensive migration validation."""
        logger.info("Starting comprehensive migration validation")
        start_time = datetime.now()
        
        # Reset validation state
        self.validation_issues = []
        self.validation_warnings = []
        
        # Run all validation checks
        checks = [
            self._validate_migration_files,
            self._validate_database_connectivity,
            self._validate_migration_syntax,
            self._validate_migration_order,
            self._validate_rollback_safety,
            self._validate_imports,
            self._validate_file_sizes
        ]
        
        total_checks = len(checks)
        passed = 0
        failed = 0
        warnings = 0
        skipped = 0
        
        for check in checks:
            try:
                result = check()
                if result == ValidationResult.PASSED:
                    passed += 1
                elif result == ValidationResult.FAILED:
                    failed += 1
                elif result == ValidationResult.WARNING:
                    warnings += 1
                else:
                    skipped += 1
            except Exception as e:
                logger.error(f"Validation check failed: {e}")
                failed += 1
                self.validation_issues.append(ValidationIssue(
                    type="validation_error",
                    message=f"Check failed with exception: {str(e)}",
                    severity=ValidationResult.FAILED
                ))
        
        # Generate report
        report = self._generate_validation_report(
            start_time, total_checks, passed, failed, warnings, skipped
        )
        
        logger.info(f"Validation completed: {passed} passed, {failed} failed, {warnings} warnings")
        return report
    
    def _validate_migration_files(self) -> ValidationResult:
        """Validate migration file structure and naming."""
        logger.info("Validating migration files")
        
        if not self.migrations_dir.exists():
            self.validation_issues.append(ValidationIssue(
                type="missing_directory",
                message="Migrations directory does not exist",
                severity=ValidationResult.FAILED,
                file_path=str(self.migrations_dir)
            ))
            return ValidationResult.FAILED
        
        migration_files = list(self.migrations_dir.glob("*.py"))
        if not migration_files:
            self.validation_issues.append(ValidationIssue(
                type="no_migrations",
                message="No migration files found",
                severity=ValidationResult.WARNING,
                file_path=str(self.migrations_dir)
            ))
            return ValidationResult.WARNING
        
        # Check file naming convention
        invalid_files = []
        for file_path in migration_files:
            if not self._is_valid_migration_filename(file_path.name):
                invalid_files.append(file_path.name)
        
        if invalid_files:
            self.validation_issues.append(ValidationIssue(
                type="invalid_naming",
                message=f"Invalid migration file names: {', '.join(invalid_files)}",
                severity=ValidationResult.WARNING,
                suggestion="Migration files should follow the pattern: {revision}_{description}.py"
            ))
            return ValidationResult.WARNING
        
        logger.info(f"Found {len(migration_files)} migration files")
        return ValidationResult.PASSED
    
    def _validate_database_connectivity(self) -> ValidationResult:
        """Validate database connectivity and permissions."""
        if not self.config['validation']['check_database_connectivity']:
            return ValidationResult.SKIPPED
        
        logger.info("Validating database connectivity")
        
        try:
            # Test connection to main database
            engine = create_engine(self.settings.DATABASE_URL)
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            
            # Test connection to test database
            test_db_url = self._get_test_database_url()
            test_engine = create_engine(test_db_url)
            with test_engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            
            logger.info("Database connectivity validation passed")
            return ValidationResult.PASSED
            
        except Exception as e:
            self.validation_issues.append(ValidationIssue(
                type="database_connectivity",
                message=f"Database connection failed: {str(e)}",
                severity=ValidationResult.FAILED,
                suggestion="Check database configuration and ensure database is running"
            ))
            return ValidationResult.FAILED
    
    def _validate_migration_syntax(self) -> ValidationResult:
        """Validate Python syntax of migration files."""
        if not self.config['validation']['check_syntax']:
            return ValidationResult.SKIPPED
        
        logger.info("Validating migration syntax")
        
        migration_files = list(self.migrations_dir.glob("*.py"))
        syntax_errors = []
        
        for file_path in migration_files:
            try:
                with open(file_path, 'r') as f:
                    content = f.read()
                
                # Check Python syntax
                compile(content, file_path, 'exec')
                
            except SyntaxError as e:
                syntax_errors.append(f"{file_path.name}:{e.lineno}: {e.msg}")
            except Exception as e:
                syntax_errors.append(f"{file_path.name}: {str(e)}")
        
        if syntax_errors:
            self.validation_issues.append(ValidationIssue(
                type="syntax_error",
                message=f"Syntax errors found: {'; '.join(syntax_errors)}",
                severity=ValidationResult.FAILED,
                suggestion="Fix syntax errors before running migrations"
            ))
            return ValidationResult.FAILED
        
        logger.info("Migration syntax validation passed")
        return ValidationResult.PASSED
    
    def _validate_migration_order(self) -> ValidationResult:
        """Validate migration revision order and dependencies."""
        if not self.config['validation']['check_migration_order']:
            return ValidationResult.SKIPPED
        
        logger.info("Validating migration order")
        
        migration_files = list(self.migrations_dir.glob("*.py"))
        revisions = []
        
        for file_path in migration_files:
            try:
                with open(file_path, 'r') as f:
                    content = f.read()
                
                # Extract revision ID
                revision_match = re.search(r'revision\s*=\s*[\'"]([^\'"]+)[\'"]', content)
                if revision_match:
                    revisions.append((file_path.name, revision_match.group(1)))
                
            except Exception as e:
                self.validation_warnings.append(ValidationIssue(
                    type="revision_extraction",
                    message=f"Could not extract revision from {file_path.name}: {str(e)}",
                    severity=ValidationResult.WARNING,
                    file_path=str(file_path)
                ))
        
        if len(revisions) < 2:
            logger.info("Not enough migrations to validate order")
            return ValidationResult.PASSED
        
        # Check for duplicate revisions
        revision_ids = [rev[1] for rev in revisions]
        duplicates = [rev for rev in revision_ids if revision_ids.count(rev) > 1]
        
        if duplicates:
            self.validation_issues.append(ValidationIssue(
                type="duplicate_revision",
                message=f"Duplicate revision IDs found: {', '.join(set(duplicates))}",
                severity=ValidationResult.FAILED,
                suggestion="Ensure each migration has a unique revision ID"
            ))
            return ValidationResult.FAILED
        
        logger.info("Migration order validation passed")
        return ValidationResult.PASSED
    
    def _validate_rollback_safety(self) -> ValidationResult:
        """Validate that migrations can be safely rolled back."""
        if not self.config['validation']['check_rollback_safety']:
            return ValidationResult.SKIPPED
        
        logger.info("Validating rollback safety")
        
        migration_files = list(self.migrations_dir.glob("*.py"))
        unsafe_migrations = []
        
        for file_path in migration_files:
            try:
                with open(file_path, 'r') as f:
                    content = f.read()
                
                # Check for dangerous patterns
                for pattern in self.config['migrations']['forbidden_patterns']:
                    if re.search(pattern, content, re.IGNORECASE):
                        unsafe_migrations.append(f"{file_path.name}: {pattern}")
                
            except Exception as e:
                self.validation_warnings.append(ValidationIssue(
                    type="rollback_check",
                    message=f"Could not check rollback safety for {file_path.name}: {str(e)}",
                    severity=ValidationResult.WARNING,
                    file_path=str(file_path)
                ))
        
        if unsafe_migrations:
            self.validation_issues.append(ValidationIssue(
                type="unsafe_migration",
                message=f"Potentially unsafe migrations found: {'; '.join(unsafe_migrations)}",
                severity=ValidationResult.WARNING,
                suggestion="Review migrations for data loss risks before deployment"
            ))
            return ValidationResult.WARNING
        
        logger.info("Rollback safety validation passed")
        return ValidationResult.PASSED
    
    def _validate_imports(self) -> ValidationResult:
        """Validate required imports in migration files."""
        if not self.config['validation']['check_imports']:
            return ValidationResult.SKIPPED
        
        logger.info("Validating migration imports")
        
        migration_files = list(self.migrations_dir.glob("*.py"))
        missing_imports = []
        
        for file_path in migration_files:
            try:
                with open(file_path, 'r') as f:
                    content = f.read()
                
                # Check for required imports
                for required_import in self.config['migrations']['required_imports']:
                    if f"import {required_import}" not in content and f"from {required_import}" not in content:
                        missing_imports.append(f"{file_path.name}: {required_import}")
                
            except Exception as e:
                self.validation_warnings.append(ValidationIssue(
                    type="import_check",
                    message=f"Could not check imports for {file_path.name}: {str(e)}",
                    severity=ValidationResult.WARNING,
                    file_path=str(file_path)
                ))
        
        if missing_imports:
            self.validation_issues.append(ValidationIssue(
                type="missing_imports",
                message=f"Missing required imports: {'; '.join(missing_imports)}",
                severity=ValidationResult.WARNING,
                suggestion="Add missing imports to migration files"
            ))
            return ValidationResult.WARNING
        
        logger.info("Import validation passed")
        return ValidationResult.PASSED
    
    def _validate_file_sizes(self) -> ValidationResult:
        """Validate migration file sizes."""
        logger.info("Validating migration file sizes")
        
        migration_files = list(self.migrations_dir.glob("*.py"))
        oversized_files = []
        
        max_size = self.config['migrations']['max_file_size']
        
        for file_path in migration_files:
            try:
                file_size = file_path.stat().st_size
                if file_size > max_size:
                    oversized_files.append(f"{file_path.name}: {file_size} bytes")
                
            except Exception as e:
                self.validation_warnings.append(ValidationIssue(
                    type="file_size_check",
                    message=f"Could not check file size for {file_path.name}: {str(e)}",
                    severity=ValidationResult.WARNING,
                    file_path=str(file_path)
                ))
        
        if oversized_files:
            self.validation_issues.append(ValidationIssue(
                type="oversized_file",
                message=f"Oversized migration files: {'; '.join(oversized_files)}",
                severity=ValidationResult.WARNING,
                suggestion="Consider splitting large migrations into smaller ones"
            ))
            return ValidationResult.WARNING
        
        logger.info("File size validation passed")
        return ValidationResult.PASSED
    
    def _is_valid_migration_filename(self, filename: str) -> bool:
        """Check if migration filename follows convention."""
        # Pattern: {revision}_{description}.py
        pattern = r'^[a-f0-9]+_[a-z0-9_]+\.py$'
        return re.match(pattern, filename) is not None
    
    def _get_test_database_url(self) -> str:
        """Get test database URL for validation."""
        base_url = self.settings.DATABASE_URL
        test_db_name = self.config['database']['test_db_name']
        
        # Replace database name in URL
        if 'postgresql://' in base_url:
            return base_url.rsplit('/', 1)[0] + f'/{test_db_name}'
        else:
            return base_url.replace('interviewiq', test_db_name)
    
    def _generate_validation_report(self, start_time: datetime, total_checks: int, 
                                  passed: int, failed: int, warnings: int, skipped: int) -> ValidationReport:
        """Generate comprehensive validation report."""
        end_time = datetime.now()
        duration = end_time - start_time
        
        # Generate summary
        if failed == 0 and warnings == 0:
            summary = "All validations passed successfully"
        elif failed == 0:
            summary = f"Validations passed with {warnings} warnings"
        else:
            summary = f"Validation failed with {failed} errors and {warnings} warnings"
        
        # Generate recommendations
        recommendations = []
        if failed > 0:
            recommendations.append("Fix all validation errors before proceeding with migrations")
        if warnings > 0:
            recommendations.append("Review warnings and address critical issues")
        if skipped > 0:
            recommendations.append("Consider enabling skipped validations for comprehensive testing")
        
        # Add specific recommendations based on issues
        issue_types = [issue.type for issue in self.validation_issues + self.validation_warnings]
        if 'syntax_error' in issue_types:
            recommendations.append("Fix syntax errors in migration files")
        if 'database_connectivity' in issue_types:
            recommendations.append("Check database configuration and connectivity")
        if 'unsafe_migration' in issue_types:
            recommendations.append("Review migrations for data safety")
        
        return ValidationReport(
            timestamp=end_time,
            total_checks=total_checks,
            passed=passed,
            failed=failed,
            warnings=warnings,
            skipped=skipped,
            issues=self.validation_issues + self.validation_warnings,
            summary=summary,
            recommendations=recommendations
        )
    
    def create_test_database(self) -> bool:
        """Create test database for validation."""
        try:
            logger.info("Creating test database for validation")
            
            # Connect to postgres database to create test database
            base_url = self.settings.DATABASE_URL
            if 'postgresql://' in base_url:
                # Extract connection details
                parts = base_url.replace('postgresql://', '').split('/')
                if len(parts) >= 2:
                    connection_part = parts[0]
                    database_part = parts[1].split('?')[0]  # Remove query parameters
                    
                    # Connect to postgres database
                    postgres_url = f"postgresql://{connection_part}/postgres"
                    engine = create_engine(postgres_url)
                    
                    with engine.connect() as conn:
                        conn.execute(text("COMMIT"))  # End any transaction
                        conn.execute(text(f"CREATE DATABASE {self.config['database']['test_db_name']}"))
                    
                    logger.info("Test database created successfully")
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to create test database: {e}")
            return False
    
    def cleanup_test_database(self) -> bool:
        """Clean up test database after validation."""
        try:
            logger.info("Cleaning up test database")
            
            # Connect to postgres database to drop test database
            base_url = self.settings.DATABASE_URL
            if 'postgresql://' in base_url:
                parts = base_url.replace('postgresql://', '').split('/')
                if len(parts) >= 2:
                    connection_part = parts[0]
                    
                    # Connect to postgres database
                    postgres_url = f"postgresql://{connection_part}/postgres"
                    engine = create_engine(postgres_url)
                    
                    with engine.connect() as conn:
                        conn.execute(text("COMMIT"))  # End any transaction
                        conn.execute(text(f"DROP DATABASE IF EXISTS {self.config['database']['test_db_name']}"))
                    
                    logger.info("Test database cleaned up successfully")
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to cleanup test database: {e}")
            return False