"""
Question Bank Service for intelligent question selection and management.

This service provides the foundation for the database-first question bank system,
enabling 80-90% reduction in AI API calls while maintaining high-quality question sets.
"""
import hashlib
import json
import random
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc
from app.database.models import Question, SessionQuestion, InterviewSession
from app.utils.logger import get_logger
from app.utils.validation_mixin import ValidationMixin
from app.models.schemas import ParseJDResponse

logger = get_logger(__name__)

class QuestionBankService:
    """Service for managing the global question bank and intelligent question selection."""
    
    # Centralized categorization rules (shared with async service)
    CATEGORIZATION_RULES = {
        "behavioral": [
            "experience", "tell me about", "describe", "situation", "behavioral"
        ],
        "system_design": [
            "system", "architecture", "design", "scale", "distributed"
        ],
        "leadership": [
            "lead", "manage", "team", "mentor", "leadership"
        ],
        "technical": []  # Default category
    }
    
    def __init__(self, db_session: Session):
        self.db = db_session
    
    def get_questions_for_role(self, role: str, job_description: str, count: int = 10) -> List[Question]:
        """
        Get questions for a specific role using intelligent selection algorithms.
        
        Args:
            role: The job role/title
            job_description: The job description text
            count: Number of questions to return
            
        Returns:
            List of selected questions
        """
        try:
            # Define processing pipeline
            pipeline = [
                lambda r, jd: self._analyze_role(r, jd),
                lambda analysis: self._find_compatible_questions(analysis),
                lambda questions: self._ensure_question_diversity(questions, count),
                self._update_usage_stats
            ]
            
            # Execute pipeline
            result = (role, job_description)
            for step in pipeline:
                result = step(*result) if isinstance(result, tuple) else step(result)
            
            logger.info(f"Selected {len(result)} questions for role '{role}'")
            return result
            
        except Exception as e:
            logger.error(f"Error selecting questions for role '{role}': {e}")
            return self._get_fallback_questions(role, count)
    
    def store_generated_questions(self, questions: List[str], role: str, job_description: str, 
                                ai_service_used: str, prompt_hash: str) -> List[Question]:
        """
        Store AI-generated questions in the question bank for future reuse.
        
        Args:
            questions: List of question texts
            role: The job role
            job_description: The job description
            ai_service_used: Which AI service generated these questions
            prompt_hash: Hash of the generation prompt
            
        Returns:
            List of stored Question objects
        """
        try:
            role_analysis = self._analyze_role(role, job_description)
            stored_questions = []
            
            for question_text in questions:
                # Check if similar question already exists
                existing_question = self._find_similar_question(question_text)
                if existing_question:
                    logger.info(f"Similar question already exists, skipping: {question_text[:50]}...")
                    stored_questions.append(existing_question)
                    continue
                
                # Create new question
                question = Question(
                    question_text=question_text,
                    question_metadata=self._create_question_metadata(role_analysis),
                    difficulty_level=self._determine_difficulty(question_text, role_analysis),
                    category=self._categorize_question(question_text),
                    subcategory=self._get_subcategory(question_text),
                    compatible_roles=[role],
                    required_skills=role_analysis.get('required_skills', []),
                    industry_tags=role_analysis.get('industry_tags', []),
                    ai_service_used=ai_service_used,
                    generation_prompt_hash=prompt_hash
                )
                
                self.db.add(question)
                stored_questions.append(question)
            
            self.db.commit()
            logger.info(f"Stored {len(stored_questions)} new questions in question bank")
            return stored_questions
            
        except Exception as e:
            logger.error(f"Error storing questions: {e}")
            self.db.rollback()
            return []
    
    def link_questions_to_session(self, session_id: str, questions: List[Question], 
                                session_context: Optional[Dict] = None) -> List[SessionQuestion]:
        """
        Link questions to a session with ordering and context.
        
        Args:
            session_id: The session ID
            questions: List of questions to link
            session_context: Optional session-specific context
            
        Returns:
            List of SessionQuestion objects
        """
        try:
            session_questions = []
            
            for i, question in enumerate(questions):
                session_question = SessionQuestion(
                    session_id=session_id,
                    question_id=question.id,
                    question_order=i + 1,
                    session_specific_context=session_context
                )
                self.db.add(session_question)
                session_questions.append(session_question)
            
            self.db.commit()
            logger.info(f"Linked {len(session_questions)} questions to session {session_id}")
            return session_questions
            
        except Exception as e:
            logger.error(f"Error linking questions to session: {e}")
            self.db.rollback()
            return []
    
    def get_session_questions(self, session_id: str) -> List[Tuple[Question, SessionQuestion]]:
        """
        Get all questions for a session with their session-specific data.
        
        Args:
            session_id: The session ID
            
        Returns:
            List of (Question, SessionQuestion) tuples ordered by question_order
        """
        try:
            results = self.db.query(Question, SessionQuestion)\
                .join(SessionQuestion, Question.id == SessionQuestion.question_id)\
                .filter(SessionQuestion.session_id == session_id)\
                .order_by(SessionQuestion.question_order)\
                .all()
            
            return results
            
        except Exception as e:
            logger.error(f"Error getting session questions: {e}")
            return []
    
    def update_question_performance(self, question_id: str, score: float, success: bool):
        """
        Update question performance metrics.
        
        Args:
            question_id: The question ID
            score: The score received (0-10)
            success: Whether the answer was considered successful
        """
        try:
            question = self.db.query(Question).filter(Question.id == question_id).first()
            if not question:
                logger.warning(f"Question {question_id} not found for performance update")
                return
            
            # Update usage count
            question.usage_count += 1
            
            # Update performance metrics using helper methods
            question.average_score = self._update_running_average(question.average_score, score, question.usage_count)
            question.success_rate = self._update_success_rate(question.success_rate, success, question.usage_count)
            
            self.db.commit()
            logger.debug(f"Updated performance for question {question_id}: score={score}, success={success}")
            
        except Exception as e:
            logger.error(f"Error updating question performance: {e}")
            self.db.rollback()
    
    def _analyze_role(self, role: str, job_description: str) -> Dict[str, Any]:
        """Analyze role and job description to extract key information."""
        # Simple role analysis - can be enhanced with NLP in the future
        role_lower = role.lower()
        jd_lower = job_description.lower()
        
        # Extract skills (basic keyword matching)
        skills = []
        skill_keywords = {
            'python': ['python', 'django', 'flask', 'fastapi'],
            'javascript': ['javascript', 'node.js', 'react', 'vue', 'angular'],
            'java': ['java', 'spring', 'hibernate'],
            'sql': ['sql', 'postgresql', 'mysql', 'database'],
            'aws': ['aws', 'amazon web services', 'cloud'],
            'docker': ['docker', 'kubernetes', 'containerization'],
            'machine_learning': ['ml', 'machine learning', 'ai', 'tensorflow', 'pytorch']
        }
        
        for skill, keywords in skill_keywords.items():
            if any(keyword in jd_lower for keyword in keywords):
                skills.append(skill)
        
        # Determine industry
        industry = 'technology'  # Default
        industry_keywords = {
            'finance': ['banking', 'finance', 'fintech', 'investment'],
            'healthcare': ['healthcare', 'medical', 'pharmaceutical'],
            'ecommerce': ['ecommerce', 'retail', 'shopping'],
            'education': ['education', 'learning', 'edtech']
        }
        
        for ind, keywords in industry_keywords.items():
            if any(keyword in jd_lower for keyword in keywords):
                industry = ind
                break
        
        # Determine seniority level
        seniority = 'mid'  # Default
        if any(word in jd_lower for word in ['senior', 'lead', 'principal', 'architect']):
            seniority = 'senior'
        elif any(word in jd_lower for word in ['junior', 'entry', 'graduate']):
            seniority = 'junior'
        
        return {
            'role': role,
            'required_skills': skills,
            'industry': industry,
            'seniority_level': seniority,
            'job_description': job_description
        }
    
    def _find_compatible_questions(self, role_analysis: Dict[str, Any]) -> List[Question]:
        """Find questions compatible with the role analysis."""
        try:
            # Build query conditions
            conditions = []
            
            # Filter by compatible roles
            if role_analysis.get('role'):
                conditions.append(
                    or_(
                        Question.compatible_roles.contains([role_analysis['role']]),
                        Question.compatible_roles.is_(None)  # Questions without role restrictions
                    )
                )
            
            # Filter by required skills
            if role_analysis.get('required_skills'):
                skill_conditions = []
                for skill in role_analysis['required_skills']:
                    skill_conditions.append(Question.required_skills.contains([skill]))
                if skill_conditions:
                    conditions.append(or_(*skill_conditions))
            
            # Filter by industry
            if role_analysis.get('industry'):
                conditions.append(
                    or_(
                        Question.industry_tags.contains([role_analysis['industry']]),
                        Question.industry_tags.is_(None)  # Questions without industry restrictions
                    )
                )
            
            # Base query
            query = self.db.query(Question)
            
            # Apply conditions
            if conditions:
                query = query.filter(and_(*conditions))
            
            # Order by quality metrics (success rate, usage count)
            query = query.order_by(
                desc(Question.success_rate),
                desc(Question.usage_count),
                desc(Question.average_score)
            )
            
            # Limit to reasonable number for diversity selection
            compatible_questions = query.limit(100).all()
            
            logger.debug(f"Found {len(compatible_questions)} compatible questions for role analysis")
            return compatible_questions
            
        except Exception as e:
            logger.error(f"Error finding compatible questions: {e}")
            return []
    
    def _ensure_question_diversity(self, questions: List[Question], count: int) -> List[Question]:
        """Ensure question diversity using functional approach."""
        if len(questions) <= count:
            return questions
        
        # Group questions by category and difficulty
        grouped = self._group_questions_by_diversity(questions)
        
        # Select diverse questions first, then fill remaining slots
        selected = self._select_diverse_questions(grouped, count)
        remaining_needed = count - len(selected)
        
        if remaining_needed > 0:
            remaining = [q for q in questions if q not in selected]
            remaining.sort(key=lambda q: (q.success_rate or 0, q.usage_count), reverse=True)
            selected.extend(remaining[:remaining_needed])
        
        return selected[:count]
    
    def _group_questions_by_diversity(self, questions: List[Question]) -> Dict[str, List[Question]]:
        """Group questions by category and difficulty."""
        from collections import defaultdict
        grouped = defaultdict(list)
        for question in questions:
            key = f"{question.category}_{question.difficulty_level}"
            grouped[key].append(question)
        return grouped
    
    def _select_diverse_questions(self, grouped: Dict[str, List[Question]], count: int) -> List[Question]:
        """Select one question from each diversity group."""
        selected = []
        for questions in grouped.values():
            if questions and len(selected) < count:
                # Select best question from this group
                best_question = max(questions, key=lambda q: (q.success_rate or 0, q.usage_count))
                selected.append(best_question)
        return selected
    
    def _update_usage_stats(self, questions: List[Question]):
        """Update usage statistics for selected questions."""
        try:
            for question in questions:
                question.usage_count += 1
            self.db.commit()
        except Exception as e:
            logger.error(f"Error updating usage stats: {e}")
            self.db.rollback()
    
    def _get_fallback_questions(self, role: str, count: int) -> List[Question]:
        """Get fallback questions when intelligent selection fails."""
        try:
            # Get most popular questions as fallback
            questions = self.db.query(Question)\
                .order_by(desc(Question.usage_count))\
                .limit(count)\
                .all()
            
            if not questions:
                logger.warning("No questions found in question bank for fallback")
                return []
            
            return questions
            
        except Exception as e:
            logger.error(f"Error getting fallback questions: {e}")
            return []
    
    def _find_similar_question(self, question_text: str) -> Optional[Question]:
        """Find if a similar question already exists in the database."""
        try:
            # Simple similarity check - can be enhanced with vector similarity
            questions = self.db.query(Question).all()
            
            for question in questions:
                # Check for high similarity (simple word overlap)
                similarity = self._calculate_similarity(question_text, question.question_text)
                if similarity > 0.8:  # 80% similarity threshold
                    return question
            
            return None
            
        except Exception as e:
            logger.error(f"Error finding similar question: {e}")
            return None
    
    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """Calculate simple text similarity based on word overlap."""
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        return len(intersection) / len(union) if union else 0.0
    
    def _create_question_metadata(self, role_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Create metadata for a question based on role analysis."""
        return {
            'role_analysis': role_analysis,
            'generated_at': '2024-01-15T10:00:00Z',  # Will be set by database
            'version': '1.0'
        }
    
    # Data-driven difficulty rules
    DIFFICULTY_RULES = [
        ('seniority', {'senior': 'hard', 'junior': 'easy', 'mid': 'medium'}),
        ('keywords', {
            'hard': ['complex', 'advanced', 'architecture', 'design', 'optimize'],
            'easy': ['basic', 'simple', 'explain', 'what is']
        })
    ]

    def _determine_difficulty(self, question_text: str, role_analysis: Dict[str, Any]) -> str:
        """Determine question difficulty using data-driven approach."""
        for rule_type, rule_data in self.DIFFICULTY_RULES:
            if difficulty := self._apply_difficulty_rule(rule_type, rule_data, question_text, role_analysis):
                return difficulty
        return 'medium'

    def _apply_difficulty_rule(self, rule_type: str, rule_data: dict, question_text: str, role_analysis: Dict[str, Any]) -> Optional[str]:
        """Apply a specific difficulty rule."""
        if rule_type == 'seniority':
            return rule_data.get(role_analysis.get('seniority_level', 'mid'))
        elif rule_type == 'keywords':
            text_lower = question_text.lower()
            for difficulty, keywords in rule_data.items():
                if any(word in text_lower for word in keywords):
                    return difficulty
        return None
    
    def _categorize_question(self, question_text: str) -> str:
        """Categorize question using centralized rules."""
        return self._categorize_by_keywords(question_text, self.CATEGORIZATION_RULES)
    
    def _categorize_by_keywords(self, text: str, rules: Dict[str, List[str]]) -> str:
        """Generic keyword-based categorization."""
        return ValidationMixin.categorize_by_keywords(text, rules)
    
    def _update_running_average(self, current_avg: Optional[float], new_value: float, count: int) -> float:
        """Calculate running average with null handling."""
        return new_value if current_avg is None else (current_avg * (count - 1) + new_value) / count

    def _update_success_rate(self, current_rate: Optional[float], success: bool, count: int) -> float:
        """Calculate running success rate with null handling."""
        if current_rate is None:
            return 1.0 if success else 0.0
        
        total_successes = current_rate * (count - 1)
        if success:
            total_successes += 1
        return total_successes / count

    def _get_subcategory(self, question_text: str) -> Optional[str]:
        """Get question subcategory based on content."""
        text_lower = question_text.lower()
        
        # Technical subcategories
        if 'algorithm' in text_lower or 'data structure' in text_lower:
            return 'algorithms'
        elif 'database' in text_lower or 'sql' in text_lower:
            return 'database'
        elif 'api' in text_lower or 'rest' in text_lower:
            return 'api_design'
        elif 'security' in text_lower or 'auth' in text_lower:
            return 'security'
        elif 'testing' in text_lower or 'test' in text_lower:
            return 'testing'
        
        return None
    
    def get_question_bank_stats(self) -> Dict[str, Any]:
        """Get statistics about the question bank."""
        try:
            total_questions = self.db.query(Question).count()
            categories = self.db.query(Question.category, func.count(Question.id))\
                .group_by(Question.category)\
                .all()
            difficulties = self.db.query(Question.difficulty_level, func.count(Question.id))\
                .group_by(Question.difficulty_level)\
                .all()
            
            return {
                'total_questions': total_questions,
                'categories': dict(categories),
                'difficulties': dict(difficulties),
                'avg_usage_count': self.db.query(func.avg(Question.usage_count)).scalar() or 0,
                'avg_success_rate': self.db.query(func.avg(Question.success_rate)).scalar() or 0
            }
            
        except Exception as e:
            logger.error(f"Error getting question bank stats: {e}")
            return {}
