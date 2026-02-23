"""
Ignition Exchange scraper.

Visits inductiveautomation.com/exchange and collects resource listings.
Uses Playwright for page navigation and BeautifulSoup for HTML parsing.

CSS selectors and field extraction patterns are loaded from selectors.json,
which can be updated remotely via RemoteDataManager without code changes.
"""

from __future__ import annotations

import logging
import re
import sys
import threading
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ignition_toolkit.core.remote_data import RemoteDataConfig, RemoteDataManager
from ignition_toolkit.core.remote_data_registry import RemoteDataRegistry

logger = logging.getLogger(__name__)

# Default fallback URL used when selectors config is unavailable
_DEFAULT_EXCHANGE_URL = "https://inductiveautomation.com/exchange"

# Module-level selector manager (lazy-initialized)
_selectors_manager: RemoteDataManager | None = None


def _get_selectors_path() -> Path:
    """Get path to bundled selectors.json, handling frozen (PyInstaller) mode."""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS) / "exchange" / "selectors.json"
    return Path(__file__).parent / "selectors.json"


def _get_selectors() -> dict:
    """Load selector configuration, initializing the manager on first call."""
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
    """Get the Exchange listing URL from config."""
    selectors = _get_selectors()
    return selectors.get("exchange_url", _DEFAULT_EXCHANGE_URL)


def format_version(v: Any) -> str:
    """Clean and format a version string."""
    if not v:
        return ""
    s = str(v).strip()
    # Remove 'v' prefix
    if s.lower().startswith("v"):
        s = s[1:]
    return s


def _find_by_config(soup: Any, field_config: dict) -> str:
    """
    Find an element using config-driven selectors.

    Tries strategies in order: class_patterns, itemprop, data_attr.
    Returns the element's text content or empty string.
    """
    # Try class patterns
    if "class_patterns" in field_config:
        pattern = "|".join(field_config["class_patterns"])
        el = soup.find(attrs={"class": re.compile(pattern, re.I)})
        if el:
            return el.get_text(strip=True)

    # Try itemprop
    if "itemprop" in field_config:
        el = soup.find(attrs={"itemprop": field_config["itemprop"]})
        if el:
            return el.get_text(strip=True)

    # Try data attribute
    if "data_attr" in field_config:
        el = soup.find(attrs={"data-stat": field_config["data_attr"]})
        if el:
            return el.get_text(strip=True)

    return ""


def extract_resource_details(page_html: str, url: str) -> dict[str, Any]:
    """
    Extract resource details from a single exchange resource page HTML.

    Returns dict with: title, contributor, category, download_count, version,
    tagline, updated_date
    """
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(page_html, "lxml")
    selectors = _get_selectors()
    resource_cfg = selectors.get("resource_page", {})

    # Extract title
    title = ""
    title_cfg = resource_cfg.get("title", {})
    for tag_name in title_cfg.get("primary", ["h1", "h2"]):
        title_el = soup.find(tag_name)
        if title_el:
            title = title_el.get_text(strip=True)
            break

    # Try meta og:title as fallback
    if not title:
        fallback_meta = title_cfg.get("fallback_meta", "og:title")
        og_title = soup.find("meta", property=fallback_meta)
        if og_title:
            title = og_title.get("content", "").strip()

    # Extract tagline / description
    tagline = ""
    tagline_cfg = resource_cfg.get("tagline", {})
    meta_name = tagline_cfg.get("meta_name", "description")
    meta_desc = soup.find("meta", attrs={"name": meta_name})
    if meta_desc:
        tagline = meta_desc.get("content", "").strip()
    if not tagline:
        fallback_meta = tagline_cfg.get("fallback_meta", "og:description")
        og_desc = soup.find("meta", property=fallback_meta)
        if og_desc:
            tagline = og_desc.get("content", "").strip()

    # Extract contributor - look for "by <author>" pattern or specific element
    contributor_cfg = resource_cfg.get("contributor", {})
    contributor = _find_by_config(soup, contributor_cfg)
    # Clean "by " prefix
    if contributor.lower().startswith("by "):
        contributor = contributor[3:].strip()

    # Extract category
    category_cfg = resource_cfg.get("category", {})
    category = _find_by_config(soup, category_cfg)

    # Extract download count
    download_count = 0
    download_cfg = resource_cfg.get("download_count", {})
    download_text = _find_by_config(soup, download_cfg)
    if download_text:
        nums = re.findall(r"[\d,]+", download_text)
        if nums:
            try:
                download_count = int(nums[0].replace(",", ""))
            except ValueError:
                pass

    # Extract version
    version_cfg = resource_cfg.get("version", {})
    version = format_version(_find_by_config(soup, version_cfg))

    # Extract updated date
    updated_date = ""
    date_cfg = resource_cfg.get("updated_date", {})
    date_element = date_cfg.get("element", "time")
    date_attr = date_cfg.get("attr", "datetime")
    time_el = soup.find(date_element)
    if time_el:
        updated_date = time_el.get(date_attr, "") or time_el.get_text(strip=True)

    # Generate a stable ID from the URL
    resource_id = url.rstrip("/").split("/")[-1]

    return {
        "id": resource_id,
        "url": url,
        "title": title,
        "contributor": contributor,
        "category": category,
        "download_count": download_count,
        "version": version,
        "updated_date": updated_date,
        "tagline": tagline,
        "scraped_at": datetime.now(timezone.utc).isoformat(),
    }


