#!/usr/bin/env python3
"""
Backend entry point for Electron subprocess.

This script starts the FastAPI server with configuration from environment variables.
It's designed to be spawned by the Electron main process.
"""

import os
import sys
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

logger = logging.getLogger(__name__)


def main():
    """Start the FastAPI backend server."""
    import uvicorn

    # Get configuration from environment variables (set by Electron)
    host = os.environ.get("IGNITION_TOOLKIT_HOST", "127.0.0.1")
    port = int(os.environ.get("IGNITION_TOOLKIT_PORT", "5000"))

    # Data directory is set by Electron to app userData path
    data_dir = os.environ.get("IGNITION_TOOLKIT_DATA")
    if data_dir:
        logger.info(f"Using data directory: {data_dir}")

    logger.info(f"Starting Ignition Toolkit backend on {host}:{port}")

    # Configure CORS to allow the Electron app
    # The frontend will connect via the dynamic port
    allowed_origins = f"http://localhost:{port},http://127.0.0.1:{port},http://localhost:3000,http://127.0.0.1:3000"
    os.environ["ALLOWED_ORIGINS"] = allowed_origins

    try:
        uvicorn.run(
            "ignition_toolkit.api.app:app",
            host=host,
            port=port,
            log_level="info",
            reload=False,  # No reload in production
            workers=1,     # Single worker for subprocess
            access_log=True,
        )
    except KeyboardInterrupt:
        logger.info("Backend shutdown requested")
    except Exception as e:
        logger.error(f"Failed to start backend: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
