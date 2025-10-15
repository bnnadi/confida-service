"""
Intelligent Question Matcher for Phase 2: Gradual Database Enhancement

This service matches user requests to existing questions in the database,
reducing AI service calls and optimizing costs while maintaining quality.
"""

import hashlib
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
from app.database.question_database_models import QuestionTemplate, QuestionMatch
from app.services.job_description_processor import ImprovedJobDescriptionProcessor
from app.utils.logger import get_logger

logger = get_logger(__name__)

@dataclass
class MatchResult:
    """Result of question matching process."""
    question_template: QuestionTemplate
    match_score: float
    confidence_level: float
    matched_criteria: Dict[str, Any]
    reasoning: str

@dataclass
class QuestionMatchRequest:
    """Request for question matching."""
    role: str
    job_description: str
    complexity_score: float
    target_questions: int = 10
    min_confidence: float = 0.7
    max_matches: int = 20

class IntelligentQuestionMatcher:
    """
    Intelligent question matcher that finds relevant questions from the database
    based on role, job description, and complexity analysis.
    """
    
    def __init__(self, db_session: Session):
        self.db_session = db_session
        self.job_processor = ImprovedJobDescriptionProcessor()
        
        # Matching weights for different criteria
        self.matching_weights = {
            'role_match': 0.3,
            'skill_match': 0.25,
            'difficulty_match': 0.2,
            'domain_match': 0.15,
            'industry_match': 0.1
        }
    
    def find_matching_questions(self, request: QuestionMatchRequest) -> List[MatchResult]:
        """
        Find matching questions from the database.
        
        Args:
            request: QuestionMatchRequest with role, job description, etc.
            
        Returns:
            List of MatchResult objects with matching questions
        """
        try:
            # Extract key information from job description
            job_analysis = self._analyze_job_description(request.job_description)
            
            # Generate request hash for caching
            request_hash = self._generate_request_hash(request.role, request.job_description)
            
            # Check for existing matches first
            existing_match = self._get_existing_match(request_hash)
            if existing_match and existing_match.confidence_level >= request.min_confidence:
                logger.info(f"Found existing high-confidence match: {existing_match.confidence_level}")
                return self._get_questions_from_match(existing_match)
            
            # Find new matches
            matches = self._find_new_matches(request, job_analysis)
            
            # Store successful matches
            if matches:
                self._store_match_results(request_hash, matches, job_analysis)
            
            return matches
            
        except Exception as e:
            logger.error(f"Error in question matching: {e}")
            return []
    
    def _analyze_job_description(self, job_description: str) -> Dict[str, Any]:
        """Analyze job description to extract matching criteria."""
        try:
            # Use job description processor to extract key information
            analysis = self.job_processor.process_job_description(job_description, 500)
            
            return {
                'technical_skills': analysis.technical_skills,
                'soft_skills': analysis.soft_skills,
                'experience_requirements': analysis.experience_requirements,
                'company_info': analysis.company_info,
                'key_requirements': analysis.key_requirements,
                'complexity_indicators': self._extract_complexity_indicators(job_description)
            }
        except Exception as e:
            logger.error(f"Error analyzing job description: {e}")
            return {
                'technical_skills': [],
                'soft_skills': [],
                'experience_requirements': [],
                'company_info': {},
                'key_requirements': [],
                'complexity_indicators': []
            }
    
    def _extract_complexity_indicators(self, job_description: str) -> List[str]:
        """Extract complexity indicators from job description."""
        complexity_keywords = [
            'senior', 'lead', 'principal', 'architect', 'staff',
            'microservices', 'distributed', 'scalability', 'performance',
            'machine learning', 'ai', 'data science', 'algorithms',
            'system design', 'architecture', 'optimization'
        ]
        
        job_lower = job_description.lower()
        found_indicators = [keyword for keyword in complexity_keywords if keyword in job_lower]
        return found_indicators
    
    def _generate_request_hash(self, role: str, job_description: str) -> str:
        """Generate hash for request caching."""
        content = f"{role.lower().strip()}:{job_description.strip()}"
        return hashlib.sha256(content.encode()).hexdigest()
    
    def _get_existing_match(self, request_hash: str) -> Optional[QuestionMatch]:
        """Get existing high-confidence match for request."""
        return self.db_session.query(QuestionMatch).filter(
            and_(
                QuestionMatch.user_request_hash == request_hash,
                QuestionMatch.confidence_level >= 0.8
            )
        ).order_by(QuestionMatch.last_used.desc()).first()
    
    def _find_new_matches(self, request: QuestionMatchRequest, job_analysis: Dict[str, Any]) -> List[MatchResult]:
        """Find new question matches based on analysis."""
        # Build query for matching questions
        query = self.db_session.query(QuestionTemplate).filter(
            QuestionTemplate.is_active == True
        )
        
        # Apply filters based on analysis
        query = self._apply_role_filters(query, request.role, job_analysis)
        query = self._apply_skill_filters(query, job_analysis['technical_skills'])
        query = self._apply_difficulty_filters(query, request.complexity_score)
        
        # Get potential matches
        potential_questions = query.limit(50).all()
        
        # Score and rank matches
        matches = []
        for question in potential_questions:
            match_result = self._score_question_match(question, request, job_analysis)
            if match_result.confidence_level >= request.min_confidence:
                matches.append(match_result)
        
        # Sort by confidence and return top matches
        matches.sort(key=lambda x: x.confidence_level, reverse=True)
        return matches[:request.max_matches]
    
    def _apply_role_filters(self, query, role: str, job_analysis: Dict[str, Any]) -> Any:
        """Apply role-based filters to query."""
        role_lower = role.lower()
        
        # Determine seniority level
        seniority_levels = []
        if any(word in role_lower for word in ['senior', 'sr', 'lead', 'principal', 'staff']):
            seniority_levels.extend(['senior', 'lead', 'principal', 'staff'])
        elif any(word in role_lower for word in ['junior', 'jr', 'entry', 'associate']):
            seniority_levels.extend(['junior', 'entry', 'associate'])
        else:
            seniority_levels.extend(['mid', 'intermediate'])
        
        # Apply seniority filter (simplified for PostgreSQL JSON compatibility)
        # Note: JSON contains operations are complex in PostgreSQL, so we'll skip this filter for now
        # and rely on other matching criteria
        
        return query
    
    def _apply_skill_filters(self, query, technical_skills: List[str]) -> Any:
        """Apply skill-based filters to query."""
        # Simplified skill filtering for PostgreSQL JSON compatibility
        # For now, we'll skip skill-based filtering and rely on other criteria
        # This can be enhanced later with proper JSON operators
        
        return query
    
    def _apply_difficulty_filters(self, query, complexity_score: float) -> Any:
        """Apply difficulty-based filters to query."""
        # Map complexity score to difficulty levels
        if complexity_score >= 2.5:
            difficulty_levels = ['hard', 'medium']
        elif complexity_score >= 1.5:
            difficulty_levels = ['medium', 'easy']
        else:
            difficulty_levels = ['easy', 'medium']
        
        return query.filter(QuestionTemplate.difficulty_level.in_(difficulty_levels))
    
    def _score_question_match(self, question: QuestionTemplate, request: QuestionMatchRequest, 
                            job_analysis: Dict[str, Any]) -> MatchResult:
        """Score how well a question matches the request."""
        scores = {}
        matched_criteria = {}
        
        # Role matching score
        role_score = self._calculate_role_match_score(question, request.role)
        scores['role_match'] = role_score
        if role_score > 0.5:
            matched_criteria['role'] = f"Matched {request.role}"
        
        # Skill matching score
        skill_score = self._calculate_skill_match_score(question, job_analysis['technical_skills'])
        scores['skill_match'] = skill_score
        if skill_score > 0.3:
            matched_criteria['skills'] = f"Matched {len(job_analysis['technical_skills'])} skills"
        
        # Difficulty matching score
        difficulty_score = self._calculate_difficulty_match_score(question, request.complexity_score)
        scores['difficulty_match'] = difficulty_score
        if difficulty_score > 0.7:
            matched_criteria['difficulty'] = f"Appropriate for complexity {request.complexity_score:.1f}"
        
        # Domain matching score
        domain_score = self._calculate_domain_match_score(question, job_analysis)
        scores['domain_match'] = domain_score
        if domain_score > 0.5:
            matched_criteria['domain'] = "Domain alignment"
        
        # Industry matching score
        industry_score = self._calculate_industry_match_score(question, job_analysis['company_info'])
        scores['industry_match'] = industry_score
        if industry_score > 0.5:
            matched_criteria['industry'] = "Industry relevance"
        
        # Calculate weighted total score
        total_score = sum(scores[criterion] * weight for criterion, weight in self.matching_weights.items())
        
        # Calculate confidence level
        confidence_level = min(total_score * 1.2, 1.0)  # Boost confidence slightly
        
        # Generate reasoning
        reasoning = self._generate_match_reasoning(scores, matched_criteria)
        
        return MatchResult(
            question_template=question,
            match_score=total_score,
            confidence_level=confidence_level,
            matched_criteria=matched_criteria,
            reasoning=reasoning
        )
    
    def _calculate_role_match_score(self, question: QuestionTemplate, role: str) -> float:
        """Calculate role matching score."""
        if not question.target_roles:
            return 0.5  # Neutral score if no specific roles
        
        role_lower = role.lower()
        for target_role in question.target_roles:
            if target_role.lower() in role_lower or role_lower in target_role.lower():
                return 1.0
        
        return 0.0
    
    def _calculate_skill_match_score(self, question: QuestionTemplate, required_skills: List[str]) -> float:
        """Calculate skill matching score."""
        if not question.required_skills or not required_skills:
            return 0.5  # Neutral score
        
        matched_skills = 0
        for skill in required_skills:
            if any(q_skill.lower() == skill.lower() for q_skill in question.required_skills):
                matched_skills += 1
        
        return min(matched_skills / len(required_skills), 1.0)
    
    def _calculate_difficulty_match_score(self, question: QuestionTemplate, complexity_score: float) -> float:
        """Calculate difficulty matching score."""
        difficulty_mapping = {
            'easy': 1.0,
            'medium': 2.0,
            'hard': 3.0
        }
        
        question_difficulty = difficulty_mapping.get(question.difficulty_level, 2.0)
        score_diff = abs(complexity_score - question_difficulty)
        
        # Score decreases as difference increases
        return max(1.0 - (score_diff / 2.0), 0.0)
    
    def _calculate_domain_match_score(self, question: QuestionTemplate, job_analysis: Dict[str, Any]) -> float:
        """Calculate domain matching score."""
        if not question.technical_domains:
            return 0.5  # Neutral score
        
        # Simple domain matching based on skills
        technical_skills = job_analysis.get('technical_skills', [])
        domain_keywords = {
            'backend': ['python', 'java', 'node.js', 'api', 'database'],
            'frontend': ['react', 'angular', 'vue', 'javascript', 'css'],
            'devops': ['aws', 'docker', 'kubernetes', 'ci/cd', 'infrastructure'],
            'data': ['python', 'sql', 'analytics', 'machine learning', 'data science']
        }
        
        matched_domains = 0
        for domain in question.technical_domains:
            domain_keywords_list = domain_keywords.get(domain, [])
            if any(skill in domain_keywords_list for skill in technical_skills):
                matched_domains += 1
        
        return min(matched_domains / len(question.technical_domains), 1.0)
    
    def _calculate_industry_match_score(self, question: QuestionTemplate, company_info: Dict[str, Any]) -> float:
        """Calculate industry matching score."""
        if not question.industries or not company_info:
            return 0.5  # Neutral score
        
        # Simple industry matching (could be enhanced with more sophisticated logic)
        return 0.7  # Default good score for now
    
    def _generate_match_reasoning(self, scores: Dict[str, float], matched_criteria: Dict[str, str]) -> str:
        """Generate human-readable reasoning for the match."""
        reasoning_parts = []
        
        if scores['role_match'] > 0.7:
            reasoning_parts.append("Strong role alignment")
        if scores['skill_match'] > 0.5:
            reasoning_parts.append("Relevant technical skills")
        if scores['difficulty_match'] > 0.7:
            reasoning_parts.append("Appropriate difficulty level")
        if scores['domain_match'] > 0.5:
            reasoning_parts.append("Domain expertise match")
        
        if not reasoning_parts:
            reasoning_parts.append("General relevance")
        
        return "; ".join(reasoning_parts)
    
    def _get_questions_from_match(self, match: QuestionMatch) -> List[MatchResult]:
        """Get questions from existing high-confidence match."""
        question = self.db_session.query(QuestionTemplate).filter(
            QuestionTemplate.id == match.question_template_id
        ).first()
        
        if question:
            return [MatchResult(
                question_template=question,
                match_score=match.match_score,
                confidence_level=match.confidence_level,
                matched_criteria=match.matched_criteria or {},
                reasoning="High-confidence cached match"
            )]
        
        return []
    
    def _store_match_results(self, request_hash: str, matches: List[MatchResult], job_analysis: Dict[str, Any]):
        """Store successful match results for future use."""
        try:
            for match in matches:
                question_match = QuestionMatch(
                    question_template_id=match.question_template.id,
                    user_request_hash=request_hash,
                    role=job_analysis.get('role', ''),
                    job_description_hash=hashlib.sha256(
                        job_analysis.get('job_description', '').encode()
                    ).hexdigest(),
                    complexity_score=job_analysis.get('complexity_score', 0.0),
                    matched_criteria=match.matched_criteria,
                    match_score=match.match_score,
                    confidence_level=match.confidence_level
                )
                self.db_session.add(question_match)
            
            self.db_session.commit()
            logger.info(f"Stored {len(matches)} question matches")
            
        except Exception as e:
            logger.error(f"Error storing match results: {e}")
            self.db_session.rollback()
