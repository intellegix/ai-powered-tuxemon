"""
Unit Tests for AI Cost Tracking System
Austin Kidwell | Intellegix | AI-Powered Tuxemon Game

Tests budget monitoring, throttling logic, and cost analysis functionality
to ensure AI costs remain within acceptable limits.
"""

import pytest
import pytest_asyncio
from datetime import datetime, timedelta
from typing import Dict, Any
from unittest.mock import AsyncMock, MagicMock, patch

from app.ai.ai_manager import DailyCostTracker
from app.core.config import get_settings


class TestCostTracker:
    """Test suite for AI cost tracking and budget management."""

    @pytest_asyncio.fixture
    async def cost_tracker(self, test_redis):
        """Provide cost tracker with test Redis instance."""
        tracker = DailyCostTracker()
        # Mock get_redis to return test instance
        with patch('app.ai.ai_manager.get_redis', return_value=test_redis):
            yield tracker

    @pytest.mark.unit
    @pytest.mark.ai
    async def test_can_make_request_within_budget(
        self,
        cost_tracker: DailyCostTracker,
        test_redis
    ):
        """Test that requests are allowed when within daily budget."""
        # Setup: Set current daily cost below limit
        today = datetime.utcnow().date().isoformat()
        await test_redis.hset(cost_tracker.redis_key, today, "5.50")

        with patch('app.ai.ai_manager.get_redis', return_value=test_redis):
            with patch('app.core.config.get_settings') as mock_settings:
                mock_settings.return_value.max_cost_per_day_usd = 10.0

                # Execute
                can_make = await cost_tracker.can_make_request()

                # Verify
                assert can_make is True

    @pytest.mark.unit
    @pytest.mark.ai
    async def test_can_make_request_over_budget(
        self,
        cost_tracker: DailyCostTracker,
        test_redis
    ):
        """Test that requests are blocked when over daily budget."""
        # Setup: Set current daily cost above limit
        today = datetime.utcnow().date().isoformat()
        await test_redis.hset(cost_tracker.redis_key, today, "15.75")

        with patch('app.ai.ai_manager.get_redis', return_value=test_redis):
            with patch('app.core.config.get_settings') as mock_settings:
                mock_settings.return_value.max_cost_per_day_usd = 10.0

                # Execute
                can_make = await cost_tracker.can_make_request()

                # Verify
                assert can_make is False

    @pytest.mark.unit
    @pytest.mark.ai
    async def test_can_make_request_no_prior_usage(
        self,
        cost_tracker: DailyCostTracker,
        test_redis
    ):
        """Test that requests are allowed on first use of the day."""
        with patch('app.ai.ai_manager.get_redis', return_value=test_redis):
            # Execute (no prior cost data)
            can_make = await cost_tracker.can_make_request()

            # Verify
            assert can_make is True

    @pytest.mark.unit
    @pytest.mark.ai
    async def test_record_request_claude_api(
        self,
        cost_tracker: DailyCostTracker,
        test_redis
    ):
        """Test recording Claude API request with detailed metrics."""
        today = datetime.utcnow().date().isoformat()
        hour = datetime.utcnow().hour

        with patch('app.ai.ai_manager.get_redis', return_value=test_redis):
            # Execute
            await cost_tracker.record_request(
                estimated_cost=0.025,
                model_used="claude",
                tokens_used=150,
                response_time_ms=1500
            )

            # Verify cost tracking
            daily_cost = await test_redis.hget(cost_tracker.redis_key, today)
            assert float(daily_cost) == 0.025

            # Verify request counting
            daily_requests = await test_redis.get(f"{cost_tracker.request_count_key}:{today}")
            assert int(daily_requests) == 1

            hourly_requests = await test_redis.get(f"{cost_tracker.request_count_key}:{today}:{hour:02d}")
            assert int(hourly_requests) == 1

            # Verify detailed stats
            stats_key = f"{cost_tracker.usage_stats_key}:{today}"
            stats = await test_redis.hgetall(stats_key)

            assert float(stats["total_cost"]) == 0.025
            assert int(stats["total_requests"]) == 1
            assert int(stats["requests_claude"]) == 1
            assert int(stats["total_tokens"]) == 150
            assert int(stats["total_response_time_ms"]) == 1500

    @pytest.mark.unit
    @pytest.mark.ai
    async def test_record_request_local_llm(
        self,
        cost_tracker: DailyCostTracker,
        test_redis
    ):
        """Test recording local LLM request with lower cost."""
        today = datetime.utcnow().date().isoformat()

        with patch('app.ai.ai_manager.get_redis', return_value=test_redis):
            # Execute
            await cost_tracker.record_request(
                estimated_cost=0.001,
                model_used="local",
                tokens_used=75,
                response_time_ms=500
            )

            # Verify cost tracking
            daily_cost = await test_redis.hget(cost_tracker.redis_key, today)
            assert float(daily_cost) == 0.001

            # Verify model-specific stats
            stats_key = f"{cost_tracker.usage_stats_key}:{today}"
            stats = await test_redis.hgetall(stats_key)

            assert int(stats["requests_local"]) == 1
            assert "requests_claude" not in stats  # Should not increment Claude counter

    @pytest.mark.unit
    @pytest.mark.ai
    async def test_record_multiple_requests_accumulation(
        self,
        cost_tracker: DailyCostTracker,
        test_redis
    ):
        """Test that multiple requests accumulate costs correctly."""
        today = datetime.utcnow().date().isoformat()

        with patch('app.ai.ai_manager.get_redis', return_value=test_redis):
            # Execute multiple requests
            await cost_tracker.record_request(estimated_cost=0.02, model_used="claude")
            await cost_tracker.record_request(estimated_cost=0.001, model_used="local")
            await cost_tracker.record_request(estimated_cost=0.025, model_used="claude")

            # Verify accumulated cost
            daily_cost = await test_redis.hget(cost_tracker.redis_key, today)
            assert float(daily_cost) == 0.046  # 0.02 + 0.001 + 0.025

            # Verify request counts
            daily_requests = await test_redis.get(f"{cost_tracker.request_count_key}:{today}")
            assert int(daily_requests) == 3

            # Verify model-specific counts
            stats_key = f"{cost_tracker.usage_stats_key}:{today}"
            stats = await test_redis.hgetall(stats_key)

            assert int(stats["requests_claude"]) == 2
            assert int(stats["requests_local"]) == 1

    @pytest.mark.unit
    @pytest.mark.ai
    async def test_get_daily_stats_comprehensive(
        self,
        cost_tracker: DailyCostTracker,
        test_redis
    ):
        """Test comprehensive daily statistics generation."""
        today = datetime.utcnow().date().isoformat()

        with patch('app.ai.ai_manager.get_redis', return_value=test_redis):
            with patch('app.core.config.get_settings') as mock_settings:
                mock_settings.return_value.max_cost_per_day_usd = 10.0

                # Setup test data
                await cost_tracker.record_request(estimated_cost=0.02, model_used="claude",
                                                 tokens_used=100, response_time_ms=1200)
                await cost_tracker.record_request(estimated_cost=0.001, model_used="local",
                                                 tokens_used=50, response_time_ms=400)
                await cost_tracker.record_request(estimated_cost=0.03, model_used="claude",
                                                 tokens_used=150, response_time_ms=1800)

                # Execute
                stats = await cost_tracker.get_daily_stats(today)

                # Verify comprehensive stats
                assert stats["date"] == today
                assert stats["total_cost"] == 0.051
                assert stats["total_requests"] == 3
                assert stats["avg_cost_per_request"] == pytest.approx(0.017, rel=1e-3)
                assert stats["budget_limit"] == 10.0
                assert stats["budget_remaining"] == pytest.approx(9.949, rel=1e-3)
                assert stats["budget_utilization"] == pytest.approx(0.51, rel=1e-2)

                # Verify model breakdown
                assert stats["requests_by_model"]["claude"] == 2
                assert stats["requests_by_model"]["local"] == 1

                # Verify performance metrics
                assert stats["total_tokens"] == 300
                assert stats["avg_response_time_ms"] == pytest.approx(1133.33, rel=1e-2)

    @pytest.mark.unit
    @pytest.mark.ai
    async def test_get_daily_stats_empty_day(
        self,
        cost_tracker: DailyCostTracker,
        test_redis
    ):
        """Test daily stats for day with no activity."""
        tomorrow = (datetime.utcnow() + timedelta(days=1)).date().isoformat()

        with patch('app.ai.ai_manager.get_redis', return_value=test_redis):
            with patch('app.core.config.get_settings') as mock_settings:
                mock_settings.return_value.max_cost_per_day_usd = 10.0

                # Execute
                stats = await cost_tracker.get_daily_stats(tomorrow)

                # Verify empty stats
                assert stats["date"] == tomorrow
                assert stats["total_cost"] == 0.0
                assert stats["total_requests"] == 0
                assert stats["budget_remaining"] == 10.0
                assert stats["budget_utilization"] == 0.0

    @pytest.mark.unit
    @pytest.mark.ai
    async def test_get_hourly_breakdown(
        self,
        cost_tracker: DailyCostTracker,
        test_redis
    ):
        """Test hourly request breakdown functionality."""
        today = datetime.utcnow().date().isoformat()

        with patch('app.ai.ai_manager.get_redis', return_value=test_redis):
            # Simulate requests at different hours
            current_hour = datetime.utcnow().hour

            # Add requests for current hour and previous hour
            await test_redis.incr(f"{cost_tracker.request_count_key}:{today}:{current_hour:02d}", 5)
            if current_hour > 0:
                prev_hour = current_hour - 1
                await test_redis.incr(f"{cost_tracker.request_count_key}:{today}:{prev_hour:02d}", 3)

            # Execute
            hourly_data = await cost_tracker.get_hourly_breakdown(today)

            # Verify
            assert len(hourly_data) == 24  # All 24 hours
            assert hourly_data[current_hour] == 5

            if current_hour > 0:
                assert hourly_data[current_hour - 1] == 3

            # Verify empty hours return 0
            for hour in range(24):
                if hour != current_hour and hour != current_hour - 1:
                    assert hourly_data[hour] == 0

    @pytest.mark.unit
    @pytest.mark.ai
    async def test_get_cost_projection_with_data(
        self,
        cost_tracker: DailyCostTracker,
        test_redis
    ):
        """Test cost projection calculation with historical data."""
        with patch('app.ai.ai_manager.get_redis', return_value=test_redis):
            with patch('app.core.config.get_settings') as mock_settings:
                mock_settings.return_value.max_cost_per_day_usd = 10.0

                # Setup historical data for last 7 days
                daily_costs = [2.5, 3.2, 1.8, 4.1, 2.9, 3.7, 2.3]
                for i, cost in enumerate(daily_costs):
                    date = (datetime.utcnow() - timedelta(days=i)).date().isoformat()
                    await test_redis.hset(cost_tracker.redis_key, date, str(cost))

                # Execute
                projection = await cost_tracker.get_cost_projection()

                # Verify
                expected_avg = sum(daily_costs) / len(daily_costs)
                expected_monthly = expected_avg * 30

                assert projection["daily_avg"] == pytest.approx(expected_avg, rel=1e-2)
                assert projection["monthly_projection"] == pytest.approx(expected_monthly, rel=1e-2)
                assert projection["weekly_total"] == pytest.approx(sum(daily_costs), rel=1e-2)
                assert projection["confidence"] == "high"  # 7 active days
                assert projection["data_points"] == 7

    @pytest.mark.unit
    @pytest.mark.ai
    async def test_get_cost_projection_insufficient_data(
        self,
        cost_tracker: DailyCostTracker,
        test_redis
    ):
        """Test cost projection with insufficient historical data."""
        with patch('app.ai.ai_manager.get_redis', return_value=test_redis):
            # Setup minimal data (only 2 days)
            today = datetime.utcnow().date().isoformat()
            yesterday = (datetime.utcnow() - timedelta(days=1)).date().isoformat()

            await test_redis.hset(cost_tracker.redis_key, today, "2.5")
            await test_redis.hset(cost_tracker.redis_key, yesterday, "3.2")

            # Execute
            projection = await cost_tracker.get_cost_projection()

            # Verify
            assert projection["confidence"] == "low"  # Only 2 data points
            assert projection["data_points"] == 2

    @pytest.mark.unit
    @pytest.mark.ai
    async def test_set_and_check_budget_alerts(
        self,
        cost_tracker: DailyCostTracker,
        test_redis
    ):
        """Test budget alert configuration and checking."""
        today = datetime.utcnow().date().isoformat()

        with patch('app.ai.ai_manager.get_redis', return_value=test_redis):
            with patch('app.core.config.get_settings') as mock_settings:
                mock_settings.return_value.max_cost_per_day_usd = 10.0

                # Setup alert threshold
                await cost_tracker.set_budget_alert(threshold_percent=80.0)

                # Verify threshold was set
                threshold = await test_redis.get("budget_alert_threshold")
                assert float(threshold) == 80.0

                # Test no alert when under threshold
                await test_redis.hset(cost_tracker.redis_key, today, "7.5")  # 75% utilization
                alert = await cost_tracker.check_budget_alerts()
                assert alert is None

                # Test alert when over threshold
                await test_redis.hset(cost_tracker.redis_key, today, "8.5")  # 85% utilization
                alert = await cost_tracker.check_budget_alerts()

                assert alert is not None
                assert alert["alert_type"] == "budget_threshold"
                assert alert["current_cost"] == 8.5
                assert alert["budget_limit"] == 10.0
                assert alert["utilization_percent"] == 85.0
                assert alert["threshold_percent"] == 80.0

    @pytest.mark.unit
    @pytest.mark.ai
    async def test_cost_tracking_error_handling(
        self,
        cost_tracker: DailyCostTracker,
        test_redis
    ):
        """Test graceful error handling in cost tracking."""
        # Test can_make_request with Redis error
        with patch('app.ai.ai_manager.get_redis', side_effect=Exception("Redis connection failed")):
            # Should default to allowing requests on error
            can_make = await cost_tracker.can_make_request()
            assert can_make is True

        # Test record_request with Redis error
        with patch('app.ai.ai_manager.get_redis', return_value=test_redis):
            with patch.object(test_redis, 'hincrbyfloat', side_effect=Exception("Redis write failed")):
                # Should not raise exception
                try:
                    await cost_tracker.record_request(estimated_cost=0.02)
                except Exception:
                    pytest.fail("record_request should handle Redis errors gracefully")

    @pytest.mark.unit
    @pytest.mark.ai
    async def test_redis_key_expiry_settings(
        self,
        cost_tracker: DailyCostTracker,
        test_redis
    ):
        """Test that Redis keys have appropriate expiry settings."""
        today = datetime.utcnow().date().isoformat()

        with patch('app.ai.ai_manager.get_redis', return_value=test_redis):
            # Mock expire calls to verify they're made
            with patch.object(test_redis, 'expire') as mock_expire:
                await cost_tracker.record_request(estimated_cost=0.02)

                # Verify expire calls were made for data retention
                expire_calls = [call.args for call in mock_expire.call_args_list]

                # Should have expire calls for cost tracking, request counting, and stats
                assert any(call[0] == cost_tracker.redis_key and call[1] == 86400 * 7 for call in expire_calls)
                assert any(call[0].startswith(cost_tracker.request_count_key) for call in expire_calls)
                assert any(call[0].startswith(cost_tracker.usage_stats_key) for call in expire_calls)

    @pytest.mark.unit
    @pytest.mark.ai
    @pytest.mark.slow
    async def test_high_volume_cost_tracking(
        self,
        cost_tracker: DailyCostTracker,
        test_redis
    ):
        """Test cost tracking performance under high request volume."""
        with patch('app.ai.ai_manager.get_redis', return_value=test_redis):
            import time

            # Record many requests quickly
            start_time = time.time()

            for i in range(100):
                await cost_tracker.record_request(
                    estimated_cost=0.01,
                    model_used="local" if i % 3 == 0 else "claude",
                    tokens_used=50 + i,
                    response_time_ms=500 + i * 10
                )

            end_time = time.time()
            total_time = (end_time - start_time) * 1000  # Convert to ms

            # Performance assertion
            assert total_time < 2000  # Should complete in under 2 seconds

            # Verify data integrity
            today = datetime.utcnow().date().isoformat()
            daily_cost = await test_redis.hget(cost_tracker.redis_key, today)
            daily_requests = await test_redis.get(f"{cost_tracker.request_count_key}:{today}")

            assert float(daily_cost) == 1.0  # 100 * 0.01
            assert int(daily_requests) == 100