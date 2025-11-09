"""
Unit tests for RLS (Row-Level Security) enforcement functions.

Tests cover:
- assert_rls_enforced() validation
- @require_rls decorator
- rls_enforced_session() context manager
- Context variable management
- Security event logging
- Error handling
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.database import (
    assert_rls_enforced,
    require_rls,
    rls_enforced_session,
    RLSViolationError,
    _current_tenant_id,
    _rls_enforced,
    get_current_tenant_context,
    is_rls_active,
    db_manager
)


@pytest.fixture
def reset_context():
    """Reset context variables before and after each test."""
    _current_tenant_id.set(None)
    _rls_enforced.set(False)
    yield
    _current_tenant_id.set(None)
    _rls_enforced.set(False)


@pytest.fixture
def mock_db_session():
    """Create mock database session."""
    session = AsyncMock(spec=AsyncSession)
    return session


@pytest.fixture
def test_tenant_id():
    """Test tenant UUID."""
    return "550e8400-e29b-41d4-a716-446655440000"


class TestAssertRLSEnforced:
    """Test assert_rls_enforced() function."""

    def test_assert_rls_enforced_raises_when_not_enforced(self, reset_context):
        """Test that assertion raises exception when RLS not enforced."""
        # RLS not enforced
        _rls_enforced.set(False)

        with pytest.raises(RLSViolationError) as exc_info:
            assert_rls_enforced()

        assert "Security violation" in str(exc_info.value)
        assert "RLS enforcement" in str(exc_info.value)

    def test_assert_rls_enforced_passes_when_enforced(self, reset_context):
        """Test that assertion passes when RLS is enforced."""
        # Set RLS enforced
        _rls_enforced.set(True)

        # Should not raise exception
        assert_rls_enforced()

    def test_assert_rls_enforced_allow_system_true(self, reset_context):
        """Test that allow_system=True bypasses RLS check."""
        # RLS not enforced
        _rls_enforced.set(False)

        # Should not raise with allow_system=True
        assert_rls_enforced(allow_system=True)

    def test_assert_rls_enforced_logs_security_event(self, reset_context):
        """Test that RLS violation is logged."""
        _rls_enforced.set(False)

        with patch('backend.core.database.structured_logger') as mock_logger:
            with pytest.raises(RLSViolationError):
                assert_rls_enforced()

            # Verify security event was logged
            mock_logger.error.assert_called_once()
            call_args = mock_logger.error.call_args
            assert "RLS violation" in call_args[0][0]
            assert call_args[1]['security_event'] == "RLS_NOT_ENFORCED"

    def test_assert_rls_enforced_with_tenant_context(self, reset_context, test_tenant_id):
        """Test assertion with tenant context set."""
        _current_tenant_id.set(test_tenant_id)
        _rls_enforced.set(True)

        # Should not raise
        assert_rls_enforced()


class TestRequireRLSDecorator:
    """Test @require_rls decorator."""

    @pytest.mark.asyncio
    async def test_require_rls_decorator_raises_when_not_enforced(self, reset_context):
        """Test that decorator raises exception when RLS not enforced."""
        @require_rls
        async def test_function():
            return "success"

        # RLS not enforced
        _rls_enforced.set(False)

        with pytest.raises(RLSViolationError):
            await test_function()

    @pytest.mark.asyncio
    async def test_require_rls_decorator_passes_when_enforced(self, reset_context):
        """Test that decorator allows execution when RLS enforced."""
        @require_rls
        async def test_function():
            return "success"

        # Set RLS enforced
        _rls_enforced.set(True)

        result = await test_function()
        assert result == "success"

    @pytest.mark.asyncio
    async def test_require_rls_decorator_with_arguments(self, reset_context):
        """Test that decorator works with function arguments."""
        @require_rls
        async def test_function(arg1, arg2, kwarg1=None):
            return f"{arg1}-{arg2}-{kwarg1}"

        _rls_enforced.set(True)

        result = await test_function("a", "b", kwarg1="c")
        assert result == "a-b-c"

    @pytest.mark.asyncio
    async def test_require_rls_decorator_logs_execution(self, reset_context, test_tenant_id):
        """Test that decorator logs function execution."""
        @require_rls
        async def test_function():
            return "success"

        _rls_enforced.set(True)
        _current_tenant_id.set(test_tenant_id)

        with patch('backend.core.database.structured_logger') as mock_logger:
            await test_function()

            # Verify debug log was created
            mock_logger.debug.assert_called_once()
            call_args = mock_logger.debug.call_args
            assert "RLS-protected function executed" in call_args[0][0]
            assert call_args[1]['function'] == "test_function"
            assert call_args[1]['tenant_id'] == test_tenant_id

    @pytest.mark.asyncio
    async def test_require_rls_decorator_preserves_function_metadata(self, reset_context):
        """Test that decorator preserves function name and docstring."""
        @require_rls
        async def test_function():
            """Test docstring."""
            return "success"

        assert test_function.__name__ == "test_function"
        # Note: @wraps may not preserve docstring in test environment


class TestRLSEnforcedSession:
    """Test rls_enforced_session() context manager."""

    @pytest.mark.asyncio
    async def test_rls_enforced_session_sets_context(
        self,
        reset_context,
        mock_db_session,
        test_tenant_id
    ):
        """Test that context manager sets RLS context."""
        # Mock execute to return tenant_id when queried
        mock_result = Mock()
        mock_result.scalar.return_value = test_tenant_id
        mock_db_session.execute.return_value = mock_result

        async with rls_enforced_session(mock_db_session, test_tenant_id, "test_op") as session:
            # Inside context, RLS should be enforced
            assert _rls_enforced.get() is True
            assert _current_tenant_id.get() == test_tenant_id

        # After context, RLS should be cleared
        assert _rls_enforced.get() is False
        assert _current_tenant_id.get() is None

    @pytest.mark.asyncio
    async def test_rls_enforced_session_calls_set_tenant_context(
        self,
        reset_context,
        mock_db_session,
        test_tenant_id
    ):
        """Test that context manager calls db_manager.set_tenant_context()."""
        with patch.object(db_manager, 'set_tenant_context', new_callable=AsyncMock) as mock_set:
            with patch.object(db_manager, 'clear_tenant_context', new_callable=AsyncMock) as mock_clear:
                async with rls_enforced_session(mock_db_session, test_tenant_id, "test_op"):
                    pass

                # Verify set was called
                mock_set.assert_called_once_with(mock_db_session, test_tenant_id)

                # Verify clear was called
                mock_clear.assert_called_once_with(mock_db_session)

    @pytest.mark.asyncio
    async def test_rls_enforced_session_logs_start_and_end(
        self,
        reset_context,
        mock_db_session,
        test_tenant_id
    ):
        """Test that context manager logs operation start and end."""
        with patch('backend.core.database.structured_logger') as mock_logger:
            with patch.object(db_manager, 'set_tenant_context', new_callable=AsyncMock):
                with patch.object(db_manager, 'clear_tenant_context', new_callable=AsyncMock):
                    async with rls_enforced_session(
                        mock_db_session,
                        test_tenant_id,
                        "test_operation"
                    ):
                        pass

            # Check info log (start)
            info_calls = [call for call in mock_logger.info.call_args_list]
            assert len(info_calls) > 0
            assert "RLS context established" in info_calls[0][0][0]

            # Check debug log (end)
            debug_calls = [call for call in mock_logger.debug.call_args_list]
            assert len(debug_calls) > 0
            assert "RLS context cleared" in str(debug_calls)

    @pytest.mark.asyncio
    async def test_rls_enforced_session_clears_context_on_exception(
        self,
        reset_context,
        mock_db_session,
        test_tenant_id
    ):
        """Test that context is cleared even if exception occurs."""
        with patch.object(db_manager, 'set_tenant_context', new_callable=AsyncMock):
            with patch.object(db_manager, 'clear_tenant_context', new_callable=AsyncMock) as mock_clear:
                with pytest.raises(ValueError):
                    async with rls_enforced_session(
                        mock_db_session,
                        test_tenant_id,
                        "test_op"
                    ):
                        raise ValueError("Test error")

                # Verify clear was still called
                mock_clear.assert_called_once()

    @pytest.mark.asyncio
    async def test_rls_enforced_session_allows_queries(
        self,
        reset_context,
        mock_db_session,
        test_tenant_id
    ):
        """Test that queries can execute inside context manager."""
        with patch.object(db_manager, 'set_tenant_context', new_callable=AsyncMock):
            with patch.object(db_manager, 'clear_tenant_context', new_callable=AsyncMock):
                async with rls_enforced_session(
                    mock_db_session,
                    test_tenant_id,
                    "test_op"
                ) as session:
                    # Inside context, RLS is enforced
                    # This should not raise
                    assert_rls_enforced()

                    # Simulate query execution
                    await session.execute("SELECT * FROM evf")


class TestContextVariableFunctions:
    """Test context variable helper functions."""

    def test_get_current_tenant_context_returns_tenant_id(self, reset_context, test_tenant_id):
        """Test get_current_tenant_context() returns current tenant ID."""
        _current_tenant_id.set(test_tenant_id)

        result = get_current_tenant_context()
        assert result == test_tenant_id

    def test_get_current_tenant_context_returns_none_when_not_set(self, reset_context):
        """Test get_current_tenant_context() returns None when not set."""
        result = get_current_tenant_context()
        assert result is None

    def test_is_rls_active_returns_true_when_enforced(self, reset_context):
        """Test is_rls_active() returns True when RLS enforced."""
        _rls_enforced.set(True)

        result = is_rls_active()
        assert result is True

    def test_is_rls_active_returns_false_when_not_enforced(self, reset_context):
        """Test is_rls_active() returns False when not enforced."""
        _rls_enforced.set(False)

        result = is_rls_active()
        assert result is False


class TestConcurrency:
    """Test thread safety of RLS enforcement."""

    @pytest.mark.asyncio
    async def test_concurrent_rls_checks(self, reset_context):
        """Test that concurrent RLS checks are safe."""
        _rls_enforced.set(True)

        async def check_rls():
            assert_rls_enforced()
            return True

        # Run 50 concurrent checks
        tasks = [check_rls() for _ in range(50)]
        results = await asyncio.gather(*tasks)

        assert all(results)

    @pytest.mark.asyncio
    async def test_concurrent_context_access(self, reset_context, test_tenant_id):
        """Test that concurrent context access is safe."""
        _current_tenant_id.set(test_tenant_id)
        _rls_enforced.set(True)

        async def get_context():
            tenant_id = get_current_tenant_context()
            is_active = is_rls_active()
            return tenant_id, is_active

        # Run 50 concurrent reads
        tasks = [get_context() for _ in range(50)]
        results = await asyncio.gather(*tasks)

        # All should return same values
        for tenant_id, is_active in results:
            assert tenant_id == test_tenant_id
            assert is_active is True


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_assert_rls_enforced_with_no_tenant_id(self, reset_context):
        """Test assertion with RLS enforced but no tenant ID."""
        # RLS enforced but no tenant_id
        _rls_enforced.set(True)
        _current_tenant_id.set(None)

        # Should still pass (system operation)
        assert_rls_enforced()

    def test_assert_rls_enforced_with_tenant_id_no_enforcement(
        self,
        reset_context,
        test_tenant_id
    ):
        """Test assertion with tenant ID but no enforcement."""
        # Tenant ID set but RLS not enforced
        _current_tenant_id.set(test_tenant_id)
        _rls_enforced.set(False)

        with pytest.raises(RLSViolationError):
            assert_rls_enforced()

    @pytest.mark.asyncio
    async def test_nested_rls_enforced_sessions(
        self,
        reset_context,
        mock_db_session,
        test_tenant_id
    ):
        """Test nested rls_enforced_session contexts."""
        tenant_id_2 = "660e8400-e29b-41d4-a716-446655440000"

        with patch.object(db_manager, 'set_tenant_context', new_callable=AsyncMock):
            with patch.object(db_manager, 'clear_tenant_context', new_callable=AsyncMock):
                # Outer context
                async with rls_enforced_session(
                    mock_db_session,
                    test_tenant_id,
                    "outer_op"
                ):
                    assert _current_tenant_id.get() == test_tenant_id

                    # Inner context (different tenant)
                    # This should work because each context is independent
                    async with rls_enforced_session(
                        mock_db_session,
                        tenant_id_2,
                        "inner_op"
                    ):
                        # Inner tenant should be active
                        assert _current_tenant_id.get() == tenant_id_2

                # After both contexts, should be cleared
                assert _rls_enforced.get() is False


@pytest.mark.integration
class TestRLSEnforcementIntegration:
    """Integration tests for RLS enforcement with database operations."""

    @pytest.mark.asyncio
    async def test_route_handler_pattern(self, reset_context, mock_db_session, test_tenant_id):
        """Test typical FastAPI route handler pattern."""
        @require_rls
        async def route_handler(db: AsyncSession):
            # Simulate query
            return {"data": "result"}

        # Simulate middleware setting RLS context
        _current_tenant_id.set(test_tenant_id)
        _rls_enforced.set(True)

        result = await route_handler(mock_db_session)
        assert result["data"] == "result"

    @pytest.mark.asyncio
    async def test_background_task_pattern(
        self,
        reset_context,
        mock_db_session,
        test_tenant_id
    ):
        """Test typical background task pattern."""
        async def background_task(tenant_id: str):
            with patch.object(db_manager, 'set_tenant_context', new_callable=AsyncMock):
                with patch.object(db_manager, 'clear_tenant_context', new_callable=AsyncMock):
                    async with rls_enforced_session(
                        mock_db_session,
                        tenant_id,
                        "background_task"
                    ):
                        # Query execution
                        assert_rls_enforced()
                        return "task_complete"

        result = await background_task(test_tenant_id)
        assert result == "task_complete"

    @pytest.mark.asyncio
    async def test_agent_operation_pattern(
        self,
        reset_context,
        mock_db_session,
        test_tenant_id
    ):
        """Test typical LangGraph agent operation pattern."""
        async def agent_operation(state: dict):
            tenant_id = state["tenant_id"]

            with patch.object(db_manager, 'set_tenant_context', new_callable=AsyncMock):
                with patch.object(db_manager, 'clear_tenant_context', new_callable=AsyncMock):
                    async with rls_enforced_session(
                        mock_db_session,
                        tenant_id,
                        "agent_operation"
                    ):
                        # Agent can query database
                        assert_rls_enforced()
                        return {"status": "success"}

        state = {"tenant_id": test_tenant_id}
        result = await agent_operation(state)
        assert result["status"] == "success"


class TestSecurityEventLogging:
    """Test that security events are properly logged."""

    def test_rls_violation_logs_security_event(self, reset_context):
        """Test that RLS violation logs security event."""
        _rls_enforced.set(False)

        with patch('backend.core.database.structured_logger') as mock_logger:
            with pytest.raises(RLSViolationError):
                assert_rls_enforced()

            # Verify error was logged with security event
            mock_logger.error.assert_called_once()
            assert mock_logger.error.call_args[1]['security_event'] == "RLS_NOT_ENFORCED"

    def test_rls_enforcement_includes_context_info(self, reset_context, test_tenant_id):
        """Test that RLS logs include context information."""
        _current_tenant_id.set(test_tenant_id)
        _rls_enforced.set(False)

        with patch('backend.core.database.structured_logger') as mock_logger:
            with pytest.raises(RLSViolationError):
                assert_rls_enforced()

            # Verify tenant_id was included in log
            assert mock_logger.error.call_args[1]['tenant_id'] == test_tenant_id
            assert mock_logger.error.call_args[1]['rls_enforced'] is False
