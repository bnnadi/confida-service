"""
Complexity Formula Calculator

Provides a clean, formula-based approach to calculating request complexity
instead of manual weight calculations in SmartTokenOptimizer.
"""

from typing import Dict, Any
from dataclasses import dataclass
from app.utils.logger import get_logger

logger = get_logger(__name__)

@dataclass
class ComplexityData:
    """Data structure for complexity analysis inputs."""
    seniority_score: float
    description_length: int
    technical_complexity: float
    industry_complexity: float
    skill_count: int

@dataclass
class ComplexityWeights:
    """Configuration for complexity calculation weights."""
    seniority: float = 0.4
    description_length: float = 0.2
    technical: float = 0.25
    industry: float = 0.1
    skills: float = 0.05

@dataclass
class ComplexityConstraints:
    """Configuration for complexity calculation constraints."""
    min_complexity_score: float = 0.5
    max_complexity_score: float = 3.0
    max_skill_count: int = 20
    technical_keywords_divisor: int = 5
    description_length_divisor: int = 100
    skill_count_divisor: int = 10

class ComplexityFormula:
    """
    Formula-based complexity calculator that replaces manual weight calculations.
    Provides clean, testable, and maintainable complexity scoring.
    """
    
    def __init__(self, weights: ComplexityWeights, constraints: ComplexityConstraints):
        self.weights = weights
        self.constraints = constraints
    
    def calculate(self, data: ComplexityData) -> float:
        """
        Calculate complexity score using formula-based approach.
        
        Args:
            data: ComplexityData containing all analysis inputs
            
        Returns:
            Final complexity score clamped between min and max constraints
        """
        try:
            # Calculate weighted components
            components = self._calculate_components(data)
            
            # Apply formula
            total_score = self._apply_formula(components)
            
            # Apply constraints
            final_score = self._apply_constraints(total_score)
            
            logger.debug(f"Complexity calculation: {components} -> {final_score}")
            return final_score
            
        except Exception as e:
            logger.error(f"Error in complexity calculation: {e}")
            return self.constraints.min_complexity_score
    
    def _calculate_components(self, data: ComplexityData) -> Dict[str, float]:
        """Calculate individual weighted components."""
        return {
            'seniority': data.seniority_score * self.weights.seniority,
            'description_length': (data.description_length / self.constraints.description_length_divisor) * self.weights.description_length,
            'technical': data.technical_complexity * self.weights.technical,
            'industry': data.industry_complexity * self.weights.industry,
            'skills': (data.skill_count / self.constraints.skill_count_divisor) * self.weights.skills
        }
    
    def _apply_formula(self, components: Dict[str, float]) -> float:
        """Apply the complexity formula."""
        return sum(components.values())
    
    def _apply_constraints(self, score: float) -> float:
        """Apply min/max constraints to the score."""
        return min(max(score, self.constraints.min_complexity_score), self.constraints.max_complexity_score)
    
    def get_component_breakdown(self, data: ComplexityData) -> Dict[str, Any]:
        """Get detailed breakdown of complexity calculation for debugging."""
        components = self._calculate_components(data)
        total = self._apply_formula(components)
        final = self._apply_constraints(total)
        
        return {
            'raw_components': components,
            'raw_total': total,
            'final_score': final,
            'weights_applied': {
                'seniority': self.weights.seniority,
                'description_length': self.weights.description_length,
                'technical': self.weights.technical,
                'industry': self.weights.industry,
                'skills': self.weights.skills
            },
            'constraints': {
                'min': self.constraints.min_complexity_score,
                'max': self.constraints.max_complexity_score
            }
        }
