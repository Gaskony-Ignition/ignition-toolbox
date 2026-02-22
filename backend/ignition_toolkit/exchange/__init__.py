"""
Ignition Exchange scraper module.

Scrapes inductiveautomation.com/exchange to collect resource listings.
"""

from ignition_toolkit.exchange.service import ExchangeService

_instance: ExchangeService | None = None


def get_exchange_service() -> ExchangeService:
    """Get the singleton ExchangeService instance."""
    global _instance
    if _instance is None:
        _instance = ExchangeService()
    return _instance


__all__ = ["ExchangeService", "get_exchange_service"]
