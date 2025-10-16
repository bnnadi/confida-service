# Question Bank Migration and Data Seeding Guide

## Overview

This guide covers the comprehensive question bank migration and data seeding system implemented for Confida. The system migrates existing session-bound questions to a global question bank and provides extensive data seeding capabilities.

## 🎯 **What Was Implemented**

### **Core Migration System**
- **Question Bank Migration Script** - Migrates existing session-bound questions to global question bank
- **Data Seeding System** - Comprehensive seeding with sample questions from multiple sources
- **CLI Management Tool** - Command-line interface for question bank operations
- **Data Validation System** - Quality checks and data integrity validation
- **Sample Question Database** - Curated collection of high-quality interview questions

### **Key Features**
- **Zero-downtime migration** - Migrates existing data without service interruption
- **Duplicate detection** - Identifies and handles duplicate questions intelligently
- **Data enrichment** - Automatically enriches questions with metadata, skills, and tags
- **Quality validation** - Comprehensive data quality checks and reporting
- **Flexible seeding** - Support for multiple question sources and formats

## 📁 **Files Created**

### **Migration Scripts**
```
scripts/
├── question_bank_migration.py      # Main migration and seeding script
├── question_bank_cli.py            # CLI tool for question bank management
└── question_bank_validator.py      # Data validation and quality checks
```

### **Data Files**
```
data/
└── sample_questions.json           # Comprehensive sample question database
```

### **Documentation**
```
docs/
└── QUESTION_BANK_MIGRATION_GUIDE.md  # This comprehensive guide
```

## 🚀 **Quick Start**

### **1. Run Migration**
```bash
# Migrate existing questions to question bank
python scripts/question_bank_migration.py

# Dry run to see what would be migrated
python scripts/question_bank_cli.py migrate --dry-run
```

### **2. Seed Sample Questions**
```bash
# Seed with comprehensive sample questions
python scripts/question_bank_cli.py seed

# Seed from custom JSON file
python scripts/question_bank_cli.py seed --file data/sample_questions.json
```

### **3. Validate Data Quality**
```bash
# Run comprehensive validation
python scripts/question_bank_validator.py

# Fix common issues
python scripts/question_bank_validator.py --fix

# Generate detailed report
python scripts/question_bank_validator.py --report
```

## 🔧 **Migration Process**

### **Step 1: Data Analysis**
The migration script analyzes existing questions to:
- Identify session-bound questions that need migration
- Detect duplicate questions across sessions
- Extract metadata and context information
- Calculate usage statistics and performance metrics

### **Step 2: Question Enrichment**
Each question is enriched with:
- **Metadata** - Source, migration timestamp, version information
- **Skills** - Extracted from question text and context
- **Roles** - Compatible roles from session context
- **Tags** - Industry tags from job descriptions
- **Statistics** - Usage count, average score, success rate

### **Step 3: Global Question Bank Creation**
Questions are migrated to the global question bank with:
- **Unique IDs** - New UUIDs for global questions
- **Session Links** - `SessionQuestion` records linking sessions to global questions
- **Metadata Preservation** - All original data preserved and enhanced
- **Duplicate Handling** - Intelligent duplicate detection and merging

### **Step 4: Session Updates**
Existing sessions are updated to:
- Link to global questions via `SessionQuestion` table
- Maintain question order and session-specific context
- Preserve all existing functionality

## 📊 **Data Seeding System**

### **Question Categories**

#### **Technical Questions**
- **Python** - Language-specific questions with difficulty levels
- **JavaScript** - Frontend and Node.js questions
- **Java** - Enterprise development questions
- **Database** - SQL, optimization, and design questions
- **Algorithms** - Data structures and algorithmic thinking

#### **Behavioral Questions**
- **Conflict Resolution** - Team dynamics and problem-solving
- **Learning Agility** - Adaptability and growth mindset
- **Resilience** - Handling failure and challenges
- **Decision Making** - Critical thinking and leadership

#### **System Design Questions**
- **Web Services** - API design and microservices
- **Real-time Systems** - Chat, notifications, streaming
- **Distributed Systems** - Caching, consistency, scalability
- **Recommendation Systems** - ML and data processing

#### **Leadership Questions**
- **Team Management** - Motivation and team building
- **Feedback** - Communication and people management
- **Stakeholder Management** - Prioritization and negotiation
- **Decision Making** - Courage and leadership

#### **Industry-Specific Questions**
- **Fintech** - Security, compliance, trading systems
- **Healthcare** - Privacy, regulations, medical software
- **E-commerce** - Scalability, recommendations, performance

