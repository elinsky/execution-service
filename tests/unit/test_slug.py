"""Tests for slug utility functions."""
import pytest
from unittest.mock import AsyncMock, MagicMock


class TestSlugify:
    """Tests for slugify function."""

    def test_slugify_basic(self):
        """Test basic slug conversion."""
        from app.utils.slug import slugify

        assert slugify("Learn Rust") == "learn-rust"
        assert slugify("DE Shaw TPM Role") == "de-shaw-tpm-role"
        assert slugify("Become Staff Engineer") == "become-staff-engineer"

    def test_slugify_special_characters(self):
        """Test that special characters are removed."""
        from app.utils.slug import slugify

        assert slugify("Project: Machine Learning!") == "project-machine-learning"
        assert slugify("Test (with parentheses)") == "test-with-parentheses"
        assert slugify("Email@example.com") == "emailexamplecom"

    def test_slugify_multiple_spaces(self):
        """Test that multiple spaces are collapsed."""
        from app.utils.slug import slugify

        assert slugify("Multiple   Spaces   Here") == "multiple-spaces-here"
        assert slugify("Tab\tSeparated") == "tab-separated"

    def test_slugify_leading_trailing_dashes(self):
        """Test that leading/trailing dashes are removed."""
        from app.utils.slug import slugify

        assert slugify("-Leading dash") == "leading-dash"
        assert slugify("Trailing dash-") == "trailing-dash"
        assert slugify("-Both sides-") == "both-sides"

    def test_slugify_empty_string(self):
        """Test slugify with empty string."""
        from app.utils.slug import slugify

        assert slugify("") == ""
        assert slugify("   ") == ""

    def test_slugify_unicode(self):
        """Test slugify preserves unicode characters."""
        from app.utils.slug import slugify

        # Unicode characters are preserved (acceptable for modern URLs)
        assert slugify("Café") == "café"
        assert slugify("naïve") == "naïve"

    def test_slugify_numbers(self):
        """Test slugify preserves numbers."""
        from app.utils.slug import slugify

        assert slugify("Project 123") == "project-123"
        assert slugify("2024 Goals") == "2024-goals"


@pytest.mark.asyncio
class TestGenerateUniqueSlug:
    """Tests for generate_unique_slug function."""

    async def test_unique_slug_no_conflict(self):
        """Test generating unique slug when no conflict exists."""
        from app.utils.slug import generate_unique_slug

        # Mock collection with no existing slugs
        mock_collection = AsyncMock()
        mock_collection.find_one.return_value = None

        slug = await generate_unique_slug(
            collection=mock_collection,
            base_slug="learn-rust",
            user_id="user123",
        )

        assert slug == "learn-rust"
        mock_collection.find_one.assert_called_once()

    async def test_unique_slug_with_conflict(self):
        """Test generating unique slug when slug already exists."""
        from app.utils.slug import generate_unique_slug

        # Mock collection that returns existing slug
        mock_collection = AsyncMock()
        mock_collection.find_one.side_effect = [
            {"slug": "learn-rust"},  # First call: slug exists
            None,  # Second call: learn-rust-2 doesn't exist
        ]

        slug = await generate_unique_slug(
            collection=mock_collection,
            base_slug="learn-rust",
            user_id="user123",
        )

        assert slug == "learn-rust-2"
        assert mock_collection.find_one.call_count == 2

    async def test_unique_slug_multiple_conflicts(self):
        """Test generating unique slug when multiple slugs exist."""
        from app.utils.slug import generate_unique_slug

        # Mock collection with multiple existing slugs
        mock_collection = AsyncMock()
        mock_collection.find_one.side_effect = [
            {"slug": "learn-rust"},  # learn-rust exists
            {"slug": "learn-rust-2"},  # learn-rust-2 exists
            {"slug": "learn-rust-3"},  # learn-rust-3 exists
            None,  # learn-rust-4 doesn't exist
        ]

        slug = await generate_unique_slug(
            collection=mock_collection,
            base_slug="learn-rust",
            user_id="user123",
        )

        assert slug == "learn-rust-4"
        assert mock_collection.find_one.call_count == 4

    async def test_unique_slug_with_exclude_id(self):
        """Test generating unique slug while excluding current document."""
        from app.utils.slug import generate_unique_slug

        # Mock collection
        mock_collection = AsyncMock()
        mock_collection.find_one.return_value = None

        slug = await generate_unique_slug(
            collection=mock_collection,
            base_slug="learn-rust",
            user_id="user123",
            exclude_id="project123",
        )

        assert slug == "learn-rust"
        # Verify the query excludes the current document
        call_args = mock_collection.find_one.call_args
        query = call_args[0][0]
        assert "_id" in query
        assert query["_id"]["$ne"] == "project123"

    async def test_unique_slug_user_scoped(self):
        """Test that slug uniqueness is scoped to user."""
        from app.utils.slug import generate_unique_slug

        mock_collection = AsyncMock()
        mock_collection.find_one.return_value = None

        slug = await generate_unique_slug(
            collection=mock_collection,
            base_slug="learn-rust",
            user_id="user123",
        )

        # Verify user_id is included in the query
        call_args = mock_collection.find_one.call_args
        query = call_args[0][0]
        assert "user_id" in query
        assert query["user_id"] == "user123"
