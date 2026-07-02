"""
Ignition Exchange scraper.

Collects resource listings from the Ignition Exchange using its JSON API
(the same API the exchange website itself calls), not DOM scraping.

Why the API and not the page?
    inductiveautomation.com/exchange is a JavaScript single-page app that
    lazily renders resource cards. Parsing the initial HTML only ever yields
    the handful of links present on first paint (~17), which is why the old
    Playwright + BeautifulSoup approach missed the other ~540 resources.

    Two endpoints give us everything in two requests:
      POST /exchange/api/search      -> every resource (all fields, images, tags)
      GET  /exchange/api/initialize  -> filter metadata incl. category id->name map

Endpoint paths, base URL and the scope filter are loaded from selectors.json,
which can be updated remotely via RemoteDataManager without code changes.
"""

from __future__ import annotations

import logging
import sys
import threading
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ignition_toolkit.core.remote_data import RemoteDataConfig, RemoteDataManager
from ignition_toolkit.core.remote_data_registry import RemoteDataRegistry

logger = logging.getLogger(__name__)

# Default fallbacks used when the remote/bundled config is unavailable
_DEFAULT_API_BASE = "https://inductiveautomation.com"
_DEFAULT_SEARCH_PATH = "/exchange/api/search"
_DEFAULT_INITIALIZE_PATH = "/exchange/api/initialize"
_DEFAULT_RESOURCE_URL_TEMPLATE = "https://inductiveautomation.com/exchange/{id}"
_DEFAULT_EXCHANGE_URL = "https://inductiveautomation.com/exchange"
_DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)
# The public website only lists Public-scope resources. The API also returns
# Organization- and Private-scope entries, which would inflate the count
# (793 raw vs ~560 shown publicly), so we filter to these scopes by default.
_DEFAULT_SCOPE_FILTER = ["Public"]

_HTTP_TIMEOUT = 60.0

# Module-level config manager (lazy-initialized)
_selectors_manager: RemoteDataManager | None = None


def _get_selectors_path() -> Path:
    """Get path to bundled selectors.json, handling frozen (PyInstaller) mode."""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS) / "exchange" / "selectors.json"
    return Path(__file__).parent / "selectors.json"


def _get_config() -> dict:
    """Load API configuration, initializing the manager on first call."""
    global _selectors_manager
    if _selectors_manager is None:
        config = RemoteDataConfig(
            component_name="exchange_selectors",
            filename="selectors.json",
            github_path="data/exchange/selectors.json",
            bundled_path_fn=_get_selectors_path,
        )
        _selectors_manager = RemoteDataManager(config)
        RemoteDataRegistry.register(_selectors_manager)
    return _selectors_manager.load()


def get_exchange_url() -> str:
    """Get the human-facing Exchange URL (used for logging/reference)."""
    return _get_config().get("exchange_url", _DEFAULT_EXCHANGE_URL)


def decode_version(raw: Any) -> str:
    """
    Decode the Exchange's packed integer version into "major.minor.patch".

    The Exchange stores versions as parseInt(major4 + minor4 + patch4), i.e. a
    12-digit string (each component zero-padded to 4 digits) with leading zeros
    stripped. Example: 100000000 -> "000100000000" -> 1.0.0; 200030004 -> 2.3.4.
    """
    if raw in (None, "", 0, "0"):
        return ""
    try:
        s = str(int(raw)).zfill(12)
    except (TypeError, ValueError):
        return str(raw).strip()
    major, minor, patch = int(s[0:4]), int(s[4:8]), int(s[8:12])
    return f"{major}.{minor}.{patch}"


def _category_map(initialize_data: dict) -> dict[str, str]:
    """Build an {id: title} map from the initialize endpoint's categories list."""
    result: dict[str, str] = {}
    for cat in initialize_data.get("categories", []) or []:
        cid = str(cat.get("id", "")).strip()
        title = (cat.get("title") or "").strip()
        if cid and title:
            result[cid] = title
    return result


def _pick_image(raw: dict) -> str:
    """Return the best screenshot URL for a resource, or ''."""
    media = raw.get("media_package_files") or []
    for m in media:
        url = (m.get("url") or "").strip()
        if url:
            return url
    return ""


