"""
Rate Limiting Middleware for FastAPI

Implements token bucket rate limiting to prevent DoS attacks and abuse.

SECURITY: Protects against:
- DoS attacks (too many requests)
- Brute force attacks
- Resource exhaustion
- API abuse

PORTABILITY v4: No external dependencies, uses only Python stdlib.
"""

import logging
import time
from collections import defaultdict

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)


class TokenBucket:
    """
    Token bucket algorithm for rate limiting

    Each client gets a bucket with a fixed capacity of tokens.
    Tokens are consumed on each request and refilled at a constant rate.
    """

    def __init__(self, capacity: int, refill_rate: float):
        """
        Initialize token bucket

        Args:
            capacity: Maximum number of tokens (burst size)
            refill_rate: Tokens added per second
        """
        self.capacity = capacity
        self.refill_rate = refill_rate
        self.tokens = capacity
        self.last_refill = time.monotonic()

    def consume(self, tokens: int = 1) -> bool:
        """
        Try to consume tokens

        Args:
            tokens: Number of tokens to consume (default: 1)

        Returns:
            True if tokens were available and consumed, False otherwise
        """
        # Refill tokens based on time passed
        now = time.monotonic()
        time_passed = now - self.last_refill
        self.tokens = min(
            self.capacity, self.tokens + time_passed * self.refill_rate
        )
        self.last_refill = now

        # Try to consume
        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        return False


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware using token bucket algorithm

    Different endpoints can have different rate limits.
    Clients are identified by IP address.

    Configuration:
    - Default: 60 requests/minute (1 req/sec)
    - Critical endpoints: 10 requests/minute
    - High-frequency endpoints: 120 requests/minute
    """

    def __init__(self, app):
        super().__init__(app)

        # Client buckets: {client_ip: {endpoint_pattern: TokenBucket}}
        self.buckets: dict[str, dict[str, TokenBucket]] = defaultdict(dict)

        # Cleanup: Remove stale buckets periodically
        self.last_cleanup = time.monotonic()
        self.cleanup_interval = 300  # 5 minutes

        # Rate limit configurations (capacity, refill_rate per second)
        # capacity = burst size, refill_rate = sustainable rate
        self.rate_limits = {
            # Critical endpoints (authentication, execution control)
            "critical": (30, 30 / 60),  # 30 req/min = 0.5 req/sec (increased from 10)
            # Normal endpoints (most APIs)
            "normal": (60, 60 / 60),  # 60 req/min = 1 req/sec
            # High-frequency endpoints (status polling, websocket handshake)
            "high": (120, 120 / 60),  # 120 req/min = 2 req/sec
        }

        # Endpoint patterns and their rate limit categories
        self.endpoint_categories = {
            # Critical - execution control
            "/api/executions": "critical",  # POST only
            "/api/credentials": "critical",
            # High-frequency - status polling
            "/api/executions/": "high",  # GET status endpoints
            "/health": "high",
            "/api/config": "high",
            # WebSocket handshake
            "/ws": "high",
            # Normal - everything else (default)
            "*": "normal",
        }

        logger.info("Rate limiting middleware initialized")

    def get_client_identifier(self, request: Request) -> str:
        """
        Get unique identifier for client

        Uses forwarded-for header if behind proxy, otherwise direct IP.

        Args:
            request: FastAPI request

        Returns:
            Client identifier (IP address)
        """
        # Check for forwarded IP (if behind proxy)
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()

        # Use direct client IP
        if request.client:
            return request.client.host

        return "unknown"

    def get_rate_limit_category(self, path: str, method: str) -> str:
        """
        Determine rate limit category for endpoint

        Args:
            path: Request path
            method: HTTP method

        Returns:
            Rate limit category (critical, normal, high)
        """
        # Execution POST is critical (start execution)
        if path == "/api/executions" and method == "POST":
            return "critical"

        # Execution DELETE is normal (not critical like POST)
        if path.startswith("/api/executions/") and method == "DELETE":
            return "normal"

        # Execution status GET is high-frequency
        if path.startswith("/api/executions/") and method == "GET":
            return "high"

        # Credentials POST/PUT are critical, GET is normal
        if path.startswith("/api/credentials") and method in ["POST", "PUT", "DELETE"]:
            return "critical"
        if path.startswith("/api/credentials") and method == "GET":
            return "normal"

        # Check other patterns
        for pattern, category in self.endpoint_categories.items():
            if pattern == "*":
                continue
            if path.startswith(pattern):
                return category

        # Default
        return "normal"

    def get_or_create_bucket(
        self, client_id: str, endpoint_category: str
    ) -> TokenBucket:
        """
        Get or create token bucket for client and endpoint

        Args:
            client_id: Client identifier
            endpoint_category: Rate limit category

        Returns:
            Token bucket for this client/endpoint combination
        """
        if endpoint_category not in self.buckets[client_id]:
            capacity, refill_rate = self.rate_limits[endpoint_category]
            self.buckets[client_id][endpoint_category] = TokenBucket(
                capacity, refill_rate
            )

        return self.buckets[client_id][endpoint_category]

    def cleanup_stale_buckets(self):
        """Remove buckets for clients that haven't made requests recently"""
        now = time.monotonic()
        if now - self.last_cleanup < self.cleanup_interval:
            return

        # Remove clients with no recent activity
        stale_clients = []
        for client_id, client_buckets in self.buckets.items():
            # Check if all buckets are full (no recent activity)
            all_full = all(
                bucket.tokens >= bucket.capacity * 0.99
                for bucket in client_buckets.values()
            )
            if all_full:
                stale_clients.append(client_id)

        for client_id in stale_clients:
            del self.buckets[client_id]

        if stale_clients:
            logger.debug(f"Cleaned up {len(stale_clients)} stale rate limit buckets")

        self.last_cleanup = now

    async def dispatch(self, request: Request, call_next):
        """
        Process request with rate limiting

        Args:
            request: FastAPI request
            call_next: Next middleware/handler

        Returns:
            Response (or 429 if rate limited)
        """
        # Skip rate limiting for static files and frontend routes
        if not request.url.path.startswith("/api") and not request.url.path.startswith(
            "/ws"
        ):
            return await call_next(request)

        # Cleanup periodically
        self.cleanup_stale_buckets()

        # Identify client
        client_id = self.get_client_identifier(request)

        # Determine rate limit category
        category = self.get_rate_limit_category(request.url.path, request.method)

        # Get or create bucket
        bucket = self.get_or_create_bucket(client_id, category)

        # Try to consume token
        if not bucket.consume():
            logger.warning(
                f"Rate limit exceeded for {client_id} on {request.url.path} ({category})"
            )
            return JSONResponse(
                status_code=429,
                content={
                    "error": "Too many requests",
                    "message": "Rate limit exceeded. Please try again later.",
                    "retry_after": 60,  # Suggest retry after 60 seconds
                },
                headers={"Retry-After": "60"},
            )

        # Process request
        response = await call_next(request)

        # Add rate limit headers
        capacity, refill_rate = self.rate_limits[category]
        remaining = int(bucket.tokens)

        response.headers["X-RateLimit-Limit"] = str(capacity)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(
            int(time.time() + (capacity - bucket.tokens) / refill_rate)
        )

        return response
