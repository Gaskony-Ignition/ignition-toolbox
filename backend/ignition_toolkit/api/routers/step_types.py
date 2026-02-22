"""
Step type metadata API endpoint

Returns metadata for all available step types including:
- Type name (e.g., 'gateway.login')
- Domain (gateway, browser, designer, perspective, utility, playbook, fat)
- Description of what the step does
- Parameter definitions with type, required, default, and description
"""

from fastapi import APIRouter
from pydantic import BaseModel

from ignition_toolkit.playbook.step_type_registry import (
    StepParameter,  # Re-exported for backwards compatibility
    get_all_definitions,
)

router = APIRouter(prefix="/api/playbooks", tags=["playbooks"])

# StepParameter is imported from the registry (single definition).
# It is re-exported here so that any code that previously imported it from
# this module continues to work without changes.
__all__ = ["StepParameter", "StepTypeInfo", "StepTypesResponse", "STEP_TYPE_METADATA"]


class StepTypeInfo(BaseModel):
    """Metadata for a step type"""
    type: str
    domain: str
    description: str
    parameters: list[StepParameter]


class StepTypesResponse(BaseModel):
    """Response containing all step types"""
    step_types: list[StepTypeInfo]
    domains: list[str]


# Auto-generated from the unified step type registry.
# To add a new step type, add it to playbook/step_type_registry.py instead of editing here.
STEP_TYPE_METADATA: list[StepTypeInfo] = [
    StepTypeInfo(
        type=defn.type_value,
        domain=defn.domain,
        description=defn.description,
        parameters=defn.parameters,
    )
    for defn in get_all_definitions()
]


@router.get("/step-types", response_model=StepTypesResponse)
async def get_step_types():
    """
    Get metadata for all available step types.

    Returns step type definitions including:
    - Type identifier (e.g., 'gateway.login')
    - Domain classification (gateway, browser, designer, etc.)
    - Human-readable description
    - Parameter definitions with types, defaults, and descriptions
    """
    # Get unique domains
    domains = sorted(set(step.domain for step in STEP_TYPE_METADATA))

    return StepTypesResponse(
        step_types=STEP_TYPE_METADATA,
        domains=domains
    )