def transform_resource(
    raw: dict[str, Any],
    category_map: dict[str, str],
    resource_url_template: str,
) -> dict[str, Any]:
    """Map a raw Exchange API resource into the toolbox result schema."""
    rid = str(raw.get("id", "")).strip()

    # Categories: raw is a list of id strings; map to human names.
    cat_ids = raw.get("categories") or []
    cat_names = [category_map.get(str(c), "") for c in cat_ids]
    cat_names = [c for c in cat_names if c]
    # Primary category drives the single-column display + filter dropdown.
    primary_category = cat_names[0] if cat_names else ""

    # Tags: list of {title}; sort for run-to-run stability in change detection.
    tags = sorted(
        {(t.get("title") or "").strip() for t in (raw.get("tags") or []) if t.get("title")}
    )

    download_count = 0
    try:
        download_count = int(raw.get("download_count") or 0)
    except (TypeError, ValueError):
        pass

    # "modified" is the last-updated timestamp (YYYY-MM-DD HH:MM:SS); keep date.
    updated_raw = (raw.get("modified") or raw.get("rv_modified") or "").strip()
    updated_date = updated_raw.split(" ")[0] if updated_raw else ""

    return {
        "id": rid,
        "url": resource_url_template.format(id=rid),
        "title": (raw.get("title") or "").strip(),
        "contributor": (raw.get("author_name") or "").strip(),
        "category": primary_category,
        "categories": cat_names,
        "download_count": download_count,
        "version": decode_version(raw.get("version")),
        "updated_date": updated_date,
        "tagline": (raw.get("tagline") or "").strip(),
        "image_url": _pick_image(raw),
        "resource_type": (raw.get("type_title") or "").strip(),
        "ignition_version": (raw.get("ignition_version_title") or "").strip(),
        "skill_level": (raw.get("skill_level_title") or "").strip(),
        "tags": tags,
        "scope": (raw.get("scope_title") or "").strip(),
        "scraped_at": datetime.now(timezone.utc).isoformat(),
    }


async def scrape_all(
    max_resources: int = 0,
    headless: bool = True,
    stop_event: threading.Event | None = None,
    progress_callback: Callable[[int, int], None] | None = None,
) -> list[dict[str, Any]]:
    """
    Scrape all resources from the Ignition Exchange via its JSON API.

    Args:
        max_resources: Maximum number of resources to keep (0 = all).
        headless: Unused (kept for API compatibility; no browser is launched).
        stop_event: Threading event to signal early stop.
        progress_callback: Called with (current, total) as resources are processed.

    Returns:
        List of resource dicts in the toolbox schema.
    """
    import httpx

    cfg = _get_config()
    api_base = cfg.get("api_base", _DEFAULT_API_BASE).rstrip("/")
    search_path = cfg.get("search_path", _DEFAULT_SEARCH_PATH)
    initialize_path = cfg.get("initialize_path", _DEFAULT_INITIALIZE_PATH)
    resource_url_template = cfg.get("resource_url_template", _DEFAULT_RESOURCE_URL_TEMPLATE)
    user_agent = cfg.get("user_agent", _DEFAULT_USER_AGENT)

    scope_filter = cfg.get("scope_filter", _DEFAULT_SCOPE_FILTER)
    # Normalize to a set of allowed scope titles; empty/None => no scope filtering.
    scope_allow: set[str] | None
    if scope_filter:
        scope_allow = {str(s).strip() for s in scope_filter}
    else:
        scope_allow = None

    headers = {
        "User-Agent": user_agent,
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Referer": get_exchange_url(),
    }

    results: list[dict[str, Any]] = []

    async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT, headers=headers) as client:
        # 1) Filter metadata (category id -> name map)
        category_map: dict[str, str] = {}
        try:
            logger.info("Fetching Exchange filter metadata: %s%s", api_base, initialize_path)
            init_resp = await client.get(api_base + initialize_path)
            init_resp.raise_for_status()
            category_map = _category_map(init_resp.json())
            logger.info("Loaded %d category names", len(category_map))
        except Exception as exc:  # noqa: BLE001 - metadata is best-effort
            logger.warning("Failed to load category metadata (continuing): %s", exc)

        if stop_event and stop_event.is_set():
            return results

        # 2) Every resource in a single request
        logger.info("Fetching Exchange resource list: %s%s", api_base, search_path)
        resp = await client.post(api_base + search_path, json={})
        resp.raise_for_status()
        raw_items = resp.json()

        if not isinstance(raw_items, list):
            logger.warning("Unexpected search response type: %s", type(raw_items).__name__)
            return results

        # Filter to the publicly-listed scopes (matches the website's count).
        if scope_allow is not None:
            filtered = [
                r for r in raw_items
                if str(r.get("scope_title", "")).strip() in scope_allow
            ]
        else:
            filtered = list(raw_items)

        logger.info(
            "Exchange returned %d resources (%d after scope filter %s)",
            len(raw_items), len(filtered), sorted(scope_allow) if scope_allow else "none",
        )

        if max_resources and max_resources > 0:
            filtered = filtered[:max_resources]

        total = len(filtered)

        # 3) Transform each into the toolbox schema
        for i, raw in enumerate(filtered):
            if stop_event and stop_event.is_set():
                logger.info("Stop requested, halting at %d/%d", i, total)
                break
            try:
                results.append(
                    transform_resource(raw, category_map, resource_url_template)
                )
            except Exception as exc:  # noqa: BLE001 - never lose the whole run over one row
                logger.warning("Failed to transform resource %s: %s", raw.get("id"), exc)

            if progress_callback:
                progress_callback(i + 1, total)

    logger.info("Scrape complete: %d resources", len(results))
    return results
