#!/usr/bin/env python3
"""
Migration Validation Script

This script validates the question bank migration and ensures data integrity.
Run this after running migrate_questions.py to verify the migration was successful.
"""

import os
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy.orm import Session
from sqlalchemy import create_engine

from app.utils.migration_validator import MigrationValidator
from app.config import get_settings
from app.utils.logger import get_logger

logger = get_logger(__name__)

def main():
    """Main function to run validation."""
    logger.info("🚀 Starting Question Bank Migration Validation...")
    
    try:
        settings = get_settings()
        engine = create_engine(settings.DATABASE_URL)
        
        with Session(engine) as db:
            validator = MigrationValidator(db)
            results = validator.validate_migration()
            
            # Generate and print report
            report = validator.generate_validation_report()
            print("\n" + report)
            
            # Save report to file
            report_file = project_root / "logs" / "migration_validation_report.txt"
            report_file.parent.mkdir(exist_ok=True)
            with open(report_file, 'w') as f:
                f.write(report)
            
            logger.info(f"📄 Validation report saved to: {report_file}")
            
            # Exit with appropriate code
            if results.get("rollback_required", False):
                logger.error("❌ Validation failed - rollback recommended")
                sys.exit(1)
            else:
                logger.info("✅ Validation passed - migration successful")
                sys.exit(0)
        
    except Exception as e:
        logger.error(f"❌ Error during validation: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()

