"""
Unit tests for Session Service.

Tests the unified session service for interview and practice sessions.
"""
import pytest
import uuid

from app.services.session_service import SessionService
from app.exceptions import AIServiceError


class TestSessionService:
    """Test cases for SessionService."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_create_session_success(self, db_session, sample_user):
        """Call create_session, assert InterviewSession created with correct role, status, mode."""
        service = SessionService(db_session)
        session = await service.create_session(
            user_id=sample_user.id,
            role="Python Developer",
            job_description="Looking for Python dev",
        )

        assert session is not None
        assert session.role == "Python Developer"
        assert session.status == "active"
        assert session.mode == "interview"
        assert session.user_id == sample_user.id

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_create_session_with_title(self, db_session, sample_user):
        """Pass title, assert job_context contains title."""
        service = SessionService(db_session)
        session = await service.create_session(
            user_id=sample_user.id,
            role="Developer",
            job_description="JD",
            title="Senior Python Developer",
        )

        assert session.job_context is not None
        assert session.job_context.get("title") == "Senior Python Developer"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_create_session_rollback_on_error(self, db_session):
        """Force DB error (invalid user_id), assert rollback and AIServiceError."""
        service = SessionService(db_session)
        # Use non-existent user_id to trigger FK violation
        fake_user_id = uuid.uuid4()

        with pytest.raises(AIServiceError, match="Failed to create interview session"):
            await service.create_session(
                user_id=fake_user_id,
                role="Developer",
                job_description="JD",
            )

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_create_practice_session_success(self, db_session, sample_user):
        """Call create_practice_session, assert session with mode=practice, scenario_id."""
        service = SessionService(db_session)
        scenario_id = "scenario-123"
        session = await service.create_practice_session(
            user_id=sample_user.id,
            role="Developer",
            scenario_id=scenario_id,
        )

        assert session is not None
        assert session.mode == "practice"
        assert session.scenario_id == scenario_id
        assert session.user_id == sample_user.id

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_session_success(self, db_session, sample_user):
        """Create session, call get_session, assert session returned."""
        service = SessionService(db_session)
        created = await service.create_session(
            user_id=sample_user.id,
            role="Developer",
            job_description="JD",
        )

        result = await service.get_session(
            session_id=str(created.id),
            user_id=sample_user.id,
        )

        assert result is not None
        assert result.id == created.id
        assert result.role == created.role

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_session_wrong_user(self, db_session, sample_user):
        """Create for user A, call with user B, assert None."""
        service = SessionService(db_session)
        created = await service.create_session(
            user_id=sample_user.id,
            role="Developer",
            job_description="JD",
        )

        other_user_id = uuid.uuid4()
        result = await service.get_session(
            session_id=str(created.id),
            user_id=other_user_id,
        )

        assert result is None

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_session_not_found(self, db_session, sample_user):
        """Call with fake session_id, assert None."""
        service = SessionService(db_session)
        fake_id = str(uuid.uuid4())

        result = await service.get_session(
            session_id=fake_id,
            user_id=sample_user.id,
        )

        assert result is None

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_create_interview_session(self, db_session, sample_user):
        """Alias for create_session, assert mode=interview."""
        service = SessionService(db_session)
        session = await service.create_interview_session(
            user_id=sample_user.id,
            role="Developer",
            job_title="Senior Dev",
            job_description="JD",
        )

        assert session is not None
        assert session.mode == "interview"
        assert session.job_context.get("title") == "Senior Dev"
