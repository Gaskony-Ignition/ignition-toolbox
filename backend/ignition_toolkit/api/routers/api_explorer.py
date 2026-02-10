"""
API Explorer routes

Provides endpoints for exploring Ignition Gateway REST APIs,
managing API keys, and executing raw API requests.
"""

import logging
from typing import Any

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ignition_toolkit.api.services.api_key_service import APIKeyService

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/explorer", tags=["api-explorer"])

# HTTP client configuration
HTTP_TIMEOUT = 30.0


# ============================================================================
# Pydantic Models
# ============================================================================


class APIKeyInfo(BaseModel):
    """API key information (without exposing the key)"""

    id: int
    name: str
    gateway_url: str
    has_api_key: bool
    description: str | None = None
    created_at: str | None = None
    last_used: str | None = None


class APIKeyCreate(BaseModel):
    """API key creation request"""

    name: str = Field(..., min_length=1, max_length=255)
    gateway_url: str = Field(..., min_length=1, max_length=500)
    api_key: str = Field(..., min_length=1)
    description: str | None = None


class APIKeyUpdate(BaseModel):
    """API key update request"""

    gateway_url: str | None = None
    api_key: str | None = None
    description: str | None = None


class GatewayRequest(BaseModel):
    """Request parameters for gateway operations"""

    gateway_url: str
    api_key_name: str | None = None
    api_key: str | None = None  # Direct API key (for quick testing)


class RawAPIRequest(BaseModel):
    """Raw API request to proxy to gateway"""

    gateway_url: str
    method: str = "GET"
    path: str
    headers: dict[str, str] | None = None
    query_params: dict[str, str] | None = None
    body: Any | None = None
    api_key_name: str | None = None
    api_key: str | None = None


class ScanRequest(BaseModel):
    """Request to trigger a gateway scan"""

    gateway_url: str
    api_key_name: str | None = None
    api_key: str | None = None


# ============================================================================
# Helper Functions
# ============================================================================


def _get_api_key(api_key_name: str | None, api_key: str | None) -> str | None:
    """
    Get API key from either name lookup or direct value

    Args:
        api_key_name: Name of stored API key
        api_key: Direct API key value

    Returns:
        API key string or None
    """
    if api_key:
        return api_key

    if api_key_name:
        service = APIKeyService()
        key = service.get_decrypted_key(api_key_name)
        if key:
            service.update_last_used(api_key_name)
        return key

    return None


def _normalize_gateway_url(url: str) -> str:
    """Normalize gateway URL to consistent format"""
    url = url.rstrip("/")
    if not url.startswith(("http://", "https://")):
        url = f"http://{url}"
    return url


def _is_http(gateway_url: str) -> bool:
    """Check if the gateway URL uses plain HTTP (not HTTPS)"""
    normalized = _normalize_gateway_url(gateway_url)
    return normalized.startswith("http://")


