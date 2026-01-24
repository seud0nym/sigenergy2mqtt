import asyncio
import logging
from unittest.mock import MagicMock, patch

import pytest

from sigenergy2mqtt.metrics.metrics import Metrics


class TestMetricsLock:
    """Tests for Metrics.lock() context manager."""

    @pytest.fixture(autouse=True)
    def reset_metrics(self):
        """Reset Metrics state before each test."""
        # Store original state
        original_lock = Metrics._lock

        # Create fresh lock for each test
        Metrics._lock = asyncio.Lock()

        yield

        # Restore original lock
        Metrics._lock = original_lock

    @pytest.mark.asyncio
    async def test_lock_no_timeout_success(self):
        """Test acquiring lock without timeout."""
        acquired = False
        async with Metrics.lock(timeout=None):
            acquired = True
            assert Metrics._lock.locked()

        assert acquired
        assert not Metrics._lock.locked()

    @pytest.mark.asyncio
    async def test_lock_with_timeout_success(self):
        """Test acquiring lock with timeout."""
        acquired = False
        async with Metrics.lock(timeout=1.0):
            acquired = True
            assert Metrics._lock.locked()

        assert acquired
        assert not Metrics._lock.locked()

    @pytest.mark.asyncio
    async def test_lock_timeout_error(self):
        """Test timeout when lock cannot be acquired."""
        # Acquire the lock first
        await Metrics._lock.acquire()

        try:
            # This should timeout since lock is already held
            with pytest.raises(asyncio.TimeoutError):
                async with Metrics.lock(timeout=0.01):
                    pass
        finally:
            # Release the lock we acquired
            Metrics._lock.release()

    @pytest.mark.asyncio
    async def test_lock_proper_release(self):
        """Verify lock is released in finally block even if exception occurs."""
        with pytest.raises(ValueError):
            async with Metrics.lock(timeout=1.0):
                assert Metrics._lock.locked()
                raise ValueError("Test exception")

        # Lock should be released despite exception
        assert not Metrics._lock.locked()

    @pytest.mark.asyncio
    async def test_lock_not_acquired_no_release(self):
        """Verify no release when lock not acquired (timeout case)."""
        # Acquire the lock first
        await Metrics._lock.acquire()

        try:
            with pytest.raises(asyncio.TimeoutError):
                async with Metrics.lock(timeout=0.01):
                    pass

            # Lock should still be held by us, not released by context manager
            assert Metrics._lock.locked()
        finally:
            Metrics._lock.release()


class TestMetricsCacheHits:
    """Tests for Metrics.modbus_cache_hits()."""

    @pytest.fixture(autouse=True)
    def reset_metrics(self):
        """Reset Metrics state before each test."""
        original_percentage = Metrics.sigenergy2mqtt_modbus_cache_hit_percentage
        Metrics.sigenergy2mqtt_modbus_cache_hit_percentage = 0.0

        yield

        Metrics.sigenergy2mqtt_modbus_cache_hit_percentage = original_percentage

    @pytest.mark.asyncio
    async def test_modbus_cache_hits_success(self):
        """Test successful cache hit percentage calculation."""
        await Metrics.modbus_cache_hits(reads=100, hits=75)
        assert Metrics.sigenergy2mqtt_modbus_cache_hit_percentage == 75.0

    @pytest.mark.asyncio
    async def test_modbus_cache_hits_zero_reads(self):
        """Test handling of zero reads (ZeroDivisionError)."""
        with patch("logging.warning") as mock_warning:
            await Metrics.modbus_cache_hits(reads=0, hits=0)
            # Should log warning about exception
            assert mock_warning.called
            assert "ZeroDivisionError" in str(mock_warning.call_args)

    @pytest.mark.asyncio
    async def test_modbus_cache_hits_exception_handling(self):
        """Test exception handling with warning log."""
        with patch("logging.warning") as mock_warning:
            # Force an exception by passing invalid types
            await Metrics.modbus_cache_hits(reads=None, hits=75)
            assert mock_warning.called
            assert "modbus cache metrics collection" in mock_warning.call_args[0][0]


