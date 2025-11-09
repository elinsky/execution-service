"""Slug generation utilities."""
import re
from typing import Optional


def slugify(text: str) -> str:
    """
    Convert text to URL-safe slug.

    Args:
        text: Input text to slugify

    Returns:
        URL-safe slug string

    Examples:
        >>> slugify("Learn Rust")
        'learn-rust'
        >>> slugify("DE Shaw TPM Role")
        'de-shaw-tpm-role'
    """
    # Convert to lowercase and strip whitespace
    slug = text.lower().strip()

    # Remove non-word characters (except spaces and hyphens)
    slug = re.sub(r"[^\w\s-]", "", slug)

    # Replace spaces and underscores with hyphens
    slug = re.sub(r"[\s_-]+", "-", slug)

    # Remove leading/trailing hyphens
    slug = re.sub(r"^-+|-+$", "", slug)

    return slug


async def generate_unique_slug(
    collection,
    base_slug: str,
    user_id: str,
    exclude_id: Optional[str] = None,
) -> str:
    """
    Generate a unique slug with numeric suffix if needed.

    Checks if base_slug exists for the user. If it does, tries base_slug-2,
    base_slug-3, etc. until a unique slug is found.

    Args:
        collection: MongoDB collection to check for uniqueness
        base_slug: Base slug to make unique
        user_id: User ID to scope uniqueness
        exclude_id: Optional document ID to exclude from uniqueness check
                   (useful when updating existing documents)

    Returns:
        Unique slug string

    Examples:
        If "learn-rust" exists, returns "learn-rust-2"
        If "learn-rust" and "learn-rust-2" exist, returns "learn-rust-3"
    """
    # Build the base query
    query = {
        "user_id": user_id,
        "slug": base_slug,
        "deleted": False,
    }

    # Exclude current document if updating
    if exclude_id:
        query["_id"] = {"$ne": exclude_id}

    # Check if base slug exists
    existing = await collection.find_one(query)

    if not existing:
        # Base slug is available
        return base_slug

    # Base slug exists, try numbered suffixes
    suffix = 2
    while True:
        candidate_slug = f"{base_slug}-{suffix}"
        query["slug"] = candidate_slug

        existing = await collection.find_one(query)
        if not existing:
            return candidate_slug

        suffix += 1
