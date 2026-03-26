"""Tests for idea generation API routes."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient

from src.api.idea_routes import router


class TestIdeaGenerateRequest:
    """Test IdeaGenerateRequest model validation."""

    def test_valid_request(self):
        """Test valid request with minimum niche length."""
        from src.api.idea_routes import IdeaGenerateRequest

        request = IdeaGenerateRequest(niche="fitness")
        assert request.niche == "fitness"
        assert request.count == 3  # default

    def test_custom_count(self):
        """Test custom count parameter."""
        from src.api.idea_routes import IdeaGenerateRequest

        request = IdeaGenerateRequest(niche="fitness", count=5)
        assert request.count == 5

    def test_invalid_niche_too_short(self):
        """Test niche shorter than 3 characters is rejected."""
        from src.api.idea_routes import IdeaGenerateRequest

        with pytest.raises(ValueError):
            IdeaGenerateRequest(niche="ab")


class TestIdeaGenerateResponse:
    """Test IdeaGenerateResponse model."""

    def test_response_structure(self):
        """Test response has required fields."""
        from src.api.idea_routes import IdeaGenerateResponse

        response = IdeaGenerateResponse(
            ideas=[{"title": "Test", "format_type": "planner"}],
            niche="test",
            generated_at="2024-01-01T00:00:00",
        )
        assert len(response.ideas) == 1
        assert response.niche == "test"


class TestIdeaRoutes:
    """Test API routes for idea generation."""

    def test_router_has_generate_endpoint(self):
        """Test router has POST /generate endpoint."""
        routes = [r.path for r in router.routes]
        assert "/generate" in routes

    def test_router_tag(self):
        """Test router is tagged with 'ideas'."""
        assert router.tags == ["ideas"]