async def scrape_all(
    max_resources: int = 0,
    headless: bool = True,
    stop_event: threading.Event | None = None,
    progress_callback: Callable[[int, int], None] | None = None,
) -> list[dict[str, Any]]:
    """
    Scrape all resources from the Ignition Exchange.

    Args:
        max_resources: Maximum number of resources to scrape (0 = all)
        headless: Run browser in headless mode
        stop_event: Threading event to signal early stop
        progress_callback: Called with (current, total) after each resource

    Returns:
        List of resource dicts
    """
    from playwright.async_api import async_playwright

    selectors = _get_selectors()
    listing_cfg = selectors.get("listing_page", {})
    exchange_url = get_exchange_url()
    link_selector = listing_cfg.get("resource_link_selector", "a[href*='/exchange/']")
    min_segments = listing_cfg.get("min_path_segments", 3)

    results: list[dict[str, Any]] = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless)
        try:
            context = await browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                )
            )
            page = await context.new_page()

            # Load the exchange listing page
            logger.info("Loading Ignition Exchange listing: %s", exchange_url)
            await page.goto(exchange_url, wait_until="networkidle", timeout=60000)

            # Collect all resource links
            resource_links: list[str] = []
            # Look for links that point to individual exchange resources
            anchors = await page.query_selector_all(link_selector)
            seen: set[str] = set()
            for anchor in anchors:
                href = await anchor.get_attribute("href")
                if not href:
                    continue
                # Make absolute
                if href.startswith("/"):
                    href = "https://inductiveautomation.com" + href
                # Filter: must be a resource detail page (has more path segments)
                if "/exchange/" in href and href != exchange_url and href not in seen:
                    # Skip links that are just the exchange root or category pages
                    path = href.replace("https://inductiveautomation.com", "").rstrip("/")
                    parts = [seg for seg in path.split("/") if seg]
                    if len(parts) >= min_segments:  # e.g. /exchange/category/resource-name
                        seen.add(href)
                        resource_links.append(href)

            if not resource_links:
                logger.warning("No resource links found on exchange listing page")
                return results

            total = len(resource_links)
            if max_resources and max_resources > 0:
                resource_links = resource_links[:max_resources]
                total = len(resource_links)

            logger.info("Found %d resources to scrape", total)

            for i, url in enumerate(resource_links):
                if stop_event and stop_event.is_set():
                    logger.info("Stop requested, halting scrape at %d/%d", i, total)
                    break

                try:
                    await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                    html = await page.content()
                    details = extract_resource_details(html, url)
                    results.append(details)
                    logger.debug("Scraped %d/%d: %s", i + 1, total, details.get("title", url))
                except Exception as exc:
                    logger.warning("Failed to scrape %s: %s", url, exc)
                    # Include a minimal entry so we don't lose track of the URL
                    results.append({
                        "id": url.rstrip("/").split("/")[-1],
                        "url": url,
                        "title": "",
                        "contributor": "",
                        "category": "",
                        "download_count": 0,
                        "version": "",
                        "updated_date": "",
                        "tagline": "",
                        "scraped_at": datetime.now(timezone.utc).isoformat(),
                    })

                if progress_callback:
                    progress_callback(i + 1, total)

        finally:
            await browser.close()

    return results
