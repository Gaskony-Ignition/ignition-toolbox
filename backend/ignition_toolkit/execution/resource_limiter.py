"""
Resource Limiter - Manages shared resources for parallel executions

Prevents resource exhaustion by limiting concurrent access to:
- Browser instances
- Gateway connections
- Memory-intensive operations
"""

import asyncio
import logging
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class ResourceType(Enum):
    """Types of shared resources"""
    BROWSER = "browser"
    GATEWAY = "gateway"
    MEMORY = "memory"
    CPU = "cpu"


class ResourceLimiter:
    """
    Limits concurrent access to shared resources

    Uses semaphores to control access to different resource types,
    preventing resource exhaustion during parallel execution.

    Example:
        limiter = ResourceLimiter(browser_limit=3, gateway_limit=5)

        async with limiter.acquire_context(ResourceType.BROWSER):
            # Use browser
            pass
    """

    def __init__(
        self,
        browser_limit: int = 3,
        gateway_limit: int = 10,
        memory_limit: int = 5,
        cpu_limit: int = 4,
    ):
        """
        Initialize resource limiter

        Args:
            browser_limit: Max concurrent browser instances
            gateway_limit: Max concurrent gateway connections
            memory_limit: Max concurrent memory-intensive operations
            cpu_limit: Max concurrent CPU-intensive operations
        """
        self._limits = {
            ResourceType.BROWSER: browser_limit,
            ResourceType.GATEWAY: gateway_limit,
            ResourceType.MEMORY: memory_limit,
            ResourceType.CPU: cpu_limit,
        }

        self._semaphores = {
            resource_type: asyncio.Semaphore(limit)
            for resource_type, limit in self._limits.items()
        }

        self._acquired_counts = {
            resource_type: 0
            for resource_type in ResourceType
        }

        self._lock = asyncio.Lock()

        logger.info(f"ResourceLimiter initialized: {self._limits}")

    async def acquire(self, resource_type: ResourceType, timeout: float | None = None) -> bool:
        """
        Acquire a resource

        Args:
            resource_type: Type of resource to acquire
            timeout: Optional timeout in seconds

        Returns:
            True if acquired, False if timeout

        Raises:
            asyncio.TimeoutError if timeout specified and exceeded
        """
        semaphore = self._semaphores.get(resource_type)
        if not semaphore:
            return True  # Unknown resource type, allow

        try:
            if timeout:
                await asyncio.wait_for(semaphore.acquire(), timeout=timeout)
            else:
                await semaphore.acquire()

            async with self._lock:
                self._acquired_counts[resource_type] += 1

            logger.debug(f"Acquired {resource_type.value} resource")
            return True

        except asyncio.TimeoutError:
            logger.warning(f"Timeout acquiring {resource_type.value} resource")
            return False

    def release(self, resource_type: ResourceType) -> None:
        """
        Release a resource

        Args:
            resource_type: Type of resource to release
        """
        semaphore = self._semaphores.get(resource_type)
        if semaphore:
            semaphore.release()
            # Note: We don't decrement _acquired_counts here because
            # the semaphore handles the actual limiting
            logger.debug(f"Released {resource_type.value} resource")

    async def acquire_context(self, resource_type: ResourceType):
        """
        Context manager for resource acquisition

        Usage:
            async with limiter.acquire_context(ResourceType.BROWSER):
                # Use browser
                pass
        """
        return _ResourceContext(self, resource_type)

    def get_available(self, resource_type: ResourceType) -> int:
        """
        Get available count for a resource type

        Args:
            resource_type: Type of resource

        Returns:
            Number of available resources
        """
        semaphore = self._semaphores.get(resource_type)
        if not semaphore:
            return 0

        # Semaphore._value gives available count
        return semaphore._value

    def get_limit(self, resource_type: ResourceType) -> int:
        """Get limit for a resource type"""
        return self._limits.get(resource_type, 0)

    def get_in_use(self, resource_type: ResourceType) -> int:
        """Get count of resources currently in use"""
        limit = self.get_limit(resource_type)
        available = self.get_available(resource_type)
        return limit - available

    def get_status(self) -> dict[str, Any]:
        """
        Get status of all resources

        Returns:
            Dictionary with resource status
        """
        return {
            resource_type.value: {
                "limit": self.get_limit(resource_type),
                "available": self.get_available(resource_type),
                "in_use": self.get_in_use(resource_type),
            }
            for resource_type in ResourceType
        }

    def set_limit(self, resource_type: ResourceType, new_limit: int) -> None:
        """
        Update limit for a resource type

        Note: This creates a new semaphore, so existing acquisitions
        are not affected.

        Args:
            resource_type: Type of resource
            new_limit: New limit value
        """
        if new_limit < 1:
            raise ValueError("Limit must be at least 1")

        self._limits[resource_type] = new_limit
        self._semaphores[resource_type] = asyncio.Semaphore(new_limit)
        logger.info(f"Updated {resource_type.value} limit to {new_limit}")


class _ResourceContext:
    """Async context manager for resource acquisition"""

    def __init__(self, limiter: ResourceLimiter, resource_type: ResourceType):
        self.limiter = limiter
        self.resource_type = resource_type

    async def __aenter__(self):
        await self.limiter.acquire(self.resource_type)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self.limiter.release(self.resource_type)
        return False


# Global instance
_resource_limiter: ResourceLimiter | None = None


def get_resource_limiter() -> ResourceLimiter:
    """Get the global resource limiter"""
    global _resource_limiter
    if _resource_limiter is None:
        _resource_limiter = ResourceLimiter()
    return _resource_limiter