### **Question Metadata Structure**
```json
{
  "question": "Explain the difference between list comprehensions and generator expressions in Python.",
  "difficulty": "medium",
  "category": "technical",
  "subcategory": "python",
  "skills": ["python", "programming", "optimization", "memory_management"],
  "tags": ["python", "performance", "data_structures"],
  "compatible_roles": ["software_engineer", "backend_developer", "python_developer"],
  "industry_tags": ["technology", "software"],
  "usage_count": 0,
  "average_score": null,
  "success_rate": null
}
```

## 🛠️ **CLI Tool Usage**

### **Migration Commands**
```bash
# Migrate existing questions
python scripts/question_bank_cli.py migrate

# Dry run migration
python scripts/question_bank_cli.py migrate --dry-run
```

### **Seeding Commands**
```bash
# Seed with built-in questions
python scripts/question_bank_cli.py seed

# Seed from JSON file
python scripts/question_bank_cli.py seed --file data/custom_questions.json
```

### **Statistics Commands**
```bash
# Show question bank statistics
python scripts/question_bank_cli.py stats
```

### **Search Commands**
```bash
# Search questions
python scripts/question_bank_cli.py search "python decorators"

# Search with filters
python scripts/question_bank_cli.py search "algorithms" --category technical --difficulty hard --limit 5
```

### **Maintenance Commands**
```bash
# Clean up duplicates
python scripts/question_bank_cli.py cleanup

# Export questions
python scripts/question_bank_cli.py export questions.json --format json
python scripts/question_bank_cli.py export questions.csv --format csv --category technical
```

## 🔍 **Data Validation System**

### **Validation Checks**

#### **Question Text Quality**
- Length validation (10-1000 characters)
- Proper punctuation and sentence structure
- Common typo detection
- Whitespace normalization

#### **Metadata Validation**
- Required fields presence
- JSON structure validation
- Data type consistency
- Value range validation

#### **Category Validation**
- Valid category values
- Category-subcategory consistency
- Proper classification logic

#### **Skills and Roles Validation**
- List structure validation
- Non-empty values
- Reasonable limits (max 20 skills, 10 roles)
- Data type consistency

#### **Usage Statistics Validation**
- Numeric value validation
- Range validation (scores 0-10, success rate 0-1)
- Consistency checks

#### **Duplicate Detection**
- Text similarity analysis
- Exact duplicate identification
- Cross-category duplicate detection

#### **Data Consistency**
- Cross-reference validation
- Relationship integrity
- Orphaned data detection

### **Quality Metrics**
- **Quality Score** - Overall data quality (0-100)
- **Validation Coverage** - Percentage of questions validated
- **Issue Distribution** - Issues by type and severity
- **Recommendations** - Automated improvement suggestions

### **Validation Commands**
```bash
# Run full validation
python scripts/question_bank_validator.py

# Fix common issues
python scripts/question_bank_validator.py --fix

# Generate detailed report
python scripts/question_bank_validator.py --report

# Dry run fixes
python scripts/question_bank_validator.py --fix --dry-run
```

## 📈 **Migration Statistics**

### **Expected Results**
- **Questions Migrated** - All existing session-bound questions
- **Duplicates Handled** - Intelligent merging of duplicate questions
- **Metadata Enriched** - Enhanced with skills, roles, and tags
- **Sessions Updated** - All sessions linked to global questions
- **Zero Data Loss** - All original data preserved

### **Performance Impact**
- **Migration Time** - Typically 1-5 minutes for 1000+ questions
- **Database Impact** - Minimal, uses transactions for safety
- **Service Availability** - No downtime during migration
- **Storage Impact** - Slight increase due to metadata enrichment

## 🔧 **Configuration**

### **Environment Variables**
```bash
# Database connection
DATABASE_URL=postgresql://user:pass@localhost:5432/confida

# Migration settings
MIGRATION_DRY_RUN=false
MIGRATION_BATCH_SIZE=100
MIGRATION_VALIDATE=true

# Seeding settings
SEED_SAMPLE_QUESTIONS=true
SEED_CUSTOM_QUESTIONS=false
SEED_VALIDATE_QUALITY=true
```

### **Migration Settings**
```python
# In question_bank_migration.py
MIGRATION_CONFIG = {
    "batch_size": 100,
    "validate_duplicates": True,
    "enrich_metadata": True,
    "preserve_original": True,
    "create_session_links": True
}
```

## 🚨 **Troubleshooting**

### **Common Issues**

#### **Migration Failures**
```bash
# Check database connectivity
python -c "from app.database.connection import get_db; print('DB connected')"

# Verify question bank structure
python scripts/question_bank_cli.py stats

# Run validation
python scripts/question_bank_validator.py
```

