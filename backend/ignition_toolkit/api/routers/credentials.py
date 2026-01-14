"""
Credential management routes

Handles secure credential storage, retrieval, updates, and deletion.
"""

import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ignition_toolkit.credentials import CredentialVault
from ignition_toolkit.credentials.vault import Credential

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/credentials", tags=["credentials"])


# ============================================================================
# Pydantic Models
# ============================================================================


class CredentialInfo(BaseModel):
    """Credential information (without password)"""

    name: str
    username: str
    gateway_url: str | None = None
    description: str | None = ""


class CredentialCreate(BaseModel):
    """Credential creation request"""

    name: str
    username: str
    password: str
    gateway_url: str | None = None
    description: str | None = ""


# ============================================================================
# Routes
# ============================================================================


@router.get("", response_model=list[CredentialInfo])
async def list_credentials():
    """List all credentials (without passwords)"""
    try:
        vault = CredentialVault()
        credentials = vault.list_credentials()
        return [
            CredentialInfo(
                name=cred.name,
                username=cred.username,
                gateway_url=cred.gateway_url,
                description=cred.description,
            )
            for cred in credentials
        ]
    except Exception as e:
        logger.exception(f"Error listing credentials: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("")
async def add_credential(credential: CredentialCreate):
    """Add new credential"""
    try:
        # Validate credential name is not empty
        if not credential.name or not credential.name.strip():
            raise HTTPException(
                status_code=400, detail="Credential name cannot be empty"
            )

        vault = CredentialVault()

        # Check if credential already exists
        try:
            existing = vault.get_credential(credential.name)
            if existing:
                raise HTTPException(
                    status_code=400, detail=f"Credential '{credential.name}' already exists"
                )
        except ValueError:
            # Credential doesn't exist, which is what we want
            pass

        # Save new credential
        vault.save_credential(
            Credential(
                name=credential.name,
                username=credential.username,
                password=credential.password,
                gateway_url=credential.gateway_url,
                description=credential.description,
            )
        )

        return {"message": "Credential added successfully", "name": credential.name}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding credential: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{name}")
async def update_credential(name: str, credential: CredentialCreate):
    """Update existing credential"""
    try:
        # Validate credential name is not empty
        if not name or not name.strip():
            raise HTTPException(
                status_code=400, detail="Credential name cannot be empty"
            )

        vault = CredentialVault()

        # Check if credential exists
        try:
            existing = vault.get_credential(name)
            if not existing:
                raise HTTPException(status_code=404, detail=f"Credential '{name}' not found")
        except ValueError:
            raise HTTPException(status_code=404, detail=f"Credential '{name}' not found")

        # Update credential (delete and re-add with same name)
        vault.delete_credential(name)
        vault.save_credential(
            Credential(
                name=name,  # Use name from URL path, not from body
                username=credential.username,
                password=credential.password,
                gateway_url=credential.gateway_url,
                description=credential.description,
            )
        )

        return {"message": "Credential updated successfully", "name": name}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating credential: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{name}")
async def delete_credential(name: str):
    """Delete credential"""
    try:
        # Validate credential name is not empty
        if not name or not name.strip():
            raise HTTPException(
                status_code=400, detail="Credential name cannot be empty"
            )

        vault = CredentialVault()
        success = vault.delete_credential(name)

        if not success:
            raise HTTPException(status_code=404, detail=f"Credential '{name}' not found")

        return {"message": "Credential deleted successfully", "name": name}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting credential: {e}")
        raise HTTPException(status_code=500, detail=str(e))
