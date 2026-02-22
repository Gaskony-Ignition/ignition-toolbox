"""
API Key Authentication Middleware

Provides API key-based authentication for production deployment.
For localhost-only use, authentication can be disabled via environment variable.
"""

import hmac
import logging
import os
import secrets
from pathlib import Path

from fastapi import Header, HTTPException, Request
from fastapi.security import APIKeyHeader

logger = logging.getLogger(__name__)

# API key configuration
API_KEY_HEADER = "X-API-Key"
api_key_scheme = APIKeyHeader(name=API_KEY_HEADER, auto_error=False)


def _get_api_key_file() -> Path:
    """Get the path to the API key file using the correct data directory."""
    from ignition_toolkit.config import get_toolkit_data_dir
    return get_toolkit_data_dir() / "api.key"


def get_or_generate_api_key() -> str:
    """
    Get existing API key or generate a new one.

    API key is stored in the toolkit data directory.
    If the file doesn't exist, a new secure key is generated.

    Returns:
        str: The API key
    """
    # Check environment variable first (for testing/development)
    env_key = os.getenv("IGNITION_TOOLKIT_API_KEY")
    if env_key:
        return env_key

    api_key_file = _get_api_key_file()

    # Try to load existing key from file
    if api_key_file.exists():
        try:
            api_key = api_key_file.read_text(encoding='utf-8').strip()
            if api_key:
                return api_key
        except OSError:
            pass  # Will generate new key below

    # Generate new secure API key
    api_key = secrets.token_urlsafe(32)

    # Save to file with restricted permissions
    try:
        api_key_file.parent.mkdir(parents=True, exist_ok=True)
        api_key_file.write_text(api_key, encoding='utf-8')
        api_key_file.chmod(0o600)  # Owner read/write only
    except Exception as e:
        # Log warning but continue (key still works from memory)
        logger.warning(f"Could not save API key to {api_key_file}: {e}")

    return api_key


# Get or generate the API key at startup
API_KEY = get_or_generate_api_key()


def is_auth_required() -> bool:
    """
    Check if authentication is required.

    Authentication can be disabled for localhost-only deployments
    by setting DISABLE_API_AUTH=true in environment.

    Returns:
        bool: True if authentication is required
    """
    disable_auth = os.getenv("DISABLE_API_AUTH", "false").lower() in ("true", "1", "yes")
    return not disable_auth


async def verify_api_key(api_key: str | None = Header(None, alias=API_KEY_HEADER)) -> str:
    """
    Verify API key from request header.

    Args:
        api_key: API key from X-API-Key header

    Returns:
        str: The verified API key

    Raises:
        HTTPException: If API key is missing or invalid
    """
    # Skip authentication if disabled (localhost-only mode)
    if not is_auth_required():
        return "localhost"

    # Check for missing API key
    if not api_key:
        raise HTTPException(
            status_code=401,
            detail="Missing API key. Include X-API-Key header in request.",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    # Verify API key using constant-time comparison to prevent timing attacks
    if not hmac.compare_digest(api_key, API_KEY):
        raise HTTPException(
            status_code=403,
            detail="Invalid API key",
        )

    return api_key


async def localhost_only(request: Request):
    """
    Middleware to restrict access to localhost only.

    This provides a lightweight security layer for desktop deployments
    where you want to allow unauthenticated access but only from localhost.

    Args:
        request: FastAPI Request object

    Raises:
        HTTPException: If request is not from localhost
    """
    if not request.client:
        raise HTTPException(status_code=403, detail="Cannot determine client address")

    client_host = request.client.host
    allowed_hosts = ["127.0.0.1", "::1", "localhost"]

    if client_host not in allowed_hosts:
        raise HTTPException(
            status_code=403,
            detail=f"Access denied. This API is restricted to localhost only. Your IP: {client_host}",
        )


def print_api_key_info():
    """
    Print API key information at startup.

    This helps users understand how to authenticate and where the key is stored.
    SECURITY: API key is redacted in output to prevent exposure in logs.
    """
    if not is_auth_required():
        print("\n" + "=" * 70)
        print("[WARN] API AUTHENTICATION DISABLED")
        print("=" * 70)
        print("Authentication is disabled (DISABLE_API_AUTH=true)")
        print("This is ONLY safe for localhost-only deployments!")
        print("For network deployment, set DISABLE_API_AUTH=false")
        print("=" * 70 + "\n")
    else:
        # SECURITY: Redact API key - show only last 8 characters
        if len(API_KEY) > 8:
            redacted_key = "*" * (len(API_KEY) - 8) + API_KEY[-8:]
        else:
            redacted_key = "********"

        api_key_file = _get_api_key_file()
        print("\n" + "=" * 70)
        print("[AUTH] API AUTHENTICATION ENABLED")
        print("=" * 70)
        print(f"API Key: {redacted_key} (redacted for security)")
        print(f"Stored in: {api_key_file}")
        print("")
        print("Include this key in all API requests:")
        print('  X-API-Key: <your-key>')
        print("")
        print("Example:")
        print('  curl -H "X-API-Key: <your-key>" http://localhost:5000/api/playbooks')
        print("")
        print("To view full API key:")
        print(f"  cat {api_key_file}")
        print("=" * 70 + "\n")
