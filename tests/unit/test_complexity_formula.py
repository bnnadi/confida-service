"""
Unit tests for Complexity Formula Calculator.

Tests the formula-based complexity scoring used for request complexity calculation.
"""
import pytest
from unittest.mock import patch
from app.utils.complexity_formula import (
    ComplexityFormula,
    ComplexityData,
    ComplexityWeights,
    ComplexityConstraints,
)


class TestComplexityFormula:
    """Test cases for ComplexityFormula."""

    @pytest.mark.unit
    def test_calculate_returns_clamped_score(self):
        """Verify score is between min (0.5) and max (3.0)."""
        weights = ComplexityWeights()
        constraints = ComplexityConstraints()
        formula = ComplexityFormula(weights, constraints)

        # Low values should clamp to 0.5
        low_data = ComplexityData(
            seniority_score=0,
            description_length=0,
            technical_complexity=0,
            industry_complexity=0,
            skill_count=0,
        )
        assert formula.calculate(low_data) == 0.5

        # High values should clamp to 3.0
        high_data = ComplexityData(
            seniority_score=10,
            description_length=1000,
            technical_complexity=10,
            industry_complexity=10,
            skill_count=20,
        )
        assert formula.calculate(high_data) == 3.0

    @pytest.mark.unit
    def test_calculate_with_default_weights(self):
        """Use ComplexityData with known values, assert formula result."""
        weights = ComplexityWeights()
        constraints = ComplexityConstraints()
        formula = ComplexityFormula(weights, constraints)

        data = ComplexityData(
            seniority_score=1.0,
            description_length=100,
            technical_complexity=1.0,
            industry_complexity=1.0,
            skill_count=5,
        )
        result = formula.calculate(data)

        # seniority: 1.0 * 0.4 = 0.4
        # description_length: (100/100) * 0.2 = 0.2
        # technical: 1.0 * 0.25 = 0.25
        # industry: 1.0 * 0.1 = 0.1
        # skills: (5/10) * 0.05 = 0.025
        # total = 0.975, clamped to [0.5, 3.0]
        assert 0.5 <= result <= 3.0
        assert abs(result - 0.975) < 0.01

    @pytest.mark.unit
    def test_calculate_components_breakdown(self):
        """Call get_component_breakdown(), assert structure has expected keys."""
        weights = ComplexityWeights()
        constraints = ComplexityConstraints()
        formula = ComplexityFormula(weights, constraints)

        data = ComplexityData(
            seniority_score=1.0,
            description_length=200,
            technical_complexity=0.5,
            industry_complexity=0.5,
            skill_count=10,
        )
        breakdown = formula.get_component_breakdown(data)

        assert "raw_components" in breakdown
        assert "raw_total" in breakdown
        assert "final_score" in breakdown
        assert "weights_applied" in breakdown
        assert "constraints" in breakdown
        assert breakdown["weights_applied"]["seniority"] == 0.4
        assert breakdown["constraints"]["min"] == 0.5
        assert breakdown["constraints"]["max"] == 3.0

    @pytest.mark.unit
    def test_calculate_exception_returns_min_score(self):
        """Pass invalid data via mock to trigger exception path, assert returns min_complexity_score."""
        weights = ComplexityWeights()
        constraints = ComplexityConstraints(min_complexity_score=0.5)
        formula = ComplexityFormula(weights, constraints)

        data = ComplexityData(
            seniority_score=1.0,
            description_length=100,
            technical_complexity=1.0,
            industry_complexity=1.0,
            skill_count=5,
        )

        with patch.object(formula, "_calculate_components", side_effect=ValueError("Invalid")):
            result = formula.calculate(data)

        assert result == 0.5

    @pytest.mark.unit
    def test_custom_weights_and_constraints(self):
        """Instantiate with custom weights and constraints, verify calculation respects them."""
        weights = ComplexityWeights(seniority=0.5, description_length=0.5)
        constraints = ComplexityConstraints(
            min_complexity_score=0.0,
            max_complexity_score=5.0,
            description_length_divisor=50,
        )
        formula = ComplexityFormula(weights, constraints)

        data = ComplexityData(
            seniority_score=2.0,
            description_length=100,
            technical_complexity=0,
            industry_complexity=0,
            skill_count=0,
        )
        result = formula.calculate(data)

        # seniority: 2.0 * 0.5 = 1.0
        # description_length: (100/50) * 0.5 = 1.0
        # total = 2.0
        assert result == 2.0
        assert 0.0 <= result <= 5.0
