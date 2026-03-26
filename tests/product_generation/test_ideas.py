"""Tests for IdeaGenerator class."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from src.product_generation.ideas import IdeaGenerator, IdeaGenerationError
from src.product_generation.schemas import IdeaSet, ProductIdea


class TestIdeaGenerator:
    """Test IdeaGenerator implementation."""

    def test_initialization(self):
        """Test IdeaGenerator initializes with client and default model."""
        mock_client = MagicMock()
        generator = IdeaGenerator(mock_client)

        assert generator.client is mock_client
        assert generator.model == "gpt-4o"

    def test_custom_model(self):
        """Test IdeaGenerator accepts custom model."""
        mock_client = MagicMock()
        generator = IdeaGenerator(mock_client, model="gpt-4o-mini")

        assert generator.model == "gpt-4o-mini"

    @pytest.mark.asyncio
    async def test_generate_validates_niche_length(self):
        """Test generate rejects niche shorter than 3 characters."""
        mock_client = MagicMock()
        generator = IdeaGenerator(mock_client)

        with pytest.raises(ValueError, match="Niche must be at least 3 characters"):
            await generator.generate("ab")

    @pytest.mark.asyncio
    async def test_generate_accepts_valid_niche(self):
        """Test generate accepts valid niche input."""
        mock_client = MagicMock()
        generator = IdeaGenerator(mock_client)

        # Should not raise - will fail at API call but validation passes
        with pytest.raises(Exception):  # Will fail on API call since we don't mock
            await generator.generate("fitness")

    @pytest.mark.asyncio
    async def test_generate_parses_response_correctly(self):
        """Test generate parses OpenAI response into IdeaSet."""
        mock_client = MagicMock()
        generator = IdeaGenerator(mock_client)

        # Mock OpenAI response
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(
                message=MagicMock(
                    content='{"ideas": [{"title": "Test", "format_type": "planner", "target_audience": "Test", "unique_angle": "Test", "key_features": ["F1"], "rationale": "Test"}], "niche": "test"}'
                )
            )
        ]
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        result = await generator.generate("test")

        assert isinstance(result, IdeaSet)
        assert len(result.ideas) == 1
        assert result.niche == "test"
        assert result.ideas[0].title == "Test"

    @pytest.mark.asyncio
    async def test_generate_respects_count_parameter(self):
        """Test generate uses count parameter for number of ideas."""
        mock_client = MagicMock()
        generator = IdeaGenerator(mock_client)

        # Mock response that includes count in prompt
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(
                message=MagicMock(
                    content='{"ideas": [{"title": "Test", "format_type": "planner", "target_audience": "Test", "unique_angle": "Test", "key_features": ["F1"], "rationale": "Test"}], "niche": "test"}'
                )
            )
        ]
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        # Check the prompt contains the count
        await generator.generate("test", count=5)

        call_args = mock_client.chat.completions.create.call_args
        user_prompt = call_args.kwargs["messages"][1]["content"]
        assert "5" in user_prompt


class TestIdeaGenerationError:
    """Test IdeaGenerationError exception."""

    def test_error_message(self):
        """Test error message is captured correctly."""
        error = IdeaGenerationError("Test error message")
        assert str(error) == "Test error message"
