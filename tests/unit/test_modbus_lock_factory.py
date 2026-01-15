"""Unit tests for ModbusLockFactory class."""

from unittest.mock import MagicMock, patch

import pytest

from sigenergy2mqtt.modbus.lock_factory import ModbusLockFactory


class TestModbusLockFactory:
    """Test cases for ModbusLockFactory class."""

    @pytest.fixture(autouse=True)
    def reset_factory(self):
        """Reset factory state before each test."""
        # Save original state
        original_locks = ModbusLockFactory._locks.copy()
        ModbusLockFactory._locks.clear()

        yield

        # Restore original state
        ModbusLockFactory._locks = original_locks

    @pytest.fixture
    def mock_modbus_client(self):
        """Create a mock modbus client."""
        return MagicMock()

    def test_get_with_none_returns_new_lock(self):
        """Test that get(None) returns a new ModbusLock with host=None."""
        with patch("sigenergy2mqtt.modbus.lock.ModbusClientFactory") as mock_factory:
            mock_factory.get_host.return_value = None

            lock = ModbusLockFactory.get(None)

            assert lock is not None
            assert lock.host is None
            assert lock.waiters == 0

    def test_get_with_none_returns_different_locks(self):
        """Test that get(None) returns new lock each time (not cached)."""
        with patch("sigenergy2mqtt.modbus.lock.ModbusClientFactory") as mock_factory:
            mock_factory.get_host.return_value = None

            lock1 = ModbusLockFactory.get(None)
            lock2 = ModbusLockFactory.get(None)

            # Each call with None should create a new lock
            assert lock1 is not lock2

    def test_get_with_client_caches_lock(self, mock_modbus_client):
        """Test that get(modbus) caches and returns same lock."""
        with patch("sigenergy2mqtt.modbus.lock.ModbusClientFactory") as mock_factory:
            mock_factory.get_host.return_value = "127.0.0.1:502"

            lock1 = ModbusLockFactory.get(mock_modbus_client)
            lock2 = ModbusLockFactory.get(mock_modbus_client)

            # Same client should return same cached lock
            assert lock1 is lock2
            assert lock1.host == "127.0.0.1:502"

    def test_get_different_clients_different_locks(self):
        """Test that different clients get different locks."""
        client1 = MagicMock()
        client2 = MagicMock()

        with patch("sigenergy2mqtt.modbus.lock.ModbusClientFactory") as mock_factory:
            mock_factory.get_host.side_effect = lambda c: "client1" if c is client1 else "client2"

            lock1 = ModbusLockFactory.get(client1)
            lock2 = ModbusLockFactory.get(client2)

            assert lock1 is not lock2
            assert lock1.host == "client1"
            assert lock2.host == "client2"

    def test_get_logs_debug_when_many_waiters(self, mock_modbus_client):
        """Test that get() logs debug message when waiters > 5."""
        with patch("sigenergy2mqtt.modbus.lock.ModbusClientFactory") as mock_factory:
            mock_factory.get_host.return_value = "127.0.0.1:502"

            # First get to create the lock
            lock = ModbusLockFactory.get(mock_modbus_client)

            # Manually set waiters > 5
            lock.waiters = 6

            with patch.object(ModbusLockFactory._logger, "debug") as mock_debug:
                # Get the lock again
                ModbusLockFactory.get(mock_modbus_client)

                # Verify debug was called
                mock_debug.assert_called_once()
                assert "waiters" in mock_debug.call_args[0][0]

    def test_get_no_log_when_few_waiters(self, mock_modbus_client):
        """Test that get() does not log when waiters <= 5."""
        with patch("sigenergy2mqtt.modbus.lock.ModbusClientFactory") as mock_factory:
            mock_factory.get_host.return_value = "127.0.0.1:502"

            # First get to create the lock
            lock = ModbusLockFactory.get(mock_modbus_client)

            # Set waiters to exactly 5
            lock.waiters = 5

            with patch.object(ModbusLockFactory._logger, "debug") as mock_debug:
                ModbusLockFactory.get(mock_modbus_client)

                # Should not log for 5 or fewer waiters
                mock_debug.assert_not_called()

    def test_get_waiter_count_empty(self):
        """Test get_waiter_count() returns 0 when no locks."""
        assert ModbusLockFactory.get_waiter_count() == 0

    def test_get_waiter_count_single_lock(self, mock_modbus_client):
        """Test get_waiter_count() with a single lock."""
        with patch("sigenergy2mqtt.modbus.lock.ModbusClientFactory") as mock_factory:
            mock_factory.get_host.return_value = "127.0.0.1:502"

            lock = ModbusLockFactory.get(mock_modbus_client)
            lock.waiters = 3

            assert ModbusLockFactory.get_waiter_count() == 3

    def test_get_waiter_count_multiple_locks(self):
        """Test get_waiter_count() sums waiters from all locks."""
        client1 = MagicMock()
        client2 = MagicMock()
        client3 = MagicMock()

        with patch("sigenergy2mqtt.modbus.lock.ModbusClientFactory") as mock_factory:
            mock_factory.get_host.side_effect = lambda c: str(id(c))

            lock1 = ModbusLockFactory.get(client1)
            lock2 = ModbusLockFactory.get(client2)
            lock3 = ModbusLockFactory.get(client3)

            lock1.waiters = 2
            lock2.waiters = 5
            lock3.waiters = 1

            assert ModbusLockFactory.get_waiter_count() == 8