#### **Data Quality Issues**
```bash
# Check for duplicates
python scripts/question_bank_cli.py search "duplicate text"

# Validate specific questions
python scripts/question_bank_validator.py --report

# Fix common issues
python scripts/question_bank_validator.py --fix
```

#### **Performance Issues**
```bash
# Check database performance
python scripts/question_bank_cli.py stats

# Monitor migration progress
tail -f logs/migration.log

# Optimize database
python scripts/question_bank_cli.py cleanup
```

### **Recovery Procedures**

#### **Rollback Migration**
```bash
# Restore from backup
pg_restore -d confida backup_before_migration.sql

# Or reset question bank
python scripts/question_bank_cli.py cleanup --reset
```

#### **Fix Corrupted Data**
```bash
# Validate and fix
python scripts/question_bank_validator.py --fix

# Re-run migration
python scripts/question_bank_migration.py
```

## 📚 **API Integration**

### **Question Bank Service**
```python
from app.services.question_bank_service import QuestionBankService
from app.database.connection import get_db

# Get question bank service
db = next(get_db())
qb_service = QuestionBankService(db)

# Get questions for role
questions = qb_service.get_questions_for_role(
    role="software_engineer",
    job_description="Python developer role",
    count=10
)

# Store generated questions
qb_service.store_generated_questions(
    questions=["Question 1", "Question 2"],
    role="software_engineer",
    job_description="Python developer role",
    ai_service_used="gpt-4",
    prompt_hash="abc123"
)

# Get statistics
stats = qb_service.get_question_bank_stats()
```

### **Async Question Bank Service**
```python
from app.services.async_question_bank_service import AsyncQuestionBankService
from app.database.async_connection import get_async_db

async with get_async_db() as db:
    qb_service = AsyncQuestionBankService(db)
    
    # Async operations
    questions = await qb_service.get_questions_for_role(
        role="software_engineer",
        job_description="Python developer role",
        count=10
    )
    
    stats = await qb_service.get_question_bank_stats()
```

## 🎯 **Best Practices**

### **Migration Best Practices**
1. **Always run dry-run first** - Validate migration before execution
2. **Backup database** - Create backup before major migrations
3. **Monitor progress** - Watch logs and statistics during migration
4. **Validate results** - Run validation after migration completion
5. **Test functionality** - Verify all features work after migration

### **Data Quality Best Practices**
1. **Regular validation** - Run validation checks regularly
2. **Fix issues promptly** - Address quality issues as they arise
3. **Monitor statistics** - Track question usage and performance
4. **Update metadata** - Keep question metadata current and accurate
5. **Remove duplicates** - Clean up duplicate questions regularly

### **Seeding Best Practices**
1. **Use curated sources** - Only seed high-quality questions
2. **Validate before seeding** - Check question quality before adding
3. **Categorize properly** - Ensure correct category and subcategory
4. **Enrich metadata** - Add comprehensive skills and tags
5. **Test integration** - Verify seeded questions work with services

## 🔮 **Future Enhancements**

### **Planned Features**
- **Question Versioning** - Track question changes over time
- **A/B Testing** - Test different question variations
- **Machine Learning** - AI-powered question recommendation
- **Analytics Dashboard** - Visual question bank management
- **API Endpoints** - REST API for question bank operations

### **Advanced Seeding**
- **External Sources** - Import from external question databases
- **AI Generation** - Generate questions using AI services
- **Community Contributions** - User-submitted questions
- **Quality Scoring** - Automated quality assessment
- **Dynamic Updates** - Real-time question updates

## 📞 **Support and Resources**

### **Documentation**
- **Migration Guide** - This comprehensive guide
- **API Documentation** - Service integration examples
- **CLI Reference** - Command-line tool documentation
- **Validation Guide** - Data quality management

### **Tools and Scripts**
- **Migration Script** - `scripts/question_bank_migration.py`
- **CLI Tool** - `scripts/question_bank_cli.py`
- **Validator** - `scripts/question_bank_validator.py`
- **Sample Data** - `data/sample_questions.json`

### **Monitoring**
- **Health Checks** - Database and service monitoring
- **Quality Metrics** - Data quality tracking
- **Performance Stats** - Migration and seeding performance
- **Error Logging** - Comprehensive error tracking

---

**The Question Bank Migration and Data Seeding system is now fully implemented and ready for production use!** 🎉

This system provides a robust foundation for managing interview questions with comprehensive migration, seeding, validation, and management capabilities.
