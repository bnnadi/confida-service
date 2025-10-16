#!/usr/bin/env python3
"""
Question Bank CLI Tool

This tool provides command-line interface for managing the question bank,
including migration, seeding, statistics, and maintenance operations.
"""

import os
import sys
import json
import argparse
from datetime import datetime
from typing import Dict, Any, List
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy.orm import Session
from sqlalchemy import create_engine, select, func, text
from app.database.models import Question, SessionQuestion, InterviewSession
from app.config import get_settings
from app.utils.logger import get_logger
from scripts.question_bank_migration import QuestionBankMigrator, QuestionBankSeeder

logger = get_logger(__name__)

class QuestionBankCLI:
    """CLI tool for question bank management."""
    
    def __init__(self):
        self.settings = get_settings()
        self.engine = create_engine(self.settings.DATABASE_URL)
    
    def migrate_questions(self, dry_run: bool = False) -> Dict[str, Any]:
        """Migrate existing questions to the question bank."""
        logger.info("🔄 Starting question migration...")
        
        with Session(self.engine) as db:
            migrator = QuestionBankMigrator(db)
            
            if dry_run:
                logger.info("🔍 DRY RUN - No changes will be made")
                # Count questions that would be migrated
                existing_questions = db.execute(
                    select(Question).where(Question.session_id.isnot(None))
                ).scalars().all()
                
                stats = {
                    "questions_to_migrate": len(existing_questions),
                    "sessions_affected": len(set(q.session_id for q in existing_questions)),
                    "dry_run": True
                }
                
                logger.info(f"📊 Would migrate {stats['questions_to_migrate']} questions from {stats['sessions_affected']} sessions")
                return stats
            else:
                return migrator.migrate_existing_questions()
    
    def seed_questions(self, source_file: str = None) -> Dict[str, Any]:
        """Seed the question bank with sample questions."""
        logger.info("🌱 Starting question seeding...")
        
        with Session(self.engine) as db:
            seeder = QuestionBankSeeder(db)
            
            if source_file:
                logger.info(f"📁 Loading questions from {source_file}")
                # Load questions from JSON file
                with open(source_file, 'r') as f:
                    questions_data = json.load(f)
                return self._seed_from_file(db, questions_data)
            else:
                return seeder.seed_comprehensive_question_bank()
    
    def _seed_from_file(self, db: Session, questions_data: Dict[str, Any]) -> Dict[str, Any]:
        """Seed questions from a JSON file."""
        stats = {"questions_created": 0, "errors": 0}
        
        # Process technical questions
        if "technical_questions" in questions_data:
            for category, questions in questions_data["technical_questions"].items():
                for q_data in questions:
                    try:
                        self._create_question_from_data(db, q_data, "technical", category)
                        stats["questions_created"] += 1
                    except Exception as e:
                        logger.error(f"Error creating question: {e}")
                        stats["errors"] += 1
        
        # Process behavioral questions
        if "behavioral_questions" in questions_data:
            for q_data in questions_data["behavioral_questions"]:
                try:
                    self._create_question_from_data(db, q_data, "behavioral", q_data.get("subcategory"))
                    stats["questions_created"] += 1
                except Exception as e:
                    logger.error(f"Error creating question: {e}")
                    stats["errors"] += 1
        
        # Process system design questions
        if "system_design_questions" in questions_data:
            for q_data in questions_data["system_design_questions"]:
                try:
                    self._create_question_from_data(db, q_data, "system_design", q_data.get("subcategory"))
                    stats["questions_created"] += 1
                except Exception as e:
                    logger.error(f"Error creating question: {e}")
                    stats["errors"] += 1
        
        # Process leadership questions
        if "leadership_questions" in questions_data:
            for q_data in questions_data["leadership_questions"]:
                try:
                    self._create_question_from_data(db, q_data, "leadership", q_data.get("subcategory"))
                    stats["questions_created"] += 1
                except Exception as e:
                    logger.error(f"Error creating question: {e}")
                    stats["errors"] += 1
        
        # Process industry-specific questions
        if "industry_specific_questions" in questions_data:
            for industry, questions in questions_data["industry_specific_questions"].items():
                for q_data in questions:
                    try:
                        self._create_question_from_data(db, q_data, "industry_specific", industry)
                        stats["questions_created"] += 1
                    except Exception as e:
                        logger.error(f"Error creating question: {e}")
                        stats["errors"] += 1
        
        db.commit()
        return stats
    
    def _create_question_from_data(self, db: Session, q_data: Dict[str, Any], category: str, subcategory: str = None):
        """Create a question from JSON data."""
        # Check if question already exists
        existing_question = db.execute(
            select(Question).where(Question.question_text == q_data["question"])
        ).scalar_one_or_none()
        
        if existing_question:
            logger.debug(f"Question already exists: {q_data['question'][:50]}...")
            return existing_question
        
        question = Question(
            question_text=q_data["question"],
            question_metadata={
                "source": "json_seeding",
                "seeded_at": datetime.utcnow().isoformat(),
                "version": "1.0"
            },
            difficulty_level=q_data.get("difficulty", "medium"),
            category=category,
            subcategory=subcategory,
            compatible_roles=q_data.get("compatible_roles", []),
            required_skills=q_data.get("skills", []),
            industry_tags=q_data.get("tags", []),
            usage_count=0,
            average_score=None,
            success_rate=None,
            ai_service_used="json_seeded",
            generation_prompt_hash=self._generate_prompt_hash(q_data["question"]),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        db.add(question)
        return question
    
    def _generate_prompt_hash(self, question_text: str) -> str:
        """Generate a hash for the question text."""
        import hashlib
        return hashlib.sha256(question_text.encode()).hexdigest()[:16]
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get comprehensive question bank statistics."""
        logger.info("📊 Gathering question bank statistics...")
        
        with Session(self.engine) as db:
            stats = {}
            
            # Total questions
            total_questions = db.execute(select(func.count(Question.id))).scalar()
            stats["total_questions"] = total_questions
            
            # Questions by category
            category_stats = db.execute(
                select(Question.category, func.count(Question.id))
                .group_by(Question.category)
            ).fetchall()
            stats["by_category"] = {category: count for category, count in category_stats}
            
            # Questions by difficulty
            difficulty_stats = db.execute(
                select(Question.difficulty_level, func.count(Question.id))
                .group_by(Question.difficulty_level)
            ).fetchall()
            stats["by_difficulty"] = {difficulty: count for difficulty, count in difficulty_stats}
            
            # Questions by subcategory
            subcategory_stats = db.execute(
                select(Question.subcategory, func.count(Question.id))
                .where(Question.subcategory.isnot(None))
                .group_by(Question.subcategory)
            ).fetchall()
            stats["by_subcategory"] = {subcategory: count for subcategory, count in subcategory_stats}
            
            # Usage statistics
            usage_stats = db.execute(
                select(
                    func.avg(Question.usage_count).label("avg_usage"),
                    func.max(Question.usage_count).label("max_usage"),
                    func.min(Question.usage_count).label("min_usage")
                )
            ).first()
            stats["usage"] = {
                "average": float(usage_stats.avg_usage) if usage_stats.avg_usage else 0,
                "maximum": usage_stats.max_usage or 0,
                "minimum": usage_stats.min_usage or 0
            }
            
            # Score statistics
            score_stats = db.execute(
                select(
                    func.avg(Question.average_score).label("avg_score"),
                    func.avg(Question.success_rate).label("avg_success_rate")
                )
                .where(Question.average_score.isnot(None))
            ).first()
            stats["scores"] = {
                "average_score": float(score_stats.avg_score) if score_stats.avg_score else None,
                "average_success_rate": float(score_stats.avg_success_rate) if score_stats.avg_success_rate else None
            }
            
            # Recent activity
            recent_questions = db.execute(
                select(func.count(Question.id))
                .where(Question.created_at >= datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0))
            ).scalar()
            stats["recent_activity"] = {
                "questions_added_today": recent_questions
            }
            
            return stats
    
    def search_questions(self, query: str, category: str = None, difficulty: str = None, limit: int = 10) -> List[Dict[str, Any]]:
        """Search questions in the question bank."""
        logger.info(f"🔍 Searching questions with query: '{query}'")
        
        with Session(self.engine) as db:
            search_query = select(Question).where(
                Question.question_text.ilike(f"%{query}%")
            )
            
            if category:
                search_query = search_query.where(Question.category == category)
            
            if difficulty:
                search_query = search_query.where(Question.difficulty_level == difficulty)
            
            search_query = search_query.limit(limit)
            
            results = db.execute(search_query).scalars().all()
            
            return [
                {
                    "id": str(q.id),
                    "question": q.question_text,
                    "category": q.category,
                    "subcategory": q.subcategory,
                    "difficulty": q.difficulty_level,
                    "usage_count": q.usage_count,
                    "average_score": q.average_score,
                    "success_rate": q.success_rate
                }
                for q in results
            ]
    
    def cleanup_duplicates(self, dry_run: bool = False) -> Dict[str, Any]:
        """Clean up duplicate questions in the question bank."""
        logger.info("🧹 Starting duplicate cleanup...")
        
        from app.utils.question_bank_utils import QuestionBankUtils
        
        with Session(self.engine) as db:
            stats = QuestionBankUtils.remove_duplicate_questions(db, dry_run)
            
            if dry_run:
                logger.info(f"🔍 DRY RUN - Found {stats['duplicates_found']} duplicate question groups")
            else:
                logger.info(f"✅ Cleanup completed. Removed {stats['questions_removed']} duplicate questions")
            
            return stats
    
    def export_questions(self, output_file: str, category: str = None, format: str = "json") -> bool:
        """Export questions to a file."""
        logger.info(f"📤 Exporting questions to {output_file}")
        
        with Session(self.engine) as db:
            query = select(Question)
            if category:
                query = query.where(Question.category == category)
            
            questions = db.execute(query).scalars().all()
            
            if format == "json":
                export_data = [
                    {
                        "question": q.question_text,
                        "category": q.category,
                        "subcategory": q.subcategory,
                        "difficulty": q.difficulty_level,
                        "skills": q.required_skills or [],
                        "roles": q.compatible_roles or [],
                        "tags": q.industry_tags or [],
                        "usage_count": q.usage_count,
                        "average_score": q.average_score,
                        "success_rate": q.success_rate
                    }
                    for q in questions
                ]
                
                with open(output_file, 'w') as f:
                    json.dump(export_data, f, indent=2)
            
            elif format == "csv":
                import csv
                with open(output_file, 'w', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow([
                        "question", "category", "subcategory", "difficulty",
                        "skills", "roles", "tags", "usage_count", "average_score", "success_rate"
                    ])
                    
                    for q in questions:
                        writer.writerow([
                            q.question_text,
                            q.category,
                            q.subcategory or "",
                            q.difficulty_level,
                            ",".join(q.required_skills or []),
                            ",".join(q.compatible_roles or []),
                            ",".join(q.industry_tags or []),
                            q.usage_count,
                            q.average_score or "",
                            q.success_rate or ""
                        ])
            
            logger.info(f"✅ Exported {len(questions)} questions to {output_file}")
            return True

def main():
    """Main CLI function."""
    parser = argparse.ArgumentParser(description="Question Bank Management CLI")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Migrate command
    migrate_parser = subparsers.add_parser("migrate", help="Migrate existing questions to question bank")
    migrate_parser.add_argument("--dry-run", action="store_true", help="Show what would be migrated without making changes")
    
    # Seed command
    seed_parser = subparsers.add_parser("seed", help="Seed question bank with sample questions")
    seed_parser.add_argument("--file", help="JSON file containing questions to seed")
    
    # Statistics command
    stats_parser = subparsers.add_parser("stats", help="Show question bank statistics")
    
    # Search command
    search_parser = subparsers.add_parser("search", help="Search questions in the question bank")
    search_parser.add_argument("query", help="Search query")
    search_parser.add_argument("--category", help="Filter by category")
    search_parser.add_argument("--difficulty", help="Filter by difficulty")
    search_parser.add_argument("--limit", type=int, default=10, help="Limit number of results")
    
    # Cleanup command
    cleanup_parser = subparsers.add_parser("cleanup", help="Clean up duplicate questions")
    cleanup_parser.add_argument("--dry-run", action="store_true", help="Show what would be cleaned up without making changes")
    
    # Export command
    export_parser = subparsers.add_parser("export", help="Export questions to file")
    export_parser.add_argument("output_file", help="Output file path")
    export_parser.add_argument("--category", help="Filter by category")
    export_parser.add_argument("--format", choices=["json", "csv"], default="json", help="Export format")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    cli = QuestionBankCLI()
    
    try:
        if args.command == "migrate":
            stats = cli.migrate_questions(dry_run=args.dry_run)
            print(f"📊 Migration Statistics: {json.dumps(stats, indent=2)}")
        
        elif args.command == "seed":
            if args.file:
                stats = cli.seed_questions(source_file=args.file)
            else:
                stats = cli.seed_questions()
            print(f"📊 Seeding Statistics: {json.dumps(stats, indent=2)}")
        
        elif args.command == "stats":
            stats = cli.get_statistics()
            print(f"📊 Question Bank Statistics: {json.dumps(stats, indent=2)}")
        
        elif args.command == "search":
            results = cli.search_questions(
                query=args.query,
                category=args.category,
                difficulty=args.difficulty,
                limit=args.limit
            )
            print(f"🔍 Search Results: {json.dumps(results, indent=2)}")
        
        elif args.command == "cleanup":
            stats = cli.cleanup_duplicates(dry_run=args.dry_run)
            print(f"📊 Cleanup Statistics: {json.dumps(stats, indent=2)}")
        
        elif args.command == "export":
            success = cli.export_questions(
                output_file=args.output_file,
                category=args.category,
                format=args.format
            )
            if success:
                print(f"✅ Questions exported to {args.output_file}")
            else:
                print("❌ Export failed")
    
    except Exception as e:
        logger.error(f"❌ Command failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
