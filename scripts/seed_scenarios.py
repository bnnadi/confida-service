#!/usr/bin/env python3
"""
Seed script for populating scenarios table with initial practice scenarios.

This script migrates the hardcoded scenario data from QuestionEngine to the database.
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from app.database.connection import get_db
from app.services.scenario_service import ScenarioService
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Original hardcoded scenario data from QuestionEngine
SCENARIO_DATA = [
    {
        "id": "software_engineer",
        "name": "Software Engineer",
        "description": "Practice questions for software engineering roles",
        "category": "technical",
        "difficulty_level": "medium",
        "compatible_roles": ["software_engineer", "backend_developer", "frontend_developer", "full_stack_developer"],
        "questions": [
            "Tell me about a challenging technical problem you solved recently.",
            "How do you approach debugging a complex issue?",
            "Describe a time when you had to learn a new technology quickly.",
            "How do you ensure code quality in your projects?",
            "Tell me about a time you had to work with a difficult team member."
        ]
    },
    {
        "id": "data_scientist",
        "name": "Data Scientist",
        "description": "Practice questions for data science roles",
        "category": "technical",
        "difficulty_level": "medium",
        "compatible_roles": ["data_scientist", "data_analyst", "machine_learning_engineer"],
        "questions": [
            "Describe a data analysis project you're particularly proud of.",
            "How do you handle missing or incomplete data?",
            "Tell me about a time you had to explain complex data insights to non-technical stakeholders.",
            "What's your approach to feature selection in machine learning?",
            "Describe a time when your analysis led to a significant business decision."
        ]
    },
    {
        "id": "product_manager",
        "name": "Product Manager",
        "description": "Practice questions for product management roles",
        "category": "business",
        "difficulty_level": "medium",
        "compatible_roles": ["product_manager", "product_owner", "product_analyst"],
        "questions": [
            "How do you prioritize features for a product roadmap?",
            "Tell me about a time you had to make a difficult product decision.",
            "How do you gather and analyze user feedback?",
            "Describe a time when you had to manage conflicting stakeholder requirements.",
            "How do you measure the success of a product feature?"
        ]
    },
    {
        "id": "sales_representative",
        "name": "Sales Representative",
        "description": "Practice questions for sales roles",
        "category": "business",
        "difficulty_level": "medium",
        "compatible_roles": ["sales_representative", "account_manager", "business_development"],
        "questions": [
            "Tell me about your most successful sales achievement.",
            "How do you handle objections from potential customers?",
            "Describe a time when you had to rebuild a relationship with a difficult client.",
            "How do you qualify leads and prospects?",
            "Tell me about a time you had to meet an aggressive sales target."
        ]
    },
    {
        "id": "marketing_manager",
        "name": "Marketing Manager",
        "description": "Practice questions for marketing roles",
        "category": "business",
        "difficulty_level": "medium",
        "compatible_roles": ["marketing_manager", "digital_marketing", "content_marketing"],
        "questions": [
            "Describe a successful marketing campaign you've managed.",
            "How do you measure the ROI of marketing activities?",
            "Tell me about a time you had to pivot a marketing strategy mid-campaign.",
            "How do you stay updated with marketing trends and technologies?",
            "Describe a time when you had to work with a limited marketing budget."
        ]
    }
]

def create_questions_for_scenario(db: Session, scenario_data: dict) -> list:
    """Create Question objects for a scenario and return their IDs."""
    from app.database.models import Question
    from datetime import datetime
    
    question_ids = []
    
    for i, question_text in enumerate(scenario_data["questions"]):
        # Create question in the global question bank
        question = Question(
            question_text=question_text,
            question_metadata={
                "type": "behavioral",
                "source": "scenario",
                "scenario_id": scenario_data["id"],
                "order": i + 1
            },
            difficulty_level=scenario_data["difficulty_level"],
            category=scenario_data["category"],
            subcategory="practice",
            compatible_roles=scenario_data["compatible_roles"],
            usage_count=0,
            ai_service_used="scenario_seed"
        )
        
        db.add(question)
        db.flush()  # Get the ID without committing
        question_ids.append(str(question.id))
        
        logger.info(f"Created question {i+1} for scenario {scenario_data['id']}: {question_text[:50]}...")
    
    return question_ids

def seed_scenarios():
    """Seed the scenarios table with initial data."""
    try:
        # Get database session
        db = next(get_db())
        scenario_service = ScenarioService(db)
        
        logger.info("Starting scenario seeding process...")
        
        # Check if scenarios already exist
        existing_scenarios = scenario_service.get_all_scenarios()
        if existing_scenarios:
            logger.warning(f"Found {len(existing_scenarios)} existing scenarios. Skipping seeding.")
            return
        
        created_count = 0
        
        for scenario_data in SCENARIO_DATA:
            try:
                # Create questions for this scenario
                question_ids = create_questions_for_scenario(db, scenario_data)
                
                # Create scenario with question references
                scenario_payload = {
                    "id": scenario_data["id"],
                    "name": scenario_data["name"],
                    "description": scenario_data["description"],
                    "category": scenario_data["category"],
                    "difficulty_level": scenario_data["difficulty_level"],
                    "compatible_roles": scenario_data["compatible_roles"],
                    "question_ids": question_ids,
                    "is_active": True,
                    "usage_count": 0
                }
                
                scenario = scenario_service.create_scenario(scenario_payload)
                created_count += 1
                
                logger.info(f"Created scenario: {scenario.id} with {len(question_ids)} questions")
                
            except Exception as e:
                logger.error(f"Error creating scenario {scenario_data['id']}: {e}")
                db.rollback()
                continue
        
        # Commit all changes
        db.commit()
        
        logger.info(f"Successfully seeded {created_count} scenarios with questions")
        
        # Verify seeding
        final_scenarios = scenario_service.get_all_scenarios()
        logger.info(f"Verification: {len(final_scenarios)} scenarios now exist in database")
        
        # Print summary
        print("\n" + "="*60)
        print("SCENARIO SEEDING COMPLETED")
        print("="*60)
        print(f"Created scenarios: {created_count}")
        print(f"Total scenarios in database: {len(final_scenarios)}")
        print("\nScenarios created:")
        for scenario in final_scenarios:
            print(f"  - {scenario.id}: {scenario.name} ({len(scenario.question_ids or [])} questions)")
        print("="*60)
        
    except Exception as e:
        logger.error(f"Error during scenario seeding: {e}")
        if 'db' in locals():
            db.rollback()
        raise
    finally:
        if 'db' in locals():
            db.close()

if __name__ == "__main__":
    seed_scenarios()
