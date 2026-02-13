"""
Unit tests for Prometheus metrics collection.
"""
import pytest
from app.utils.metrics import metrics, get_metrics_output


class TestMetricsCollector:
    """Test cases for MetricsCollector (global instance)."""

    @pytest.mark.unit
    def test_record_request(self):
        """Test recording API request metrics."""
        metrics.record_request("GET", "/health", 200, 0.05)
        metrics.record_request("POST", "/analyze", 201, 1.2)
        assert metrics.request_count is not None

    @pytest.mark.unit
    def test_record_error(self):
        """Test recording error metrics."""
        metrics.record_error("client_error", "/api/v1/questions")
        assert metrics.error_count is not None

    @pytest.mark.unit
    def test_record_cache_request_and_summary(self):
        """Test recording cache metrics and get_metrics_summary."""
        metrics.record_cache_request("get", "hit", 0.001)
        metrics.record_cache_request("get", "miss", 0.002)
        summary = metrics.get_metrics_summary()
        assert "cache_requests" in summary
        assert "hit_rate" in summary["cache_requests"]

    @pytest.mark.unit
    def test_get_metrics_output(self):
        """Test get_metrics_output returns string."""
        output = get_metrics_output()
        assert isinstance(output, str)
        assert len(output) > 0