class TestMetricsRead:
    """Tests for Metrics.modbus_read()."""

    @pytest.fixture(autouse=True)
    def reset_metrics(self):
        """Reset Metrics state before each test."""
        original_reads = Metrics.sigenergy2mqtt_modbus_register_reads
        original_total = Metrics.sigenergy2mqtt_modbus_read_total
        original_max = Metrics.sigenergy2mqtt_modbus_read_max
        original_mean = Metrics.sigenergy2mqtt_modbus_read_mean
        original_min = Metrics.sigenergy2mqtt_modbus_read_min

        # Reset to initial state
        Metrics.sigenergy2mqtt_modbus_register_reads = 0
        Metrics.sigenergy2mqtt_modbus_read_total = 0.0
        Metrics.sigenergy2mqtt_modbus_read_max = 0.0
        Metrics.sigenergy2mqtt_modbus_read_mean = 0.0
        Metrics.sigenergy2mqtt_modbus_read_min = float("inf")

        yield

        # Restore original state
        Metrics.sigenergy2mqtt_modbus_register_reads = original_reads
        Metrics.sigenergy2mqtt_modbus_read_total = original_total
        Metrics.sigenergy2mqtt_modbus_read_max = original_max
        Metrics.sigenergy2mqtt_modbus_read_mean = original_mean
        Metrics.sigenergy2mqtt_modbus_read_min = original_min

    @pytest.mark.asyncio
    async def test_modbus_read_success(self):
        """Test successful read metrics collection."""
        await Metrics.modbus_read(registers=10, seconds=0.05)

        assert Metrics.sigenergy2mqtt_modbus_register_reads == 10
        assert Metrics.sigenergy2mqtt_modbus_read_total == 50.0  # 0.05 * 1000
        assert Metrics.sigenergy2mqtt_modbus_read_max == 50.0
        assert Metrics.sigenergy2mqtt_modbus_read_min == 50.0
        assert Metrics.sigenergy2mqtt_modbus_read_mean == 5.0  # 50 / 10

    @pytest.mark.asyncio
    async def test_modbus_read_updates_min_max(self):
        """Verify min/max tracking logic."""
        await Metrics.modbus_read(registers=5, seconds=0.1)  # 100ms
        await Metrics.modbus_read(registers=5, seconds=0.05)  # 50ms
        await Metrics.modbus_read(registers=5, seconds=0.15)  # 150ms

        assert Metrics.sigenergy2mqtt_modbus_read_max == 150.0
        assert Metrics.sigenergy2mqtt_modbus_read_min == 50.0
        assert Metrics.sigenergy2mqtt_modbus_register_reads == 15

    @pytest.mark.asyncio
    async def test_modbus_read_mean_calculation(self):
        """Verify mean calculation."""
        await Metrics.modbus_read(registers=10, seconds=0.1)  # 100ms
        await Metrics.modbus_read(registers=10, seconds=0.2)  # 200ms

        # Total = 300ms, reads = 20, mean = 15ms
        assert Metrics.sigenergy2mqtt_modbus_read_mean == 15.0

    @pytest.mark.asyncio
    async def test_modbus_read_exception_handling(self):
        """Test exception handling with warning log."""
        with patch("logging.warning") as mock_warning:
            # Force an exception
            await Metrics.modbus_read(registers=None, seconds=0.1)
            assert mock_warning.called
            assert "modbus read metrics collection" in mock_warning.call_args[0][0]


class TestMetricsReadError:
    """Tests for Metrics.modbus_read_error()."""

    @pytest.fixture(autouse=True)
    def reset_metrics(self):
        """Reset Metrics state before each test."""
        original_errors = Metrics.sigenergy2mqtt_modbus_read_errors
        Metrics.sigenergy2mqtt_modbus_read_errors = 0

        yield

        Metrics.sigenergy2mqtt_modbus_read_errors = original_errors

    @pytest.mark.asyncio
    async def test_modbus_read_error_success(self):
        """Test read error counter increment."""
        assert Metrics.sigenergy2mqtt_modbus_read_errors == 0

        await Metrics.modbus_read_error()
        assert Metrics.sigenergy2mqtt_modbus_read_errors == 1

        await Metrics.modbus_read_error()
        assert Metrics.sigenergy2mqtt_modbus_read_errors == 2

    @pytest.mark.asyncio
    async def test_modbus_read_error_exception_handling(self):
        """Test exception handling."""
        with patch.object(Metrics, "_lock") as mock_lock:
            mock_lock.acquire.side_effect = Exception("Test exception")

            with patch("logging.warning") as mock_warning:
                await Metrics.modbus_read_error()
                assert mock_warning.called
                assert "modbus read error metrics collection" in mock_warning.call_args[0][0]


