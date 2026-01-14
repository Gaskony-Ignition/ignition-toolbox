"""
Credential Manager Service

Handles credential autofill logic for playbook execution.
Replaces duplicate helper functions from executions.py.
"""

import logging

from fastapi import HTTPException

from ignition_toolkit.credentials import Credential, CredentialVault
from ignition_toolkit.playbook.models import Playbook

logger = logging.getLogger(__name__)


class CredentialManager:
    """
    Manages credential autofill for playbook parameters

    Consolidates logic previously scattered across executions.py:
    - _retrieve_credential
    - _autofill_credential_type_parameters
    - _autofill_gateway_url_parameter
    - _autofill_username_password_parameters
    - apply_credential_autofill
    """

    def __init__(self, vault: CredentialVault | None = None):
        """
        Initialize credential manager

        Args:
            vault: CredentialVault instance (creates new one if None)
        """
        self.vault = vault or CredentialVault()

    def get_credential(self, credential_name: str) -> Credential:
        """
        Retrieve credential from vault

        Args:
            credential_name: Name of credential to retrieve

        Returns:
            Credential object

        Raises:
            HTTPException: 404 if credential not found
        """
        credential = self.vault.get_credential(credential_name)
        if not credential:
            raise HTTPException(
                status_code=404, detail=f"Credential '{credential_name}' not found"
            )
        return credential

    def apply_autofill(
        self,
        playbook: Playbook,
        credential_name: str | None,
        gateway_url: str | None,
        parameters: dict,
    ) -> tuple[str | None, dict]:
        """
        Auto-fill parameters from credential if provided

        Applies autofill in order:
        1. credential-type parameters (parameters that reference credentials)
        2. gateway_url parameter (if credential has gateway_url)
        3. username/password parameters (if credential has them)

        Args:
            playbook: Loaded playbook object
            credential_name: Name of credential to use
            gateway_url: Optional gateway URL from request
            parameters: Parameters dict to modify

        Returns:
            Tuple of (gateway_url, parameters) with auto-filled values

        Raises:
            HTTPException: If credential not found
        """
        if not credential_name:
            return gateway_url, parameters

        # Retrieve credential from vault
        credential = self.get_credential(credential_name)

        # Auto-fill gateway_url if not provided in request
        if not gateway_url and credential.gateway_url:
            gateway_url = credential.gateway_url

        # Apply all parameter autofills
        parameters = self._autofill_credential_type_parameters(
            playbook, credential_name, parameters
        )
        parameters = self._autofill_gateway_url_parameter(
            playbook, credential, parameters
        )
        parameters = self._autofill_username_password_parameters(
            playbook, credential, parameters
        )

        logger.info(
            f"Applied credential autofill: gateway_url={gateway_url}, "
            f"credential={credential_name}, params={list(parameters.keys())}"
        )

        return gateway_url, parameters

    def _autofill_credential_type_parameters(
        self, playbook: Playbook, credential_name: str, parameters: dict
    ) -> dict:
        """
        Auto-fill credential-type parameters with credential name

        Args:
            playbook: Loaded playbook object
            credential_name: Name of credential to use
            parameters: Parameters dict to modify

        Returns:
            Updated parameters dict
        """
        for param in playbook.parameters:
            if param.type == "credential" and param.name not in parameters:
                parameters[param.name] = credential_name
                logger.debug(f"Autofilled credential parameter: {param.name}")

        return parameters

    def _autofill_gateway_url_parameter(
        self, playbook: Playbook, credential: Credential, parameters: dict
    ) -> dict:
        """
        Auto-fill gateway_url parameter if it exists in playbook

        Args:
            playbook: Loaded playbook object
            credential: Credential object with gateway_url
            parameters: Parameters dict to modify

        Returns:
            Updated parameters dict
        """
        if not credential.gateway_url:
            return parameters

        for param in playbook.parameters:
            if param.name.lower() in ["gateway_url", "url"] and param.name not in parameters:
                parameters[param.name] = credential.gateway_url
                logger.debug(f"Autofilled gateway_url parameter: {param.name}")

        return parameters

    def _autofill_username_password_parameters(
        self, playbook: Playbook, credential: Credential, parameters: dict
    ) -> dict:
        """
        Auto-fill username/password parameters if they exist in playbook

        Args:
            playbook: Loaded playbook object
            credential: Credential object with username/password
            parameters: Parameters dict to modify

        Returns:
            Updated parameters dict
        """
        for param in playbook.parameters:
            # Username autofill
            if (
                param.name.lower() in ["username", "user", "gateway_username"]
                and param.name not in parameters
            ):
                parameters[param.name] = credential.username
                logger.debug(f"Autofilled username parameter: {param.name}")

            # Password autofill
            elif (
                param.name.lower() in ["password", "pass", "gateway_password"]
                and param.name not in parameters
            ):
                parameters[param.name] = credential.password
                logger.debug(f"Autofilled password parameter: {param.name}")

        return parameters
