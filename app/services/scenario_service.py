"""
Scenario Service for managing practice interview scenarios.

This service provides database-driven scenario management, replacing the hardcoded
scenario questions in the QuestionEngine with proper database integration.
"""
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc
from app.database.models import Scenario, Question
from app.utils.logger import get_logger
from app.exceptions import AIServiceError
# from app.utils.cache import cache_result  # TODO: Implement caching later

logger = get_logger(__name__)

class ScenarioService:
    """Service for managing practice interview scenarios."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_scenario_by_id(self, scenario_id: str) -> Optional[Scenario]:
        """
        Get a scenario by its ID.
        
        Args:
            scenario_id: The scenario identifier
            
        Returns:
            Scenario object or None if not found
        """
        try:
            scenario = self.db.query(Scenario).filter(
                and_(
                    Scenario.id == scenario_id,
                    Scenario.is_active == True
                )
            ).first()
            
            if scenario:
                logger.info(f"Retrieved scenario: {scenario_id}")
            else:
                logger.warning(f"Scenario not found: {scenario_id}")
                
            return scenario
            
        except Exception as e:
            logger.error(f"Error retrieving scenario {scenario_id}: {e}")
            raise AIServiceError(f"Failed to retrieve scenario: {e}")
    
    def get_all_scenarios(self) -> List[Scenario]:
        """
        Get all active scenarios.
        
        Returns:
            List of active scenarios
        """
        try:
            scenarios = self.db.query(Scenario).filter(
                Scenario.is_active == True
            ).order_by(Scenario.name).all()
            
            logger.info(f"Retrieved {len(scenarios)} active scenarios")
            return scenarios
            
        except Exception as e:
            logger.error(f"Error retrieving scenarios: {e}")
            raise AIServiceError(f"Failed to retrieve scenarios: {e}")
    
    def get_scenarios_by_category(self, category: str) -> List[Scenario]:
        """
        Get scenarios by category.
        
        Args:
            category: The scenario category
            
        Returns:
            List of scenarios in the category
        """
        try:
            scenarios = self.db.query(Scenario).filter(
                and_(
                    Scenario.category == category,
                    Scenario.is_active == True
                )
            ).order_by(Scenario.name).all()
            
            logger.info(f"Retrieved {len(scenarios)} scenarios for category: {category}")
            return scenarios
            
        except Exception as e:
            logger.error(f"Error retrieving scenarios for category {category}: {e}")
            raise AIServiceError(f"Failed to retrieve scenarios for category: {e}")
    
    def get_scenarios_by_role(self, role: str) -> List[Scenario]:
        """
        Get scenarios compatible with a specific role.
        
        Args:
            role: The job role
            
        Returns:
            List of compatible scenarios
        """
        try:
            # Query scenarios where compatible_roles contains the role or is null (compatible with all)
            scenarios = self.db.query(Scenario).filter(
                and_(
                    Scenario.is_active == True,
                    or_(
                        Scenario.compatible_roles.contains([role]),
                        Scenario.compatible_roles.is_(None)
                    )
                )
            ).order_by(Scenario.name).all()
            
            logger.info(f"Retrieved {len(scenarios)} scenarios compatible with role: {role}")
            return scenarios
            
        except Exception as e:
            logger.error(f"Error retrieving scenarios for role {role}: {e}")
            raise AIServiceError(f"Failed to retrieve scenarios for role: {e}")
    
    def get_scenario_questions(self, scenario_id: str) -> List[Dict[str, Any]]:
        """
        Get questions for a specific scenario.
        
        Args:
            scenario_id: The scenario identifier
            
        Returns:
            List of question dictionaries with id, text, and metadata
        """
        try:
            scenario = self.get_scenario_by_id(scenario_id)
            if not scenario:
                raise AIServiceError(f"Scenario not found: {scenario_id}")
            
            # If scenario has specific question IDs, fetch those questions
            if scenario.question_ids:
                question_ids = scenario.question_ids
                
                # Convert string IDs to UUID objects for proper comparison
                from uuid import UUID
                uuid_question_ids = [UUID(q_id) for q_id in question_ids]
                questions = self.db.query(Question).filter(
                    Question.id.in_(uuid_question_ids)
                ).all()
                
                # Create question dictionaries in the order specified by question_ids
                question_dict = {q.id: q for q in questions}
                questions_data = []
                
                for q_id in question_ids:
                    uuid_q_id = UUID(q_id)
                    if uuid_q_id in question_dict:
                        q = question_dict[uuid_q_id]
                        questions_data.append({
                            "id": str(q.id),
                            "text": q.question_text,
                            "type": q.question_metadata.get("type", "behavioral"),
                            "difficulty_level": q.difficulty_level,
                            "category": q.category,
                            "subcategory": q.subcategory,
                            "metadata": q.question_metadata
                        })
                
                logger.info(f"Retrieved {len(questions_data)} questions for scenario {scenario_id}")
                return questions_data
            else:
                # Fallback: return empty list if no questions configured
                logger.warning(f"No questions configured for scenario {scenario_id}")
                return []
                
        except Exception as e:
            logger.error(f"Error retrieving questions for scenario {scenario_id}: {e}")
            raise AIServiceError(f"Failed to retrieve questions for scenario: {e}")
    
    def increment_usage_count(self, scenario_id: str) -> None:
        """
        Increment the usage count for a scenario.
        
        Args:
            scenario_id: The scenario identifier
        """
        try:
            scenario = self.get_scenario_by_id(scenario_id)
            if scenario:
                scenario.usage_count += 1
                self.db.commit()
                logger.info(f"Incremented usage count for scenario {scenario_id}")
            else:
                logger.warning(f"Cannot increment usage count - scenario not found: {scenario_id}")
                
        except Exception as e:
            logger.error(f"Error incrementing usage count for scenario {scenario_id}: {e}")
            self.db.rollback()
            raise AIServiceError(f"Failed to increment usage count: {e}")
    
    def create_scenario(self, scenario_data: Dict[str, Any]) -> Scenario:
        """
        Create a new scenario.
        
        Args:
            scenario_data: Dictionary containing scenario information
            
        Returns:
            Created scenario object
        """
        try:
            scenario = Scenario(
                id=scenario_data["id"],
                name=scenario_data["name"],
                description=scenario_data.get("description"),
                category=scenario_data.get("category"),
                difficulty_level=scenario_data.get("difficulty_level", "medium"),
                compatible_roles=scenario_data.get("compatible_roles"),
                question_ids=scenario_data.get("question_ids"),
                is_active=scenario_data.get("is_active", True),
                usage_count=0,
                average_rating=scenario_data.get("average_rating")
            )
            
            self.db.add(scenario)
            self.db.commit()
            self.db.refresh(scenario)
            
            logger.info(f"Created scenario: {scenario.id}")
            return scenario
            
        except Exception as e:
            logger.error(f"Error creating scenario: {e}")
            self.db.rollback()
            raise AIServiceError(f"Failed to create scenario: {e}")
    
    def update_scenario(self, scenario_id: str, update_data: Dict[str, Any]) -> Optional[Scenario]:
        """
        Update an existing scenario.
        
        Args:
            scenario_id: The scenario identifier
            update_data: Dictionary containing fields to update
            
        Returns:
            Updated scenario object or None if not found
        """
        try:
            scenario = self.get_scenario_by_id(scenario_id)
            if not scenario:
                return None
            
            # Update fields
            for field, value in update_data.items():
                if hasattr(scenario, field):
                    setattr(scenario, field, value)
            
            self.db.commit()
            self.db.refresh(scenario)
            
            logger.info(f"Updated scenario: {scenario_id}")
            return scenario
            
        except Exception as e:
            logger.error(f"Error updating scenario {scenario_id}: {e}")
            self.db.rollback()
            raise AIServiceError(f"Failed to update scenario: {e}")
    
    def delete_scenario(self, scenario_id: str) -> bool:
        """
        Soft delete a scenario by setting is_active to False.
        
        Args:
            scenario_id: The scenario identifier
            
        Returns:
            True if deleted, False if not found
        """
        try:
            scenario = self.get_scenario_by_id(scenario_id)
            if not scenario:
                return False
            
            scenario.is_active = False
            self.db.commit()
            
            logger.info(f"Deleted scenario: {scenario_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting scenario {scenario_id}: {e}")
            self.db.rollback()
            raise AIServiceError(f"Failed to delete scenario: {e}")
    
    def get_scenario_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about scenarios.
        
        Returns:
            Dictionary containing scenario statistics
        """
        try:
            total_scenarios = self.db.query(Scenario).count()
            active_scenarios = self.db.query(Scenario).filter(Scenario.is_active == True).count()
            total_usage = self.db.query(func.sum(Scenario.usage_count)).scalar() or 0
            
            # Get most popular scenarios
            popular_scenarios = self.db.query(Scenario).filter(
                Scenario.is_active == True
            ).order_by(desc(Scenario.usage_count)).limit(5).all()
            
            stats = {
                "total_scenarios": total_scenarios,
                "active_scenarios": active_scenarios,
                "total_usage": total_usage,
                "popular_scenarios": [
                    {
                        "id": s.id,
                        "name": s.name,
                        "usage_count": s.usage_count
                    } for s in popular_scenarios
                ]
            }
            
            logger.info(f"Retrieved scenario statistics: {stats}")
            return stats
            
        except Exception as e:
            logger.error(f"Error retrieving scenario statistics: {e}")
            raise AIServiceError(f"Failed to retrieve scenario statistics: {e}")