class TestMetricsWrite:
    """Tests for Metrics.modbus_write()."""

    @pytest.fixture(autouse=True)
    def reset_metrics(self):
        """Reset Metrics state before each test."""
        original_writes = Metrics.sigenergy2mqtt_modbus_writes
        original_total = Metrics.sigenergy2mqtt_modbus_write_total
        original_max = Metrics.sigenergy2mqtt_modbus_write_max
        original_mean = Metrics.sigenergy2mqtt_modbus_write_mean
        original_min = Metrics.sigenergy2mqtt_modbus_write_min

        # Reset to initial state
        Metrics.sigenergy2mqtt_modbus_writes = 0
        Metrics.sigenergy2mqtt_modbus_write_total = 0.0
        Metrics.sigenergy2mqtt_modbus_write_max = 0.0
        Metrics.sigenergy2mqtt_modbus_write_mean = 0.0
        Metrics.sigenergy2mqtt_modbus_write_min = float("inf")

        yield

        # Restore original state
        Metrics.sigenergy2mqtt_modbus_writes = original_writes
        Metrics.sigenergy2mqtt_modbus_write_total = original_total
        Metrics.sigenergy2mqtt_modbus_write_max = original_max
        Metrics.sigenergy2mqtt_modbus_write_mean = original_mean
        Metrics.sigenergy2mqtt_modbus_write_min = original_min

    @pytest.mark.asyncio
    async def test_modbus_write_success(self):
        """Test successful write metrics collection."""
        await Metrics.modbus_write(registers=5, seconds=0.03)

        assert Metrics.sigenergy2mqtt_modbus_writes == 5
        assert Metrics.sigenergy2mqtt_modbus_write_total == 30.0  # 0.03 * 1000
        assert Metrics.sigenergy2mqtt_modbus_write_max == 30.0
        assert Metrics.sigenergy2mqtt_modbus_write_min == 30.0
        assert Metrics.sigenergy2mqtt_modbus_write_mean == 6.0  # 30 / 5

    @pytest.mark.asyncio
    async def test_modbus_write_updates_min_max(self):
        """Verify min/max tracking logic."""
        await Metrics.modbus_write(registers=2, seconds=0.1)  # 100ms
        await Metrics.modbus_write(registers=2, seconds=0.05)  # 50ms
        await Metrics.modbus_write(registers=2, seconds=0.15)  # 150ms

        assert Metrics.sigenergy2mqtt_modbus_write_max == 150.0
        assert Metrics.sigenergy2mqtt_modbus_write_min == 50.0
        assert Metrics.sigenergy2mqtt_modbus_writes == 6

    @pytest.mark.asyncio
    async def test_modbus_write_mean_calculation(self):
        """Verify mean calculation."""
        await Metrics.modbus_write(registers=5, seconds=0.1)  # 100ms
        await Metrics.modbus_write(registers=5, seconds=0.2)  # 200ms

        # Total = 300ms, writes = 10, mean = 30ms
        assert Metrics.sigenergy2mqtt_modbus_write_mean == 30.0

    @pytest.mark.asyncio
    async def test_modbus_write_exception_handling(self):
        """Test exception handling with warning log."""
        with patch("logging.warning") as mock_warning:
            # Force an exception
            await Metrics.modbus_write(registers=None, seconds=0.1)
            assert mock_warning.called
            assert "modbus write metrics collection" in mock_warning.call_args[0][0]


class TestMetricsWriteError:
    """Tests for Metrics.modbus_write_error()."""

    @pytest.fixture(autouse=True)
    def reset_metrics(self):
        """Reset Metrics state before each test."""
        original_errors = Metrics.sigenergy2mqtt_modbus_write_errors
        Metrics.sigenergy2mqtt_modbus_write_errors = 0

        yield

        Metrics.sigenergy2mqtt_modbus_write_errors = original_errors

    @pytest.mark.asyncio
    async def test_modbus_write_error_success(self):
        """Test write error counter increment."""
        assert Metrics.sigenergy2mqtt_modbus_write_errors == 0

        await Metrics.modbus_write_error()
        assert Metrics.sigenergy2mqtt_modbus_write_errors == 1

        await Metrics.modbus_write_error()
        assert Metrics.sigenergy2mqtt_modbus_write_errors == 2

    @pytest.mark.asyncio
    async def test_modbus_write_error_exception_handling(self):
        """Test exception handling."""
        with patch.object(Metrics, "_lock") as mock_lock:
            mock_lock.acquire.side_effect = Exception("Test exception")

            with patch("logging.warning") as mock_warning:
                await Metrics.modbus_write_error()
                assert mock_warning.called
                assert "modbus write error metrics collection" in mock_warning.call_args[0][0]
