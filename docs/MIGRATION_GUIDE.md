# InterviewIQ Database Migration Guide

This guide provides comprehensive documentation for managing database migrations in the InterviewIQ system using Alembic.

## Table of Contents

1. [Overview](#overview)
2. [Migration System Architecture](#migration-system-architecture)
3. [Getting Started](#getting-started)
4. [Creating Migrations](#creating-migrations)
5. [Running Migrations](#running-migrations)
6. [Validation and Testing](#validation-and-testing)
7. [Production Deployment](#production-deployment)
8. [Rollback Procedures](#rollback-procedures)
9. [Troubleshooting](#troubleshooting)
10. [Best Practices](#best-practices)

## Overview

The InterviewIQ migration system is built on Alembic and provides:

- **Automated Schema Management**: Version-controlled database schema changes
- **Data Migration Support**: Safe data transformations and migrations
- **Rollback Capabilities**: Ability to revert changes when needed
- **Validation System**: Comprehensive pre and post-deployment validation
- **Production Safety**: Backup creation and monitoring
- **Performance Testing**: Migration impact assessment

## Migration System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Migration System                         │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────┐ │
│  │   Migration     │  │   Validation    │  │  Production  │ │
│  │   Manager       │  │   System        │  │  Deployer    │ │
│  │                 │  │                 │  │              │ │
│  │ • Create        │  │ • Integrity     │  │ • Backup     │ │
│  │ • Upgrade       │  │ • Testing       │  │ • Deploy     │ │
│  │ • Downgrade     │  │ • Performance   │  │ • Monitor    │ │
│  │ • History       │  │ • Data Safety   │  │ • Rollback   │ │
│  └─────────────────┘  └─────────────────┘  └──────────────┘ │
├─────────────────────────────────────────────────────────────┤
│                    Alembic Core                             │
│  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────┐ │
│  │   Migration     │  │   Environment   │  │  Version     │ │
│  │   Files         │  │   Configuration │  │  Control     │ │
│  └─────────────────┘  └─────────────────┘  └──────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

## Getting Started

### Prerequisites

- Python 3.8+
- PostgreSQL 12+
- Alembic 1.13+
- SQLAlchemy 2.0+

### Installation

1. Install dependencies:
```bash
pip install alembic sqlalchemy psycopg2-binary
```

2. Verify installation:
```bash
alembic --version
```

### Configuration

The migration system is configured through:

- `alembic.ini`: Main Alembic configuration
- `app/database/migrations/env.py`: Environment setup
- `app/config.py`: Database connection settings

## Creating Migrations

### Automatic Migration Generation

Generate migrations automatically from model changes:

```bash
# Create migration from model changes
python app/database/migrate.py create "Add new user fields"

# Or use alembic directly
alembic revision --autogenerate -m "Add new user fields"
```

### Manual Migration Creation

Create empty migration for custom changes:

```bash
# Create empty migration
python app/database/migrate.py create "Custom data migration" --no-autogenerate

# Or use alembic directly
alembic revision -m "Custom data migration"
```

### Migration File Structure

Migration files are located in `app/database/migrations/versions/` and follow this naming convention:

```
YYYYMMDD_HHMMSS_revision_id_description.py
```

Example: `20241014_143022_7b15fd9db179_add_question_bank_foundation.py`

### Writing Migration Code

```python
"""Add question bank foundation

Revision ID: 7b15fd9db179
Revises: 84cb1aaf7a64
Create Date: 2024-10-14 14:30:22.393175

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = '7b15fd9db179'
down_revision = '84cb1aaf7a64'
branch_labels = None
depends_on = None

def upgrade() -> None:
    """Apply migration changes."""
    # Create new table
    op.create_table('session_questions',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('session_id', sa.UUID(), nullable=False),
        sa.Column('question_id', sa.UUID(), nullable=False),
        sa.Column('question_order', sa.Integer(), nullable=False),
        sa.Column('session_specific_context', postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['question_id'], ['questions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['session_id'], ['interview_sessions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Add new columns
    op.add_column('questions', sa.Column('question_metadata', postgresql.JSONB(), nullable=False))
    op.add_column('questions', sa.Column('usage_count', sa.Integer(), nullable=False))
    
    # Create indexes
    op.create_index('idx_questions_category', 'questions', ['category'])
    op.create_index('idx_questions_difficulty', 'questions', ['difficulty_level'])

def downgrade() -> None:
    """Revert migration changes."""
    # Drop indexes
    op.drop_index('idx_questions_difficulty', table_name='questions')
    op.drop_index('idx_questions_category', table_name='questions')
    
    # Drop columns
    op.drop_column('questions', 'usage_count')
    op.drop_column('questions', 'question_metadata')
    
    # Drop table
    op.drop_table('session_questions')
```

## Running Migrations

### Development Environment

```bash
# Upgrade to latest migration
python app/database/migrate.py upgrade

# Upgrade to specific revision
python app/database/migrate.py upgrade 7b15fd9db179

# Check current revision
python app/database/migrate.py current

# View migration history
python app/database/migrate.py history
```

### Staging Environment

```bash
# Run with validation
python app/database/migrate.py validate head
python app/database/migrate.py upgrade head
```

### Production Environment

```bash
# Production deployment with full safety checks
python scripts/deploy_migrations.py head --environment production

# With maintenance window
python scripts/deploy_migrations.py head --maintenance-window "02:00-04:00"

# Dry run (validation only)
python scripts/deploy_migrations.py head --dry-run
```

## Validation and Testing

### Pre-Deployment Validation

```bash
# Run comprehensive validation
python app/database/migrate.py validate head

# Test on clean database
python -c "
from app.utils.migration_validator import MigrationValidator
validator = MigrationValidator()
results = validator.test_migration_on_clean_database('head')
print(results)
"
```

### Validation Checks

The validation system performs these checks:

1. **Migration Integrity**
   - File existence and format
   - Migration chain consistency
   - SQL syntax validation
   - Dependency validation

2. **Clean Database Testing**
   - Test migration on fresh database
   - Schema validation
   - Rollback testing

3. **Performance Testing**
   - Migration duration measurement
   - Database size impact
   - Performance regression detection

4. **Data Integrity**
   - Foreign key constraint validation
   - Data consistency checks
   - Index integrity verification

### Manual Validation

```python
from app.utils.migration_validator import MigrationValidator

validator = MigrationValidator()

# Validate migration integrity
integrity_results = validator.validate_migration_integrity("head")
print(f"Integrity check passed: {integrity_results['validation_passed']}")

# Test on clean database
clean_test_results = validator.test_migration_on_clean_database("head")
print(f"Clean test passed: {clean_test_results['test_passed']}")

# Performance test
performance_results = validator.performance_test_migration("head")
print(f"Performance test passed: {performance_results['performance_passed']}")
```

## Production Deployment

### Deployment Process

The production deployment process includes:

1. **Pre-Deployment Validation**
   - Migration integrity checks
   - Clean database testing
   - Performance impact assessment
   - System resource validation

2. **Backup Creation**
   - Full database backup
   - Backup verification
   - Backup storage

3. **Migration Application**
   - Maintenance mode activation
   - Migration execution
   - Maintenance mode deactivation

4. **Post-Deployment Validation**
   - Data integrity checks
   - Application connectivity tests
   - Critical query validation

5. **Monitoring**
   - Performance monitoring
   - Error rate monitoring
   - Automatic rollback triggers

### Deployment Commands

```bash
# Standard production deployment
python scripts/deploy_migrations.py head

# With custom maintenance window
python scripts/deploy_migrations.py head --maintenance-window "01:00-03:00"

# Skip backup (not recommended)
python scripts/deploy_migrations.py head --no-backup

# Skip validation (not recommended)
python scripts/deploy_migrations.py head --no-validation

# Dry run for testing
python scripts/deploy_migrations.py head --dry-run
```

### Deployment Monitoring

The deployment system monitors:

- Database performance metrics
- Connection counts
- Slow query detection
- Error rates
- Application responsiveness

## Rollback Procedures

### Automatic Rollback

The system automatically triggers rollback when:

- Migration application fails
- Post-deployment validation fails
- Performance issues detected
- Critical errors occur

### Manual Rollback

```bash
# Rollback to previous revision
python app/database/migrate.py downgrade -1

# Rollback to specific revision
python app/database/migrate.py downgrade 84cb1aaf7a64

# Rollback from backup
python app/database/migrate.py restore /path/to/backup.sql
```

### Emergency Rollback

In case of critical issues:

1. **Immediate Response**
   ```bash
   # Set maintenance mode
   echo "MAINTENANCE_MODE=true" > /tmp/maintenance.flag
   
   # Rollback to last known good state
   python app/database/migrate.py downgrade -1
   ```

2. **Full Database Restore**
   ```bash
   # Restore from latest backup
   python app/database/migrate.py restore /backups/latest_backup.sql
   ```

3. **Verification**
   ```bash
   # Verify rollback success
   python app/database/migrate.py current
   python app/database/migrate.py validate current
   ```

### Rollback Validation

After rollback, always validate:

```bash
# Check current revision
python app/database/migrate.py current

# Validate data integrity
python -c "
from app.utils.migration_validator import MigrationValidator
validator = MigrationValidator()
results = validator.validate_data_integrity_after_migration('current')
print(f'Data integrity: {results[\"integrity_passed\"]}')
"

# Test application functionality
python -c "
from app.utils.migration_validator import MigrationValidator
validator = MigrationValidator()
results = validator._test_critical_queries()
print(f'Critical queries: {results[\"all_passed\"]}')
"
```

## Troubleshooting

### Common Issues

#### 1. Migration Chain Broken

**Symptoms:**
- `alembic check` fails
- Migration history shows gaps
- Upgrade/downgrade fails

**Solution:**
```bash
# Check migration chain
alembic check

# Fix chain manually if needed
alembic stamp head
```

#### 2. Database Connection Issues

**Symptoms:**
- Connection timeout errors
- Authentication failures
- Network connectivity issues

**Solution:**
```bash
# Test database connectivity
python -c "
from app.config import get_settings
from sqlalchemy import create_engine
settings = get_settings()
engine = create_engine(settings.DATABASE_URL)
with engine.connect() as conn:
    print('Connection successful')
"

# Check environment variables
echo $DATABASE_URL
```

#### 3. Migration Conflicts

**Symptoms:**
- Autogenerate creates conflicting changes
- Manual migrations conflict with model changes
- Schema drift between environments

**Solution:**
```bash
# Review autogenerated changes
alembic revision --autogenerate -m "Review changes"

# Manually edit migration file to resolve conflicts
# Then apply the corrected migration
```

#### 4. Performance Issues

**Symptoms:**
- Slow migration execution
- Database locks
- High resource usage

**Solution:**
```bash
# Monitor migration performance
python -c "
from app.utils.migration_validator import MigrationValidator
validator = MigrationValidator()
results = validator.performance_test_migration('head')
print(f'Migration duration: {results[\"metrics\"][\"migration_duration\"]}s')
"

# Optimize migration for large tables
# - Use batch operations
# - Add progress indicators
# - Consider offline migration for very large datasets
```

### Debug Mode

Enable debug logging:

```bash
# Set debug environment
export ALEMBIC_ECHO=true
export LOG_LEVEL=DEBUG

# Run migration with debug output
python app/database/migrate.py upgrade head
```

### Recovery Procedures

#### 1. Partial Migration Failure

If migration fails partway through:

```bash
# Check current state
python app/database/migrate.py current

# Check for partial changes
python -c "
from app.utils.migration_validator import MigrationValidator
validator = MigrationValidator()
results = validator.validate_data_integrity_after_migration('current')
print(results)
"

# Complete or rollback based on findings
```

#### 2. Data Corruption

If data corruption is detected:

```bash
# Immediate backup of current state
python app/database/migrate.py backup --path /emergency/backup_$(date +%Y%m%d_%H%M%S).sql

# Restore from last known good backup
python app/database/migrate.py restore /backups/last_known_good.sql

# Validate restoration
python app/database/migrate.py validate current
```

## Best Practices

### Migration Development

1. **Always Test Locally First**
   ```bash
   # Test on development database
   python app/database/migrate.py upgrade head
   python app/database/migrate.py downgrade -1
   python app/database/migrate.py upgrade head
   ```

2. **Use Descriptive Migration Messages**
   ```bash
   # Good
   alembic revision --autogenerate -m "Add question bank foundation with global questions and session questions"
   
   # Bad
   alembic revision --autogenerate -m "Update schema"
   ```

3. **Review Autogenerated Migrations**
   - Always review autogenerated changes
   - Remove unnecessary operations
   - Add custom logic where needed

4. **Test Rollback Procedures**
   ```bash
   # Always test rollback
   python app/database/migrate.py upgrade head
   python app/database/migrate.py downgrade -1
   python app/database/migrate.py upgrade head
   ```

### Production Deployment

1. **Use Maintenance Windows**
   ```bash
   # Deploy during low-traffic periods
   python scripts/deploy_migrations.py head --maintenance-window "02:00-04:00"
   ```

2. **Always Create Backups**
   ```bash
   # Never skip backup creation
   python scripts/deploy_migrations.py head  # Backup created automatically
   ```

3. **Monitor Post-Deployment**
   ```bash
   # Monitor for at least 30 minutes after deployment
   # Check application logs and performance metrics
   ```

4. **Have Rollback Plan Ready**
   - Know the rollback procedure
   - Have backup locations documented
   - Test rollback procedures regularly

### Data Migration Best Practices

1. **Use Batch Operations for Large Datasets**
   ```python
   def upgrade():
       # Good: Batch processing
       batch_size = 1000
       while True:
           batch = op.get_bind().execute(
               "SELECT * FROM old_table LIMIT %s OFFSET %s", 
               (batch_size, offset)
           ).fetchall()
           if not batch:
               break
           # Process batch
           offset += batch_size
   ```

2. **Add Progress Indicators**
   ```python
   def upgrade():
       total = op.get_bind().execute("SELECT COUNT(*) FROM old_table").scalar()
       processed = 0
       for row in op.get_bind().execute("SELECT * FROM old_table"):
           # Process row
           processed += 1
           if processed % 1000 == 0:
               print(f"Processed {processed}/{total} rows")
   ```

3. **Validate Data After Migration**
   ```python
   def upgrade():
       # Perform migration
       # ...
       
       # Validate results
       count_before = op.get_bind().execute("SELECT COUNT(*) FROM old_table").scalar()
       count_after = op.get_bind().execute("SELECT COUNT(*) FROM new_table").scalar()
       assert count_before == count_after, "Data count mismatch"
   ```

### Security Considerations

1. **Protect Sensitive Data**
   - Never log sensitive information
   - Use environment variables for credentials
   - Encrypt backup files

2. **Access Control**
   - Limit migration execution to authorized personnel
   - Use service accounts for automated deployments
   - Audit all migration activities

3. **Backup Security**
   - Store backups in secure locations
   - Encrypt backup files
   - Regular backup testing

## Migration Checklist

### Before Creating Migration

- [ ] Model changes are complete and tested
- [ ] Database schema changes are documented
- [ ] Data migration requirements are identified
- [ ] Performance impact is assessed

### Before Applying Migration

- [ ] Migration is tested on development database
- [ ] Rollback procedure is tested
- [ ] Backup is created (production)
- [ ] Maintenance window is scheduled (production)
- [ ] Stakeholders are notified (production)

### After Applying Migration

- [ ] Migration success is verified
- [ ] Data integrity is validated
- [ ] Application functionality is tested
- [ ] Performance is monitored
- [ ] Documentation is updated

### Emergency Procedures

- [ ] Rollback procedure is documented
- [ ] Backup locations are known
- [ ] Emergency contacts are available
- [ ] Recovery time objectives are defined

## Support and Resources

### Documentation
- [Alembic Documentation](https://alembic.sqlalchemy.org/)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)

### Tools
- Migration Manager: `app/database/migrate.py`
- Validation System: `app/utils/migration_validator.py`
- Production Deployer: `scripts/deploy_migrations.py`

### Monitoring
- Migration History: `alembic history`
- Current Revision: `alembic current`
- Validation Results: Migration validation system
- Performance Metrics: Production monitoring system

For additional support, contact the development team or refer to the project's issue tracker.
