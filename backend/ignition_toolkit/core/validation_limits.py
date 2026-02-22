"""
Centralized validation limit constants.

All maximum lengths and count limits for input validation are defined here.
Import from this module instead of hardcoding magic numbers in validators.
"""


class ValidationLimits:
    """Maximum lengths and counts for API input validation."""

    # Parameter validation
    PARAMETER_COUNT_MAX: int = 50
    PARAMETER_NAME_MAX: int = 255
    PARAMETER_VALUE_MAX: int = 10000

    # URL and path validation
    GATEWAY_URL_MAX: int = 500
    PLAYBOOK_PATH_MAX: int = 500

    # Metadata validation
    PLAYBOOK_NAME_MAX: int = 200
    PLAYBOOK_DESCRIPTION_MAX: int = 2000
    TAG_MAX_LENGTH: int = 50
    TAG_COUNT_MAX: int = 20
