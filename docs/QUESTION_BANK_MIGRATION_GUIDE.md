# Question Bank Migration and Data Seeding Guide

This guide explains how to migrate existing questions to the global question bank structure and seed the question bank with initial data.

## Overview

The question bank migration process consists of three main steps:

1. **Data Migration** - Migrate any existing questions to the global question bank structure
2. **Data Seeding** - Populate the question bank with comprehensive, diverse questions
3. **Validation** - Verify data integrity and migration success

## Prerequisites

- Database schema migration `7b15fd9db179` must be applied (creates global question bank structure)
- Database connection configured in environment variables
- Python dependencies installed

## Migration Process

### Step 1: Data Migration

Run the migration script to migrate any existing questions:

```bash
python scripts/migrate_questions.py
```

**What it does:**
- Checks for questions without proper metadata and updates them
- Validates data integrity
- Updates session statistics
- Ensures all questions have required fields

**Output:**
- Migration statistics (questions migrated, sessions updated, etc.)
- Logs of any issues or warnings

### Step 2: Data Seeding

Seed the question bank with comprehensive questions:

```bash
python scripts/seed/seed_question_bank.py
```

**What it does:**
- Loads questions from `data/sample_questions.json`
- Adds additional comprehensive questions
- Skips questions that already exist (safe to run multiple times)
- Creates questions with proper metadata, categories, and tags

**Output:**
- Seeding statistics (questions created, skipped, errors)
- Question distribution by category

### Step 3: Validation

Validate the migration and seeding:

```bash
python scripts/validate_migration.py
```

**What it does:**
- Counts statistics (total questions, sessions, links)
- Checks data integrity (orphaned questions, invalid links, duplicates)
- Measures performance impact
- Generates validation report

**Output:**
- Validation report printed to console
- Report saved to `logs/migration_validation_report.txt`
- Exit code: 0 if successful, 1 if rollback recommended

## Scripts Overview

### `scripts/migrate_questions.py`

**Purpose:** Migrate existing questions to global question bank structure

**Features:**
- Updates questions without metadata
- Infers category and subcategory from question text
- Validates data integrity
- Updates session statistics
- Safe to run multiple times

**Usage:**
```bash
python scripts/migrate_questions.py
```

### `scripts/seed/seed_question_bank.py`

**Purpose:** Seed question bank with comprehensive questions

**Features:**
- Loads questions from `data/sample_questions.json`
- Adds technical, behavioral, system design, leadership, and industry-specific questions
- Skips duplicates (safe to run multiple times)
- Creates questions with proper metadata

**Usage:**
```bash
python scripts/seed/seed_question_bank.py
```

### `scripts/validate_migration.py`

**Purpose:** Validate migration and data integrity

**Features:**
- Validates data integrity
- Checks for orphaned questions, invalid links, duplicates
- Measures performance impact
- Generates comprehensive validation report

**Usage:**
```bash
python scripts/validate_migration.py
```

## Validation Report

The validation script generates a comprehensive report that includes:

- **Statistics:** Total questions, sessions, session-question links
- **Data Integrity:** Issues and warnings found
- **Performance:** Query performance metrics
- **Rollback Recommendation:** Whether rollback is required

The report is saved to `logs/migration_validation_report.txt`.

## Rollback Procedures

If validation indicates rollback is required:

1. **Check the validation report** for specific issues
2. **Review logs** for detailed error messages
3. **Fix data issues** manually or restore from backup
4. **Re-run validation** to confirm fixes

### Common Issues and Solutions

**Issue: Invalid session-question links**
- **Cause:** SessionQuestion references non-existent Question
- **Solution:** Remove invalid SessionQuestion records or create missing Questions

**Issue: Orphaned questions**
- **Cause:** Questions exist but aren't linked to any session
- **Solution:** This is not necessarily a problem - orphaned questions can be used for future sessions

**Issue: Duplicate questions**
- **Cause:** Multiple questions with identical text
- **Solution:** Review duplicates and merge if appropriate, or mark one as inactive

**Issue: Questions without metadata**
- **Cause:** Questions created before metadata was required
- **Solution:** Re-run migration script to update metadata

## Performance Testing

After migration, test performance with production-like data volumes:

1. **Query Performance:** Test question selection queries
2. **Load Testing:** Test under concurrent load
3. **Index Usage:** Verify indexes are being used
4. **Cache Performance:** Test caching effectiveness

## Best Practices

1. **Backup First:** Always backup database before migration
2. **Test in Staging:** Run migration in staging environment first
3. **Monitor Logs:** Watch for warnings and errors during migration
4. **Validate After:** Always run validation after migration
5. **Document Issues:** Document any issues encountered and resolutions

## Troubleshooting

### Migration Fails

1. Check database connection
2. Verify schema migration is applied
3. Review error logs for specific issues
4. Check database permissions

### Seeding Fails

1. Verify `data/sample_questions.json` exists and is valid JSON
2. Check database connection
3. Review error logs for specific questions
4. Check for duplicate questions (may cause errors)

### Validation Fails

1. Review validation report for specific issues
2. Check data integrity issues
3. Fix issues and re-run validation
4. Consider rollback if critical issues found

## Support

For issues or questions:
1. Check logs in `logs/` directory
2. Review validation report
3. Check database for data issues
4. Consult team for assistance

## Related Documentation

- `QUESTION_BANK_MIGRATION_GUIDE.md` - This guide
- `MIGRATION_GUIDE.md` - General migration guide
- `DATABASE_SETUP.md` - Database setup instructions
