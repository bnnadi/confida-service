"""
Smart Token Optimizer Service

This service provides intelligent token optimization for AI service calls,
reducing costs while maintaining question quality through dynamic token
calculation based on request complexity.
"""
import re
import yaml
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from app.utils.logger import get_logger
from app.config import get_settings

logger = get_logger(__name__)

@dataclass
class TokenOptimizationResult:
    """Result of token optimization analysis."""
    optimal_tokens: int
    complexity_score: float
    estimated_cost: float
    optimization_applied: str
    confidence_score: float

class SmartTokenOptimizer:
    """
    Intelligent token optimizer that calculates optimal token counts
    based on request complexity and service characteristics.
    """
    
    def __init__(self, config_path: Optional[str] = None):
        self.settings = get_settings()
        self.config = self._load_config(config_path)
        
        # Load configuration sections
        self.service_configs = self.config['services']
        self.role_complexity_map = self.config['role_complexity']
        self.technical_keywords = self.config['technical_keywords']
        self.industry_complexity = self.config['industry_complexity']
        self.complexity_weights = self.config['complexity_weights']
        self.constraints = self.config['constraints']
    
    def _load_config(self, config_path: Optional[str] = None) -> Dict[str, Any]:
        """Load configuration from YAML file with fallback to defaults."""
        if config_path and Path(config_path).exists():
            try:
                with open(config_path, 'r') as f:
                    config = yaml.safe_load(f)
                    logger.info(f"Loaded token optimization config from {config_path}")
                    self._config_loaded_from_file = True
                    return config
            except Exception as e:
                logger.warning(f"Failed to load config from {config_path}: {e}")
        
        # Try default config path
        default_path = Path(__file__).parent.parent.parent / "config" / "token_optimization.yaml"
        if default_path.exists():
            try:
                with open(default_path, 'r') as f:
                    config = yaml.safe_load(f)
                    logger.info(f"Loaded token optimization config from {default_path}")
                    self._config_loaded_from_file = True
                    return config
            except Exception as e:
                logger.warning(f"Failed to load default config: {e}")
        
        # Fallback to hardcoded defaults
        logger.warning("Using hardcoded default configuration")
        return self._get_default_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration as fallback."""
        return {
            'services': {
                "ollama": {
                    "base_tokens": 200,
                    "max_tokens": 2000,
                    "cost_per_1k_tokens": 0.0,
                    "quality_factor": 0.8
                },
                "openai": {
                    "base_tokens": 300,
                    "max_tokens": 1500,
                    "cost_per_1k_tokens": 0.01,
                    "quality_factor": 1.0
                },
                "anthropic": {
                    "base_tokens": 400,
                    "max_tokens": 1800,
                    "cost_per_1k_tokens": 0.015,
                    "quality_factor": 1.1
                }
            },
            'role_complexity': {
                "intern": 0.5,
                "junior": 1.0,
                "mid": 1.5,
                "senior": 2.0,
                "lead": 2.5,
                "principal": 3.0,
                "staff": 2.8,
                "architect": 3.2
            },
            'technical_keywords': [
                "machine learning", "artificial intelligence", "deep learning",
                "distributed systems", "microservices", "kubernetes", "docker",
                "cloud computing", "aws", "azure", "gcp", "scalability",
                "performance optimization", "system design", "architecture",
                "algorithms", "data structures", "database design", "nosql",
                "react", "angular", "vue", "node.js", "python", "java", "go",
                "devops", "ci/cd", "infrastructure", "security", "encryption"
            ],
            'industry_complexity': {
                "fintech": 1.3,
                "healthcare": 1.2,
                "e-commerce": 1.1,
                "gaming": 1.0,
                "education": 0.9,
                "nonprofit": 0.8
            },
            'complexity_weights': {
                'seniority': 0.4,
                'description_length': 0.2,
                'technical': 0.25,
                'industry': 0.1,
                'skills': 0.05
            },
            'constraints': {
                'min_complexity_score': 0.5,
                'max_complexity_score': 3.0,
                'max_skill_count': 20,
                'technical_keywords_divisor': 5,
                'description_length_divisor': 100,
                'skill_count_divisor': 10
            }
        }
    
    def optimize_request(self, role: str, job_description: str, service: str, 
                        target_questions: int = 10) -> TokenOptimizationResult:
        """
        Optimize token usage for a specific request.
        
        Args:
            role: Job role/title
            job_description: Job description text
            service: AI service to use (ollama, openai, anthropic)
            target_questions: Number of questions to generate
            
        Returns:
            TokenOptimizationResult with optimization details
        """
        try:
            # Analyze request complexity
            complexity_analysis = self._analyze_complexity(role, job_description)
            
            # Calculate optimal tokens
            optimal_tokens = self._calculate_optimal_tokens(
                complexity_analysis, service, target_questions
            )
            
            # Estimate cost
            estimated_cost = self._estimate_cost(optimal_tokens, service)
            
            # Calculate confidence score
            confidence_score = self._calculate_confidence_score(complexity_analysis)
            
            # Determine optimization applied
            optimization_applied = self._get_optimization_description(
                complexity_analysis, optimal_tokens, service
            )
            
            result = TokenOptimizationResult(
                optimal_tokens=optimal_tokens,
                complexity_score=complexity_analysis['total_score'],
                estimated_cost=estimated_cost,
                optimization_applied=optimization_applied,
                confidence_score=confidence_score
            )
            
            logger.info(f"Token optimization: {role} -> {optimal_tokens} tokens, "
                       f"complexity: {complexity_analysis['total_score']:.2f}, "
                       f"cost: ${estimated_cost:.4f}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error in token optimization: {e}")
            # Return safe defaults
            return TokenOptimizationResult(
                optimal_tokens=500,
                complexity_score=1.0,
                estimated_cost=0.005,
                optimization_applied="fallback_default",
                confidence_score=0.5
            )
    
    def _analyze_complexity(self, role: str, job_description: str) -> Dict[str, Any]:
        """Analyze the complexity of a request."""
        # Extract seniority from role
        seniority_score = self._extract_seniority_score(role)
        
        # Analyze job description
        description_length = len(job_description.split())
        technical_complexity = self._analyze_technical_complexity(job_description)
        industry_complexity = self._analyze_industry_complexity(job_description)
        skill_requirements = self._extract_skill_count(job_description)
        
        # Calculate total complexity score using configuration weights
        weights = self.complexity_weights
        constraints = self.constraints
        
        total_score = (
            seniority_score * weights['seniority'] +
            (description_length / constraints['description_length_divisor']) * weights['description_length'] +
            technical_complexity * weights['technical'] +
            industry_complexity * weights['industry'] +
            (skill_requirements / constraints['skill_count_divisor']) * weights['skills']
        )
        
        # Clamp between configured min and max
        total_score = min(max(total_score, constraints['min_complexity_score']), constraints['max_complexity_score'])
        
        return {
            'seniority_score': seniority_score,
            'description_length': description_length,
            'technical_complexity': technical_complexity,
            'industry_complexity': industry_complexity,
            'skill_count': skill_requirements,
            'total_score': total_score
        }
    
    def _extract_seniority_score(self, role: str) -> float:
        """Extract seniority level from role title."""
        role_lower = role.lower()
        
        # Check for exact matches first
        for level, score in self.role_complexity_map.items():
            if level in role_lower:
                return score
        
        # Check for partial matches
        if any(word in role_lower for word in ["senior", "sr", "lead", "principal", "staff"]):
            return 2.5
        elif any(word in role_lower for word in ["junior", "jr", "entry", "associate"]):
            return 1.0
        elif any(word in role_lower for word in ["intern", "trainee", "apprentice"]):
            return 0.5
        else:
            return 1.5  # Default to mid-level
    
    def _analyze_technical_complexity(self, job_description: str) -> float:
        """Analyze technical complexity of job description."""
        description_lower = job_description.lower()
        
        # Count technical keywords
        technical_count = sum(1 for keyword in self.technical_keywords 
                             if keyword in description_lower)
        
        # Normalize to 0-2 scale using configuration
        return min(technical_count / self.constraints['technical_keywords_divisor'], 2.0)
    
    def _analyze_industry_complexity(self, job_description: str) -> float:
        """Analyze industry complexity."""
        description_lower = job_description.lower()
        
        for industry, factor in self.industry_complexity.items():
            if industry in description_lower:
                return factor
        
        return 1.0  # Default complexity
    
    def _extract_skill_count(self, job_description: str) -> int:
        """Extract number of required skills from job description."""
        # Look for skill lists (bullet points, numbered lists, etc.)
        skill_patterns = [
            r'•\s*([^•\n]+)',  # Bullet points
            r'\d+\.\s*([^\d\n]+)',  # Numbered lists
            r'required[:\s]+([^.\n]+)',  # Required skills
            r'must have[:\s]+([^.\n]+)',  # Must have skills
        ]
        
        skills_found = 0
        for pattern in skill_patterns:
            matches = re.findall(pattern, job_description, re.IGNORECASE)
            skills_found += len(matches)
        
        return min(skills_found, self.constraints['max_skill_count'])
    
    def _calculate_optimal_tokens(self, complexity_analysis: Dict[str, Any], 
                                 service: str, target_questions: int) -> int:
        """Calculate optimal token count based on complexity and service."""
        service_config = self.service_configs.get(service, self.service_configs["openai"])
        
        # Base calculation
        base_tokens = service_config["base_tokens"]
        complexity_score = complexity_analysis["total_score"]
        
        # Adjust for target questions (more questions = more tokens needed)
        question_factor = min(target_questions / 10, 1.5)  # Cap at 1.5x for 15+ questions
        
        # Calculate optimal tokens
        optimal_tokens = int(
            base_tokens * complexity_score * question_factor * service_config["quality_factor"]
        )
        
        # Apply service limits
        optimal_tokens = min(max(optimal_tokens, base_tokens), service_config["max_tokens"])
        
        return optimal_tokens
    
    def _estimate_cost(self, tokens: int, service: str) -> float:
        """Estimate cost for token usage."""
        service_config = self.service_configs.get(service, self.service_configs["openai"])
        return (tokens / 1000) * service_config["cost_per_1k_tokens"]
    
    def _calculate_confidence_score(self, complexity_analysis: Dict[str, Any]) -> float:
        """Calculate confidence score for the optimization."""
        # Higher confidence for more detailed analysis
        confidence_factors = [
            complexity_analysis["description_length"] > 50,  # Detailed description
            complexity_analysis["technical_complexity"] > 0,  # Technical content
            complexity_analysis["skill_count"] > 0,  # Skills mentioned
        ]
        
        confidence = sum(confidence_factors) / len(confidence_factors)
        return min(confidence, 1.0)
    
    def _get_optimization_description(self, complexity_analysis: Dict[str, Any], 
                                    optimal_tokens: int, service: str) -> str:
        """Generate human-readable optimization description."""
        complexity_score = complexity_analysis["total_score"]
        
        if complexity_score < 1.0:
            return f"Low complexity optimization ({service}): {optimal_tokens} tokens"
        elif complexity_score < 2.0:
            return f"Medium complexity optimization ({service}): {optimal_tokens} tokens"
        else:
            return f"High complexity optimization ({service}): {optimal_tokens} tokens"
    
    def get_optimization_stats(self) -> Dict[str, Any]:
        """Get optimization statistics and configuration."""
        return {
            "service_configs": self.service_configs,
            "role_complexity_map": self.role_complexity_map,
            "technical_keywords_count": len(self.technical_keywords),
            "industry_complexity_factors": self.industry_complexity,
            "complexity_weights": self.complexity_weights,
            "constraints": self.constraints,
            "config_source": "yaml_file" if hasattr(self, '_config_loaded_from_file') else "defaults"
        }
