"""
AI Client - Unified interface for AI-powered verification

Supports multiple AI providers with a common interface.
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class VerificationStatus(str, Enum):
    """Status of AI verification"""

    PASSED = "passed"
    FAILED = "failed"
    UNCERTAIN = "uncertain"
    ERROR = "error"


@dataclass
class VerificationResult:
    """Result of AI visual verification"""

    status: VerificationStatus
    confidence: float  # 0.0 to 1.0
    passed: bool
    explanation: str
    details: dict[str, Any] = field(default_factory=dict)
    raw_response: str | None = None


class AIProvider(ABC):
    """Abstract base class for AI providers"""

    @abstractmethod
    async def verify_screenshot(
        self,
        screenshot_base64: str,
        prompt: str,
        confidence_threshold: float = 0.8,
    ) -> VerificationResult:
        """
        Verify a screenshot against a prompt using AI vision.

        Args:
            screenshot_base64: Base64-encoded screenshot image
            prompt: Verification prompt describing what to check
            confidence_threshold: Minimum confidence to pass (0.0-1.0)

        Returns:
            VerificationResult with status, confidence, and explanation
        """
        pass

    @abstractmethod
    async def analyze_screenshot(
        self,
        screenshot_base64: str,
        prompt: str,
    ) -> dict[str, Any]:
        """
        Analyze a screenshot with a custom prompt.

        Args:
            screenshot_base64: Base64-encoded screenshot image
            prompt: Analysis prompt

        Returns:
            Dictionary with analysis results
        """
        pass


class AIClient:
    """
    Unified AI client that delegates to provider implementations.

    Example:
        client = AIClient(provider=AnthropicProvider(api_key="..."))
        result = await client.verify_screenshot(
            screenshot_base64="...",
            prompt="Verify the login form is visible",
            confidence_threshold=0.85
        )
    """

    def __init__(self, provider: AIProvider):
        """
        Initialize AI client with a provider.

        Args:
            provider: AI provider implementation (e.g., AnthropicProvider)
        """
        self.provider = provider

    async def verify_screenshot(
        self,
        screenshot_base64: str,
        prompt: str,
        confidence_threshold: float = 0.8,
    ) -> VerificationResult:
        """
        Verify a screenshot using AI vision.

        Args:
            screenshot_base64: Base64-encoded screenshot image
            prompt: Verification prompt describing what to check
            confidence_threshold: Minimum confidence to pass (0.0-1.0)

        Returns:
            VerificationResult with status, confidence, and explanation
        """
        logger.info(f"Verifying screenshot with prompt: {prompt[:100]}...")
        return await self.provider.verify_screenshot(
            screenshot_base64=screenshot_base64,
            prompt=prompt,
            confidence_threshold=confidence_threshold,
        )

    async def analyze_screenshot(
        self,
        screenshot_base64: str,
        prompt: str,
    ) -> dict[str, Any]:
        """
        Analyze a screenshot with a custom prompt.

        Args:
            screenshot_base64: Base64-encoded screenshot image
            prompt: Analysis prompt

        Returns:
            Dictionary with analysis results
        """
        logger.info(f"Analyzing screenshot with prompt: {prompt[:100]}...")
        return await self.provider.analyze_screenshot(
            screenshot_base64=screenshot_base64,
            prompt=prompt,
        )
