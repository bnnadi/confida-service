"""
Difficulty Rule Engine for data-driven difficulty determination.
Makes question bank rules more maintainable and extensible.
"""

from typing import Dict, Any, Optional, List, Callable
from abc import ABC, abstractmethod
from app.utils.logger import get_logger

logger = get_logger(__name__)

class DifficultyRule(ABC):
    """Abstract base class for difficulty rules."""
    
    def __init__(self, name: str):
        self.name = name
    
    @abstractmethod
    def apply(self, question_text: str, role_analysis: Dict[str, Any]) -> Optional[str]:
        """Apply the rule and return difficulty level if matched."""
        pass

class SeniorityRule(DifficultyRule):
    """Rule for determining difficulty based on seniority level."""
    
    def __init__(self):
        super().__init__("seniority")
        self.seniority_mapping = {
            'senior': 'hard',
            'junior': 'easy', 
            'mid': 'medium',
            'leadership': 'hard'
        }
    
    def apply(self, question_text: str, role_analysis: Dict[str, Any]) -> Optional[str]:
        seniority = role_analysis.get('seniority_level', 'mid')
        return self.seniority_mapping.get(seniority)

class KeywordRule(DifficultyRule):
    """Rule for determining difficulty based on keywords."""
    
    def __init__(self):
        super().__init__("keywords")
        self.keyword_rules = {
            'hard': ['complex', 'advanced', 'architecture', 'design', 'optimize', 'scalability', 'performance'],
            'easy': ['basic', 'simple', 'explain', 'what is', 'define', 'describe'],
            'medium': ['implement', 'create', 'build', 'develop', 'manage']
        }
    
    def apply(self, question_text: str, role_analysis: Dict[str, Any]) -> Optional[str]:
        text_lower = question_text.lower()
        for difficulty, keywords in self.keyword_rules.items():
            if any(keyword in text_lower for keyword in keywords):
                return difficulty
        return None

class LengthRule(DifficultyRule):
    """Rule for determining difficulty based on question length."""
    
    def __init__(self):
        super().__init__("length")
        self.length_thresholds = {
            'easy': 50,    # Short questions are easier
            'hard': 150    # Long questions are harder
        }
    
    def apply(self, question_text: str, role_analysis: Dict[str, Any]) -> Optional[str]:
        text_length = len(question_text)
        if text_length <= self.length_thresholds['easy']:
            return 'easy'
        elif text_length >= self.length_thresholds['hard']:
            return 'hard'
        return None

class DifficultyRuleEngine:
    """Data-driven rule engine for difficulty determination using strategy pattern."""
    
    def __init__(self):
        # Use strategy pattern for different rule types
        self.rules = [
            SeniorityRule(),
            KeywordRule(),
            LengthRule()
        ]
    
    def determine_difficulty(self, question_text: str, role_analysis: Dict[str, Any]) -> str:
        """Determine difficulty using strategy pattern."""
        for rule in self.rules:
            try:
                if difficulty := rule.apply(question_text, role_analysis):
                    logger.debug(f"Difficulty determined by {rule.name} rule: {difficulty}")
                    return difficulty
            except Exception as e:
                logger.warning(f"Error in {rule.name} rule: {e}")
                continue
        
        logger.debug("No rules matched, defaulting to medium difficulty")
        return 'medium'
    
    def add_custom_rule(self, rule: DifficultyRule):
        """Add a custom rule to the engine."""
        self.rules.append(rule)
        logger.info(f"Added custom rule: {rule.name}")
    
    def get_rule_explanation(self, question_text: str, role_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Get explanation of which rules applied."""
        explanation = {
            'question_text': question_text,
            'role_analysis': role_analysis,
            'applied_rules': [],
            'final_difficulty': None
        }
        
        for rule in self.rules:
            try:
                result = rule.apply(question_text, role_analysis)
                if result:
                    explanation['applied_rules'].append({
                        'rule': rule.name,
                        'result': result
                    })
                    if not explanation['final_difficulty']:
                        explanation['final_difficulty'] = result
            except Exception as e:
                explanation['applied_rules'].append({
                    'rule': rule.name,
                    'error': str(e)
                })
        
        if not explanation['final_difficulty']:
            explanation['final_difficulty'] = 'medium'
        
        return explanation

class CategoryRuleEngine:
    """Rule engine for question categorization."""
    
    def __init__(self):
        self.categorization_rules = {
            "technical": [
                'code', 'programming', 'algorithm', 'data structure', 'database', 'api',
                'framework', 'library', 'debug', 'test', 'deploy', 'git', 'docker'
            ],
            "behavioral": [
                'experience', 'challenge', 'conflict', 'team', 'leadership', 'decision',
                'mistake', 'learn', 'improve', 'situation', 'example', 'story'
            ],
            "system_design": [
                'design', 'architecture', 'scalability', 'performance', 'distributed',
                'microservice', 'load balancer', 'cache', 'database design', 'system'
            ],
            "leadership": [
                'manage', 'lead', 'team', 'mentor', 'strategy', 'vision', 'decision',
                'conflict resolution', 'performance review', 'hiring'
            ],
            "problem_solving": [
                'solve', 'problem', 'debug', 'troubleshoot', 'fix', 'issue', 'error',
                'optimize', 'improve', 'analyze'
            ]
        }
    
    def categorize_question(self, question_text: str) -> str:
        """Categorize question based on content analysis."""
        text_lower = question_text.lower()
        
        # Count matches for each category
        category_scores = {}
        for category, keywords in self.categorization_rules.items():
            score = sum(1 for keyword in keywords if keyword in text_lower)
            if score > 0:
                category_scores[category] = score
        
        if not category_scores:
            return 'general'
        
        # Return category with highest score
        return max(category_scores, key=category_scores.get)
    
    def get_category_confidence(self, question_text: str) -> Dict[str, float]:
        """Get confidence scores for all categories."""
        text_lower = question_text.lower()
        total_keywords = sum(len(keywords) for keywords in self.categorization_rules.values())
        
        confidence_scores = {}
        for category, keywords in self.categorization_rules.items():
            matches = sum(1 for keyword in keywords if keyword in text_lower)
            confidence_scores[category] = matches / len(keywords)
        
        return confidence_scores
