#!/usr/bin/env python3
"""
Question Bank Data Validation and Quality Check System

This script validates the quality and integrity of questions in the question bank,
including data validation, consistency checks, and quality metrics.
"""

import os
import sys
import re
from datetime import datetime, timedelta
from typing import Dict, Any, List, Tuple
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy.orm import Session
from sqlalchemy import create_engine, select, func, and_, or_
from app.database.models import Question, SessionQuestion, Answer
from app.config import get_settings
from app.utils.logger import get_logger

logger = get_logger(__name__)

class QuestionBankValidator:
    """Validates question bank data quality and integrity."""
    
    def __init__(self):
        self.settings = get_settings()
        self.engine = create_engine(self.settings.DATABASE_URL)
        self.validation_results = {
            "total_questions": 0,
            "valid_questions": 0,
            "issues_found": 0,
            "quality_score": 0.0,
            "issues": []
        }
    
    def run_full_validation(self) -> Dict[str, Any]:
        """Run comprehensive validation of the question bank."""
        logger.info("🔍 Starting comprehensive question bank validation...")
        
        with Session(self.engine) as db:
            # Get all questions
            questions = db.execute(select(Question)).scalars().all()
            self.validation_results["total_questions"] = len(questions)
            
            logger.info(f"Validating {len(questions)} questions...")
            
            # Run validation checks
            self._validate_question_text(questions)
            self._validate_metadata(questions)
            self._validate_categories(questions)
            self._validate_difficulty_levels(questions)
            self._validate_skills_and_roles(questions)
            self._validate_usage_statistics(questions)
            self._validate_duplicates(questions)
            self._validate_orphaned_questions(questions)
            self._validate_consistency(questions)
            
            # Calculate quality score
            self._calculate_quality_score()
            
            logger.info("✅ Validation completed!")
            return self.validation_results
    
    def _validate_question_text(self, questions: List[Question]):
        """Validate question text quality."""
        logger.info("Validating question text...")
        
        for question in questions:
            issues = []
            
            # Check for empty or very short questions
            if not question.question_text or len(question.question_text.strip()) < 10:
                issues.append("Question text is too short or empty")
            
            # Check for very long questions
            if len(question.question_text) > 1000:
                issues.append("Question text is too long (>1000 characters)")
            
            # Check for proper sentence structure
            if not question.question_text.endswith(('?', '.', '!')):
                issues.append("Question should end with proper punctuation")
            
            # Check for common typos or issues
            if re.search(r'\b(teh|adn|recieve|seperate)\b', question.question_text, re.IGNORECASE):
                issues.append("Question contains common typos")
            
            # Check for excessive whitespace
            if re.search(r'\s{3,}', question.question_text):
                issues.append("Question contains excessive whitespace")
            
            if issues:
                self._add_issue("question_text", question.id, issues)
    
    def _validate_metadata(self, questions: List[Question]):
        """Validate question metadata."""
        logger.info("Validating question metadata...")
        
        for question in questions:
            issues = []
            
            # Check if metadata exists and is valid JSON
            if not question.question_metadata:
                issues.append("Question metadata is missing")
            elif not isinstance(question.question_metadata, dict):
                issues.append("Question metadata is not a valid dictionary")
            
            # Check for required metadata fields
            if question.question_metadata:
                required_fields = ["source"]
                for field in required_fields:
                    if field not in question.question_metadata:
                        issues.append(f"Missing required metadata field: {field}")
            
            if issues:
                self._add_issue("metadata", question.id, issues)
    
    def _validate_categories(self, questions: List[Question]):
        """Validate question categories."""
        logger.info("Validating question categories...")
        
        valid_categories = {
            "technical", "behavioral", "system_design", "leadership", 
            "industry_specific", "general"
        }
        
        for question in questions:
            issues = []
            
            # Check if category exists
            if not question.category:
                issues.append("Category is missing")
            elif question.category not in valid_categories:
                issues.append(f"Invalid category: {question.category}")
            
            # Check category-subcategory consistency
            if question.category == "technical" and question.subcategory:
                valid_tech_subcategories = {
                    "python", "javascript", "java", "database", "algorithms", 
                    "system_design", "frontend", "backend", "devops"
                }
                if question.subcategory not in valid_tech_subcategories:
                    issues.append(f"Invalid technical subcategory: {question.subcategory}")
            
            elif question.category == "behavioral" and question.subcategory:
                valid_behavioral_subcategories = {
                    "conflict_resolution", "learning_agility", "resilience",
                    "decision_making", "collaboration", "leadership"
                }
                if question.subcategory not in valid_behavioral_subcategories:
                    issues.append(f"Invalid behavioral subcategory: {question.subcategory}")
            
            if issues:
                self._add_issue("category", question.id, issues)
    
    def _validate_difficulty_levels(self, questions: List[Question]):
        """Validate difficulty levels."""
        logger.info("Validating difficulty levels...")
        
        valid_difficulties = {"easy", "medium", "hard"}
        
        for question in questions:
            issues = []
            
            if not question.difficulty_level:
                issues.append("Difficulty level is missing")
            elif question.difficulty_level not in valid_difficulties:
                issues.append(f"Invalid difficulty level: {question.difficulty_level}")
            
            # Check difficulty consistency with question length/complexity
            if question.difficulty_level == "easy" and len(question.question_text) > 200:
                issues.append("Easy question is too long/complex")
            
            if question.difficulty_level == "hard" and len(question.question_text) < 50:
                issues.append("Hard question is too short/simple")
            
            if issues:
                self._add_issue("difficulty", question.id, issues)
    
    def _validate_skills_and_roles(self, questions: List[Question]):
        """Validate skills and roles data."""
        logger.info("Validating skills and roles...")
        
        for question in questions:
            issues = []
            
            # Check required skills
            if not question.required_skills:
                issues.append("Required skills are missing")
            elif not isinstance(question.required_skills, list):
                issues.append("Required skills should be a list")
            elif len(question.required_skills) == 0:
                issues.append("Required skills list is empty")
            elif len(question.required_skills) > 20:
                issues.append("Too many required skills (max 20)")
            
            # Check compatible roles
            if not question.compatible_roles:
                issues.append("Compatible roles are missing")
            elif not isinstance(question.compatible_roles, list):
                issues.append("Compatible roles should be a list")
            elif len(question.compatible_roles) == 0:
                issues.append("Compatible roles list is empty")
            elif len(question.compatible_roles) > 10:
                issues.append("Too many compatible roles (max 10)")
            
            # Check for invalid characters in skills/roles
            if question.required_skills:
                for skill in question.required_skills:
                    if not isinstance(skill, str) or not skill.strip():
                        issues.append(f"Invalid skill: {skill}")
            
            if question.compatible_roles:
                for role in question.compatible_roles:
                    if not isinstance(role, str) or not role.strip():
                        issues.append(f"Invalid role: {role}")
            
            if issues:
                self._add_issue("skills_roles", question.id, issues)
    
    def _validate_usage_statistics(self, questions: List[Question]):
        """Validate usage statistics."""
        logger.info("Validating usage statistics...")
        
        for question in questions:
            issues = []
            
            # Check usage count
            if question.usage_count is None or question.usage_count < 0:
                issues.append("Invalid usage count")
            
            # Check average score
            if question.average_score is not None:
                if not isinstance(question.average_score, (int, float)):
                    issues.append("Average score should be a number")
                elif question.average_score < 0 or question.average_score > 10:
                    issues.append("Average score should be between 0 and 10")
            
            # Check success rate
            if question.success_rate is not None:
                if not isinstance(question.success_rate, (int, float)):
                    issues.append("Success rate should be a number")
                elif question.success_rate < 0 or question.success_rate > 1:
                    issues.append("Success rate should be between 0 and 1")
            
            # Check consistency between usage count and scores
            if question.usage_count > 0 and question.average_score is None:
                issues.append("Question has usage but no average score")
            
            if issues:
                self._add_issue("usage_stats", question.id, issues)
    
    def _validate_duplicates(self, questions: List[Question]):
        """Check for duplicate questions."""
        logger.info("Checking for duplicate questions...")
        
        question_texts = {}
        for question in questions:
            text = question.question_text.lower().strip()
            if text in question_texts:
                self._add_issue("duplicate", question.id, [f"Duplicate of question {question_texts[text]}"])
            else:
                question_texts[text] = str(question.id)
    
    def _validate_orphaned_questions(self, questions: List[Question]):
        """Check for orphaned questions (not linked to any sessions)."""
        logger.info("Checking for orphaned questions...")
        
        with Session(self.engine) as db:
            for question in questions:
                # Check if question is linked to any sessions
                session_links = db.execute(
                    select(SessionQuestion).where(SessionQuestion.question_id == question.id)
                ).scalars().all()
                
                if not session_links and question.usage_count == 0:
                    self._add_issue("orphaned", question.id, ["Question is not linked to any sessions and has no usage"])
    
    def _validate_consistency(self, questions: List[Question]):
        """Validate data consistency across questions."""
        logger.info("Validating data consistency...")
        
        # Check for questions with same text but different categories
        category_groups = {}
        for question in questions:
            text = question.question_text.lower().strip()
            if text not in category_groups:
                category_groups[text] = set()
            category_groups[text].add(question.category)
        
        for text, categories in category_groups.items():
            if len(categories) > 1:
                # Find questions with this text
                for question in questions:
                    if question.question_text.lower().strip() == text:
                        self._add_issue("consistency", question.id, 
                                      [f"Same question text appears in multiple categories: {categories}"])
    
    def _add_issue(self, issue_type: str, question_id: str, issues: List[str]):
        """Add an issue to the validation results."""
        self.validation_results["issues_found"] += 1
        self.validation_results["issues"].append({
            "type": issue_type,
            "question_id": str(question_id),
            "issues": issues,
            "timestamp": datetime.utcnow().isoformat()
        })
    
    def _calculate_quality_score(self):
        """Calculate overall quality score."""
        total_questions = self.validation_results["total_questions"]
        issues_found = self.validation_results["issues_found"]
        
        if total_questions == 0:
            self.validation_results["quality_score"] = 0.0
        else:
            # Calculate score based on issues per question
            issues_per_question = issues_found / total_questions
            # Convert to 0-100 scale (lower issues = higher score)
            self.validation_results["quality_score"] = max(0, 100 - (issues_per_question * 100))
        
        self.validation_results["valid_questions"] = total_questions - issues_found
    
    def generate_quality_report(self) -> str:
        """Generate a detailed quality report."""
        report = []
        report.append("=" * 60)
        report.append("QUESTION BANK QUALITY REPORT")
        report.append("=" * 60)
        report.append(f"Generated: {datetime.utcnow().isoformat()}")
        report.append("")
        
        # Summary
        report.append("SUMMARY:")
        report.append(f"  Total Questions: {self.validation_results['total_questions']}")
        report.append(f"  Valid Questions: {self.validation_results['valid_questions']}")
        report.append(f"  Issues Found: {self.validation_results['issues_found']}")
        report.append(f"  Quality Score: {self.validation_results['quality_score']:.1f}/100")
        report.append("")
        
        # Issues by type
        issue_types = {}
        for issue in self.validation_results["issues"]:
            issue_type = issue["type"]
            if issue_type not in issue_types:
                issue_types[issue_type] = 0
            issue_types[issue_type] += 1
        
        if issue_types:
            report.append("ISSUES BY TYPE:")
            for issue_type, count in sorted(issue_types.items()):
                report.append(f"  {issue_type}: {count}")
            report.append("")
        
        # Detailed issues
        if self.validation_results["issues"]:
            report.append("DETAILED ISSUES:")
            for issue in self.validation_results["issues"][:20]:  # Show first 20 issues
                report.append(f"  Question {issue['question_id']} ({issue['type']}):")
                for problem in issue["issues"]:
                    report.append(f"    - {problem}")
                report.append("")
            
            if len(self.validation_results["issues"]) > 20:
                report.append(f"  ... and {len(self.validation_results['issues']) - 20} more issues")
        
        # Recommendations
        report.append("RECOMMENDATIONS:")
        if self.validation_results["quality_score"] < 70:
            report.append("  - Quality score is below 70. Consider reviewing and fixing issues.")
        if issue_types.get("duplicate", 0) > 0:
            report.append("  - Remove duplicate questions to improve data quality.")
        if issue_types.get("orphaned", 0) > 0:
            report.append("  - Review orphaned questions and either link them to sessions or remove them.")
        if issue_types.get("metadata", 0) > 0:
            report.append("  - Fix missing or invalid metadata for better question management.")
        
        return "\n".join(report)
    
    def fix_common_issues(self, dry_run: bool = True) -> Dict[str, Any]:
        """Fix common issues found during validation."""
        logger.info("🔧 Fixing common issues...")
        
        fixes_applied = {
            "questions_updated": 0,
            "questions_deleted": 0,
            "errors": 0
        }
        
        with Session(self.engine) as db:
            # Fix empty metadata
            questions_with_empty_metadata = db.execute(
                select(Question).where(
                    or_(
                        Question.question_metadata.is_(None),
                        Question.question_metadata == {}
                    )
                )
            ).scalars().all()
            
            for question in questions_with_empty_metadata:
                try:
                    if not dry_run:
                        question.question_metadata = {
                            "source": "validation_fix",
                            "fixed_at": datetime.utcnow().isoformat()
                        }
                        db.commit()
                    fixes_applied["questions_updated"] += 1
                except Exception as e:
                    logger.error(f"Error fixing metadata for question {question.id}: {e}")
                    fixes_applied["errors"] += 1
            
            # Fix invalid difficulty levels
            questions_with_invalid_difficulty = db.execute(
                select(Question).where(
                    Question.difficulty_level.notin_(["easy", "medium", "hard"])
                )
            ).scalars().all()
            
            for question in questions_with_invalid_difficulty:
                try:
                    if not dry_run:
                        question.difficulty_level = "medium"  # Default to medium
                        db.commit()
                    fixes_applied["questions_updated"] += 1
                except Exception as e:
                    logger.error(f"Error fixing difficulty for question {question.id}: {e}")
                    fixes_applied["errors"] += 1
            
            # Remove duplicate questions (keep the oldest)
            duplicate_texts = db.execute(
                select(Question.question_text, func.count(Question.id))
                .group_by(Question.question_text)
                .having(func.count(Question.id) > 1)
            ).fetchall()
            
            for question_text, count in duplicate_texts:
                duplicates = db.execute(
                    select(Question).where(Question.question_text == question_text)
                    .order_by(Question.created_at)
                ).scalars().all()
                
                # Keep the first one, remove the rest
                for question in duplicates[1:]:
                    try:
                        if not dry_run:
                            db.delete(question)
                            db.commit()
                        fixes_applied["questions_deleted"] += 1
                    except Exception as e:
                        logger.error(f"Error deleting duplicate question {question.id}: {e}")
                        fixes_applied["errors"] += 1
        
        return fixes_applied

def main():
    """Main function for running validation."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Question Bank Validation Tool")
    parser.add_argument("--fix", action="store_true", help="Fix common issues found during validation")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be fixed without making changes")
    parser.add_argument("--report", action="store_true", help="Generate detailed quality report")
    
    args = parser.parse_args()
    
    validator = QuestionBankValidator()
    
    # Run validation
    results = validator.run_full_validation()
    
    # Print results
    print(f"📊 Validation Results:")
    print(f"  Total Questions: {results['total_questions']}")
    print(f"  Valid Questions: {results['valid_questions']}")
    print(f"  Issues Found: {results['issues_found']}")
    print(f"  Quality Score: {results['quality_score']:.1f}/100")
    
    # Generate report if requested
    if args.report:
        report = validator.generate_quality_report()
        print("\n" + report)
    
    # Fix issues if requested
    if args.fix:
        fixes = validator.fix_common_issues(dry_run=args.dry_run)
        print(f"\n🔧 Fixes Applied:")
        print(f"  Questions Updated: {fixes['questions_updated']}")
        print(f"  Questions Deleted: {fixes['questions_deleted']}")
        print(f"  Errors: {fixes['errors']}")

if __name__ == "__main__":
    main()
