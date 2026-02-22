"""
Ignition Exchange scraper.

Visits inductiveautomation.com/exchange and collects resource listings.
Uses Playwright for page navigation and BeautifulSoup for HTML parsing.
"""

from __future__ import annotations

import logging
import re
import threading
from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)

EXCHANGE_URL = "https://inductiveautomation.com/exchange"


def format_version(v: Any) -> str:
    """Clean and format a version string."""
    if not v:
        return ""
    s = str(v).strip()
    # Remove 'v' prefix
    if s.lower().startswith("v"):
        s = s[1:]
    return s


def extract_resource_details(page_html: str, url: str) -> dict[str, Any]:
    """
    Extract resource details from a single exchange resource page HTML.

    Returns dict with: title, contributor, category, download_count, version,
    tagline, updated_date
    """
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(page_html, "lxml")

    # Extract title
    title = ""
    title_el = soup.find("h1") or soup.find("h2")
    if title_el:
        title = title_el.get_text(strip=True)

    # Try meta og:title as fallback
    if not title:
        og_title = soup.find("meta", property="og:title")
        if og_title:
            title = og_title.get("content", "").strip()

    # Extract tagline / description
    tagline = ""
    # Try meta description first
    meta_desc = soup.find("meta", attrs={"name": "description"})
    if meta_desc:
        tagline = meta_desc.get("content", "").strip()
    if not tagline:
        og_desc = soup.find("meta", property="og:description")
        if og_desc:
            tagline = og_desc.get("content", "").strip()

    # Extract contributor - look for "by <author>" pattern or specific element
    contributor = ""
    # Look for contributor/author elements
    for selector in [
        {"class": re.compile(r"contributor|author|creator", re.I)},
        {"itemprop": "author"},
    ]:
        el = soup.find(attrs=selector)
        if el:
            contributor = el.get_text(strip=True)
            # Clean "by " prefix
            if contributor.lower().startswith("by "):
                contributor = contributor[3:].strip()
            break

    # Extract category
    category = ""
    for selector in [
        {"class": re.compile(r"category|tag|type", re.I)},
        {"itemprop": "category"},
    ]:
        el = soup.find(attrs=selector)
        if el:
            category = el.get_text(strip=True)
            break

    # Extract download count
    download_count = 0
    for selector in [
        {"class": re.compile(r"download", re.I)},
        {"data-stat": "downloads"},
    ]:
        el = soup.find(attrs=selector)
        if el:
            text = el.get_text(strip=True)
            nums = re.findall(r"[\d,]+", text)
            if nums:
                try:
                    download_count = int(nums[0].replace(",", ""))
                    break
                except ValueError:
                    pass

    # Extract version
    version = ""
    for selector in [
        {"class": re.compile(r"version", re.I)},
        {"itemprop": "softwareVersion"},
    ]:
        el = soup.find(attrs=selector)
        if el:
            version = format_version(el.get_text(strip=True))
            break

    # Extract updated date
    updated_date = ""
    time_el = soup.find("time")
    if time_el:
        updated_date = time_el.get("datetime", "") or time_el.get_text(strip=True)

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
            logger.info("Loading Ignition Exchange listing: %s", EXCHANGE_URL)
            await page.goto(EXCHANGE_URL, wait_until="networkidle", timeout=60000)

            # Collect all resource links
            resource_links: list[str] = []
            # Look for links that point to individual exchange resources
            anchors = await page.query_selector_all("a[href*='/exchange/']")
            seen: set[str] = set()
            for anchor in anchors:
                href = await anchor.get_attribute("href")
                if not href:
                    continue
                # Make absolute
                if href.startswith("/"):
                    href = "https://inductiveautomation.com" + href
                # Filter: must be a resource detail page (has more path segments)
                if "/exchange/" in href and href != EXCHANGE_URL and href not in seen:
                    # Skip links that are just the exchange root or category pages
                    path = href.replace("https://inductiveautomation.com", "").rstrip("/")
                    parts = [seg for seg in path.split("/") if seg]
                    if len(parts) >= 3:  # e.g. /exchange/category/resource-name
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
