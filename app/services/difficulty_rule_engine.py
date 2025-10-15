"""
Difficulty Rule Engine for data-driven difficulty determination.
Makes question bank rules more maintainable and extensible.
"""

from typing import Dict, Any, Optional, List, Callable
from app.utils.logger import get_logger

logger = get_logger(__name__)

class DifficultyRuleEngine:
    """Data-driven rule engine for difficulty determination."""
    
    def __init__(self):
        self.rules = {
            'seniority': self._apply_seniority_rule,
            'keywords': self._apply_keyword_rule,
            'length': self._apply_length_rule,
            'complexity': self._apply_complexity_rule
        }
        
        # Rule configurations
        self.seniority_mapping = {
            'senior': 'hard',
            'junior': 'easy', 
            'mid': 'medium',
            'leadership': 'hard'
        }
        
        self.keyword_rules = {
            'hard': ['complex', 'advanced', 'architecture', 'design', 'optimize', 'scalability', 'performance'],
            'easy': ['basic', 'simple', 'explain', 'what is', 'define', 'describe'],
            'medium': ['implement', 'create', 'build', 'develop', 'manage']
        }
        
        self.length_thresholds = {
            'easy': 50,    # Short questions are easier
            'hard': 150    # Long questions are harder
        }
        
        self.complexity_indicators = {
            'hard': ['algorithm', 'data structure', 'system design', 'distributed', 'concurrent'],
            'easy': ['variable', 'function', 'loop', 'condition', 'array']
        }
    
    def determine_difficulty(self, question_text: str, role_analysis: Dict[str, Any]) -> str:
        """Determine difficulty using unified rule processing."""
        for rule_name, rule_config in self.rule_configs.items():
            try:
                if difficulty := self._apply_rule(rule_name, rule_config, question_text, role_analysis):
                    logger.debug(f"Difficulty determined by {rule_name} rule: {difficulty}")
                    return difficulty
            except Exception as e:
                logger.warning(f"Error in {rule_name} rule: {e}")
                continue
        
        logger.debug("No rules matched, defaulting to medium difficulty")
        return 'medium'
    
    def _apply_rule(self, rule_name: str, rule_config: Dict[str, Any], question_text: str, role_analysis: Dict[str, Any]) -> Optional[str]:
        """Apply a rule using unified pattern-based logic."""
        rule_type = rule_config['type']
        source_field = rule_config['source_field']
        
        # Get source data based on field
        if source_field == 'question_text':
            source_data = question_text.lower()
        elif source_field == 'seniority_level':
            source_data = role_analysis.get('seniority_level', 'mid')
        else:
            return None
        
        # Apply rule based on type
        if rule_type == 'mapping':
            return rule_config['data'].get(source_data)
        elif rule_type == 'keyword_match':
            for difficulty, keywords in rule_config['data'].items():
                if any(keyword in source_data for keyword in keywords):
                    return difficulty
        elif rule_type == 'threshold':
            if source_field == 'question_text':
                text_length = len(question_text)
                if text_length <= rule_config['data']['easy']:
                    return 'easy'
                elif text_length >= rule_config['data']['hard']:
                    return 'hard'
        
        return None
    
    
    def add_custom_rule(self, rule_name: str, rule_func: Callable, priority: int = 0):
        """Add a custom rule to the engine."""
        self.rules[rule_name] = rule_func
        logger.info(f"Added custom rule: {rule_name}")
    
    def get_rule_explanation(self, question_text: str, role_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Get explanation of which rules applied."""
        explanation = {
            'question_text': question_text,
            'role_analysis': role_analysis,
            'applied_rules': [],
            'final_difficulty': None
        }
        
        for rule_name, rule_func in self.rules.items():
            try:
                result = rule_func(question_text, role_analysis)
                if result:
                    explanation['applied_rules'].append({
                        'rule': rule_name,
                        'result': result
                    })
                    if not explanation['final_difficulty']:
                        explanation['final_difficulty'] = result
            except Exception as e:
                explanation['applied_rules'].append({
                    'rule': rule_name,
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