async def _make_gateway_request(
    gateway_url: str,
    path: str,
    method: str = "GET",
    api_key: str | None = None,
    headers: dict[str, str] | None = None,
    query_params: dict[str, str] | None = None,
    body: Any | None = None,
    retry_without_key_on_http: bool = True,
) -> dict:
    """
    Make a request to the Ignition Gateway API

    When URL is HTTP and API key auth fails (401/403), automatically retries
    without the API key header since API key auth requires HTTPS on Ignition 8.3.

    Args:
        gateway_url: Base gateway URL
        path: API path (e.g., /data/api/v1/gateway-info)
        method: HTTP method
        api_key: API key for authentication
        headers: Additional headers
        query_params: Query parameters
        body: Request body
        retry_without_key_on_http: If True and URL is HTTP, retry without API key on 401/403

    Returns:
        Response data dict with status, headers, and body
    """
    url = f"{_normalize_gateway_url(gateway_url)}{path}"

    # Build headers
    req_headers = headers.copy() if headers else {}
    if api_key:
        req_headers["X-Ignition-API-Token"] = api_key
    req_headers.setdefault("Accept", "application/json")

    try:
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT, verify=False) as client:
            response = await client.request(
                method=method.upper(),
                url=url,
                headers=req_headers,
                params=query_params,
                json=body if body and method.upper() in ("POST", "PUT", "PATCH") else None,
            )

            # If HTTP + API key auth failed, retry without the API key
            if (
                retry_without_key_on_http
                and api_key
                and _is_http(gateway_url)
                and response.status_code in (401, 403)
            ):
                logger.info(
                    f"API key auth failed over HTTP (status {response.status_code}), "
                    f"retrying without API key: {path}"
                )
                retry_headers = req_headers.copy()
                retry_headers.pop("X-Ignition-API-Token", None)
                response = await client.request(
                    method=method.upper(),
                    url=url,
                    headers=retry_headers,
                    params=query_params,
                    json=body if body and method.upper() in ("POST", "PUT", "PATCH") else None,
                )

            # Try to parse JSON response
            try:
                body_data = response.json()
            except (ValueError, TypeError):
                body_data = response.text

            return {
                "status_code": response.status_code,
                "headers": dict(response.headers),
                "body": body_data,
                "url": str(response.url),
            }

    except httpx.ConnectError as e:
        raise HTTPException(
            status_code=502,
            detail=f"Cannot connect to gateway: {gateway_url}. Error: {str(e)}",
        )
    except httpx.TimeoutException:
        raise HTTPException(
            status_code=504,
            detail=f"Gateway request timed out: {gateway_url}",
        )
    except Exception as e:
        logger.exception(f"Gateway request failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# API Key Routes
# ============================================================================


@router.get("/api-keys", response_model=list[APIKeyInfo])
async def list_api_keys():
    """List all stored API keys (without exposing key values)"""
    try:
        service = APIKeyService()
        return service.list_api_keys()
    except Exception as e:
        logger.exception(f"Error listing API keys: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api-keys", response_model=APIKeyInfo)
async def create_api_key(request: APIKeyCreate):
    """Create a new API key entry"""
    try:
        service = APIKeyService()
        return service.create_api_key(
            name=request.name,
            gateway_url=_normalize_gateway_url(request.gateway_url),
            api_key=request.api_key,
            description=request.description,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception(f"Error creating API key: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/api-keys/{name}", response_model=APIKeyInfo)
async def update_api_key(name: str, request: APIKeyUpdate):
    """Update an existing API key"""
    try:
        service = APIKeyService()
        gateway_url = (
            _normalize_gateway_url(request.gateway_url)
            if request.gateway_url
            else None
        )
        return service.update_api_key(
            name=name,
            gateway_url=gateway_url,
            api_key=request.api_key,
            description=request.description,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.exception(f"Error updating API key: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/api-keys/{name}")
async def delete_api_key(name: str):
    """Delete an API key"""
    try:
        service = APIKeyService()
        success = service.delete_api_key(name)
        if not success:
            raise HTTPException(status_code=404, detail=f"API key '{name}' not found")
        return {"message": "API key deleted successfully", "name": name}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error deleting API key: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Gateway Discovery Routes
# ============================================================================


@router.post("/openapi")
async def fetch_openapi_spec(request: GatewayRequest):
    """
    Fetch OpenAPI specification from gateway

    Returns the OpenAPI spec for the Ignition REST API
    """
    api_key = _get_api_key(request.api_key_name, request.api_key)

    # Try common OpenAPI spec paths (Ignition 8.3 serves at /openapi.json)
    paths_to_try = [
        "/openapi.json",
        "/openapi",
    ]

    for path in paths_to_try:
        try:
            response = await _make_gateway_request(
                gateway_url=request.gateway_url,
                path=path,
                api_key=api_key,
            )
            if response["status_code"] == 200:
                return response["body"]
        except HTTPException:
            continue

    raise HTTPException(
        status_code=404,
        detail="OpenAPI specification not found on gateway",
    )


@router.post("/gateway-info")
async def get_gateway_info(request: GatewayRequest):
    """
    Get gateway system information

    Uses Ignition 8.3 REST API endpoints to gather system info.
    Falls back to legacy /system/gwinfo for basic info.

    When URL is HTTP, uses legacy /system/gwinfo as primary source
    since API key authentication requires HTTPS.
    """
    api_key = _get_api_key(request.api_key_name, request.api_key)
    is_http = _is_http(request.gateway_url)

    info: dict[str, Any] = {}

    # For HTTP connections, use legacy endpoint as primary (no auth required)
    if is_http:
        logger.info("HTTP connection detected, using legacy /system/gwinfo as primary")
        try:
            legacy = await _make_gateway_request(
                gateway_url=request.gateway_url,
                path="/system/gwinfo",
                retry_without_key_on_http=False,
            )
            if legacy["status_code"] == 200:
                text = legacy["body"] if isinstance(legacy["body"], str) else ""
                parsed = {}
                for pair in text.split(";"):
                    if "=" in pair:
                        k, v = pair.split("=", 1)
                        parsed[k] = v
                info["system"] = {
                    "version": parsed.get("Version", "Unknown"),
                    "edition": parsed.get("PlatformEdition", ""),
                    "state": parsed.get("ContextStatus", ""),
                    "platformName": parsed.get("PlatformName", ""),
                }
                info["http_info"] = (
                    "Connected over HTTP. API key authentication requires HTTPS. "
                    "Using session-based fallback for gateway info."
                )
        except Exception as e:
            logger.warning(f"Could not get legacy gwinfo over HTTP: {e}")

    # Get gateway info (Ignition 8.3 API) - primary for HTTPS, secondary for HTTP
    if not info.get("system"):
        try:
            gw_info = await _make_gateway_request(
                gateway_url=request.gateway_url,
                path="/data/api/v1/gateway-info",
                api_key=api_key,
            )
            if gw_info["status_code"] == 200:
                body = gw_info["body"]
                info["system"] = body
        except Exception as e:
            logger.warning(f"Could not get gateway-info: {e}")

    # Fallback to legacy /system/gwinfo (no auth required) for HTTPS that failed
    if not info.get("system"):
        try:
            legacy = await _make_gateway_request(
                gateway_url=request.gateway_url,
                path="/system/gwinfo",
                retry_without_key_on_http=False,
            )
            if legacy["status_code"] == 200:
                text = legacy["body"] if isinstance(legacy["body"], str) else ""
                parsed = {}
                for pair in text.split(";"):
                    if "=" in pair:
                        k, v = pair.split("=", 1)
                        parsed[k] = v
                info["system"] = {
                    "version": parsed.get("Version", "Unknown"),
                    "edition": parsed.get("PlatformEdition", ""),
                    "state": parsed.get("ContextStatus", ""),
                    "platformName": parsed.get("PlatformName", ""),
                }
        except Exception as e:
            logger.warning(f"Could not get legacy gwinfo: {e}")
            info["system"] = None

    # Get overview (connections, problems)
    try:
        overview = await _make_gateway_request(
            gateway_url=request.gateway_url,
            path="/data/api/v1/overview",
            api_key=api_key,
        )
        if overview["status_code"] == 200:
            info["overview"] = overview["body"]
    except Exception as e:
        logger.warning(f"Could not get overview: {e}")

    # Get module health
    try:
        modules_info = await _make_gateway_request(
            gateway_url=request.gateway_url,
            path="/data/api/v1/modules/healthy",
            api_key=api_key,
        )
        if modules_info["status_code"] == 200:
            info["modules"] = modules_info["body"]
    except Exception as e:
        logger.warning(f"Could not get modules: {e}")
        info["modules"] = None

    # Get license info
    try:
        license_info = await _make_gateway_request(
            gateway_url=request.gateway_url,
            path="/data/api/v1/licenses",
            api_key=api_key,
        )
        if license_info["status_code"] == 200:
            info["license"] = license_info["body"]
    except Exception as e:
        logger.warning(f"Could not get license: {e}")
        info["license"] = None

    # Get trial info
    try:
        trial_info = await _make_gateway_request(
            gateway_url=request.gateway_url,
            path="/data/api/v1/trial",
            api_key=api_key,
        )
        if trial_info["status_code"] == 200:
            info["trial"] = trial_info["body"]
    except Exception as e:
        logger.warning(f"Could not get trial info: {e}")

    return info


@router.post("/resources/{resource_type}")
async def list_resources(resource_type: str, request: GatewayRequest):
    """
    List gateway resources by type

    Supported types:
    - databases: Database connections
    - opc: OPC-UA connections
    - tags: Tag providers
    - projects: Perspective/Vision projects
    - devices: Device connections
    """
    api_key = _get_api_key(request.api_key_name, request.api_key)

    # Map resource types to Ignition 8.3 API paths
    resource_paths = {
        "databases": "/data/api/v1/resources/list/ignition/database-connection",
        "opc": "/data/api/v1/resources/list/ignition/opc-connection",
        "tags": "/data/api/v1/resources/list/ignition/tag-provider",
        "projects": "/data/api/v1/projects/list",
        "devices": "/data/api/v1/resources/list/com.inductiveautomation.opcua/device",
        "users": "/data/api/v1/resources/list/ignition/user-source",
        "schedules": "/data/api/v1/resources/list/ignition/schedule",
        "alarm-journals": "/data/api/v1/resources/list/ignition/alarm-journal",
        "email-profiles": "/data/api/v1/resources/list/ignition/email-profile",
        "audit-profiles": "/data/api/v1/resources/list/ignition/audit-profile",
    }

    if resource_type not in resource_paths:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown resource type: {resource_type}. "
            f"Supported types: {', '.join(resource_paths.keys())}",
        )

    response = await _make_gateway_request(
        gateway_url=request.gateway_url,
        path=resource_paths[resource_type],
        api_key=api_key,
    )

    return response


# ============================================================================
# Raw Request Execution
# ============================================================================


@router.post("/request")
async def execute_raw_request(request: RawAPIRequest):
    """
    Execute a raw API request against the gateway

    This is a proxy endpoint that forwards requests to the gateway
    with proper authentication headers.
    """
    api_key = _get_api_key(request.api_key_name, request.api_key)

    response = await _make_gateway_request(
        gateway_url=request.gateway_url,
        path=request.path,
        method=request.method,
        api_key=api_key,
        headers=request.headers,
        query_params=request.query_params,
        body=request.body,
    )

    return response


# ============================================================================
# Gateway Actions
# ============================================================================


@router.post("/scan/projects")
async def scan_projects(request: ScanRequest):
    """
    Trigger a project resource scan on the gateway

    This is useful after making changes to project files
    """
    api_key = _get_api_key(request.api_key_name, request.api_key)

    response = await _make_gateway_request(
        gateway_url=request.gateway_url,
        path="/data/api/v1/scan/projects",
        method="POST",
        api_key=api_key,
    )

    if response["status_code"] not in (200, 204):
        raise HTTPException(
            status_code=response["status_code"],
            detail=f"Project scan failed: {response.get('body', 'Unknown error')}",
        )

    return {"message": "Project scan triggered successfully"}


@router.post("/scan/config")
async def scan_config(request: ScanRequest):
    """
    Trigger a configuration scan on the gateway

    This refreshes gateway configuration from disk
    """
    api_key = _get_api_key(request.api_key_name, request.api_key)

    response = await _make_gateway_request(
        gateway_url=request.gateway_url,
        path="/data/api/v1/scan/config",
        method="POST",
        api_key=api_key,
    )

    if response["status_code"] not in (200, 204):
        raise HTTPException(
            status_code=response["status_code"],
            detail=f"Config scan failed: {response.get('body', 'Unknown error')}",
        )

    return {"message": "Configuration scan triggered successfully"}


# ============================================================================
# Connection Test
# ============================================================================


@router.post("/test-connection")
async def test_gateway_connection(request: GatewayRequest):
    """
    Test connection to a gateway

    Verifies the gateway is reachable and API key is valid.
    For HTTP connections, falls back to legacy /system/gwinfo when
    API key auth fails (since API keys require HTTPS on Ignition 8.3).
    """
    api_key = _get_api_key(request.api_key_name, request.api_key)
    is_http = _is_http(request.gateway_url)

    try:
        response = await _make_gateway_request(
            gateway_url=request.gateway_url,
            path="/data/api/v1/gateway-info",
            api_key=api_key,
            retry_without_key_on_http=False,  # We handle fallback manually here
        )

        if response["status_code"] == 200:
            body = response["body"]
            version = body.get("version", "Unknown") if isinstance(body, dict) else "Unknown"
            return {
                "success": True,
                "message": "Connection successful",
                "gateway_version": version,
            }
        elif response["status_code"] in (401, 403) and is_http:
            # HTTP connection with auth failure - try legacy fallback
            try:
                legacy = await _make_gateway_request(
                    gateway_url=request.gateway_url,
                    path="/system/gwinfo",
                    retry_without_key_on_http=False,
                )
                if legacy["status_code"] == 200:
                    text = legacy["body"] if isinstance(legacy["body"], str) else ""
                    parsed = {}
                    for pair in text.split(";"):
                        if "=" in pair:
                            k, v = pair.split("=", 1)
                            parsed[k] = v
                    version = parsed.get("Version", "Unknown")
                    return {
                        "success": True,
                        "message": (
                            "Gateway reachable. API key authentication requires "
                            "HTTPS - using session fallback."
                        ),
                        "gateway_version": version,
                        "is_http": True,
                    }
            except Exception:
                pass
            # Legacy fallback also failed
            return {
                "success": False,
                "message": (
                    "API key authentication failed over HTTP. "
                    "API keys require HTTPS on Ignition 8.3. "
                    "Switch to HTTPS or use session-based access."
                ),
                "is_http": True,
            }
        elif response["status_code"] == 401:
            return {
                "success": False,
                "message": "API key invalid or expired.",
            }
        elif response["status_code"] == 403:
            return {
                "success": False,
                "message": "Access denied - API key may lack required permissions.",
            }
        else:
            return {
                "success": False,
                "message": f"Unexpected response: HTTP {response['status_code']}",
            }

    except HTTPException as e:
        return {
            "success": False,
            "message": e.detail,
        }
