"""
Comparison utilities for detecting changes between Exchange scrape runs.

Compares two lists of items by a unique ID field and returns
new, updated, and removed items.
"""

from __future__ import annotations

from typing import Any


def compare_items(
    current: list[dict[str, Any]],
    previous: list[dict[str, Any]],
    id_field: str = "id",
    exclude_fields: list[str] | None = None,
) -> dict[str, list[dict[str, Any]]]:
    """
    Compare two lists of items and return differences.

    Args:
        current: The newly scraped items
        previous: The items from the last run
        id_field: The field to use as the unique identifier
        exclude_fields: Fields to exclude when comparing for updates
                        (e.g. scraped_at which always changes)

    Returns:
        dict with keys "new", "updated", "removed", each containing a list of items
    """
    if exclude_fields is None:
        exclude_fields = ["scraped_at"]

    current_by_id: dict[str, dict[str, Any]] = {
        item[id_field]: item for item in current if id_field in item
    }
    previous_by_id: dict[str, dict[str, Any]] = {
        item[id_field]: item for item in previous if id_field in item
    }

    new_items: list[dict[str, Any]] = []
    updated_items: list[dict[str, Any]] = []
    removed_items: list[dict[str, Any]] = []

    # Find new and updated
    for item_id, item in current_by_id.items():
        if item_id not in previous_by_id:
            new_items.append(item)
        else:
            prev = previous_by_id[item_id]
            # Compare fields excluding the excluded ones
            changed = False
            for key, val in item.items():
                if key in exclude_fields:
                    continue
                if prev.get(key) != val:
                    changed = True
                    break
            if changed:
                updated_items.append(item)

    # Find removed
    for item_id, item in previous_by_id.items():
        if item_id not in current_by_id:
            removed_items.append(item)

    return {
        "new": new_items,
        "updated": updated_items,
        "removed": removed_items,
    }
