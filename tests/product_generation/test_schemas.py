"""Tests for product generation schemas."""

import pytest
from datetime import datetime

from src.product_generation.schemas import ProductIdea, IdeaSet


class TestProductIdea:
    """Test ProductIdea model validation."""

    def test_valid_product_idea(self):
        """Test creating a valid ProductIdea."""
        idea = ProductIdea(
            title="Fitness Planner 2024",
            format_type="planner",
            target_audience="Fitness enthusiasts",
            unique_angle="30-day challenge focus",
            key_features=["Daily workout log", "Meal planner", "Progress tracker"],
            rationale="High demand for fitness organization tools",
        )
        assert idea.title == "Fitness Planner 2024"
        assert idea.format_type == "planner"
        assert len(idea.key_features) == 3

    def test_all_format_types(self):
        """Test all valid format types."""
        for format_type in ["planner", "worksheet", "guide"]:
            idea = ProductIdea(
                title="Test",
                format_type=format_type,
                target_audience="Test audience",
                unique_angle="Test angle",
                key_features=["Feature 1"],
                rationale="Test rationale",
            )
            assert idea.format_type == format_type

    def test_invalid_format_type(self):
        """Test invalid format type is rejected."""
        with pytest.raises(ValueError):
            ProductIdea(
                title="Test",
                format_type="ebook",  # Invalid
                target_audience="Test",
                unique_angle="Test",
                key_features=["Test"],
                rationale="Test",
            )


class TestIdeaSet:
    """Test IdeaSet model validation."""

    def test_valid_idea_set(self):
        """Test creating a valid IdeaSet."""
        idea = ProductIdea(
            title="Test Product",
            format_type="planner",
            target_audience="Test audience",
            unique_angle="Test angle",
            key_features=["Feature 1"],
            rationale="Test rationale",
        )
        idea_set = IdeaSet(
            ideas=[idea],
            niche="Health & Wellness",
        )
        assert len(idea_set.ideas) == 1
        assert idea_set.niche == "Health & Wellness"
        assert idea_set.generated_at is not None

    def test_multiple_ideas(self):
        """Test IdeaSet with multiple ideas."""
        ideas = [
            ProductIdea(
                title=f"Product {i}",
                format_type="planner",
                target_audience="Test",
                unique_angle="Test",
                key_features=["Feature"],
                rationale="Test",
            )
            for i in range(3)
        ]
        idea_set = IdeaSet(ideas=ideas, niche="Test Niche")
        assert len(idea_set.ideas) == 3
