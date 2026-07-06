"""
Perspective Project Audit API Router

Static analysis of a Perspective project export: upload a project zip,
run the seed rule pack (naming, layout, bindings, scripts, consistency,
hygiene), get back a customer-facing findings report.

SECURITY: the uploaded project is streamed to a temporary directory that is
deleted at the end of the request — it is never written anywhere permanent.
Customer project exports can contain proprietary view logic and should not
outlive the request that analysed them.
"""

import logging
import tempfile
import zipfile
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import Response

from ignition_toolkit.audit.engine import RuleEngine
from ignition_toolkit.audit.project import PerspectiveProject
from ignition_toolkit.audit.report import AuditReport, generate_report
from ignition_toolkit.audit.rules.perspective import default_rules

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/audit", tags=["audit"])

# Customer project exports are typically a few MB; 50 MB comfortably covers
# a large real project while keeping a single request from exhausting memory
# or disk on the desktop machine running the Toolbox.
MAX_UPLOAD_BYTES = 50 * 1024 * 1024
_UPLOAD_CHUNK_BYTES = 1024 * 1024


async def _save_upload_to_temp(file: UploadFile, dest: Path) -> int:
    """Stream ``file`` to ``dest``, rejecting the upload once it exceeds the limit.

    Reads in fixed-size chunks (rather than ``await file.read()``, which
    would buffer the entire body first) so an oversized upload is rejected
    without ever holding the whole thing in memory.
    """
    total = 0
    with dest.open("wb") as out:
        while True:
            chunk = await file.read(_UPLOAD_CHUNK_BYTES)
            if not chunk:
                break
            total += len(chunk)
            if total > MAX_UPLOAD_BYTES:
                raise HTTPException(
                    status_code=413,
                    detail=(
                        f"Upload exceeds the {MAX_UPLOAD_BYTES // (1024 * 1024)} MB limit "
                        "for a Perspective project export."
                    ),
                )
            out.write(chunk)
    return total


def _load_project_or_400(zip_path: Path, filename: str | None) -> PerspectiveProject:
    """Load a project export, mapping bad input to 400s instead of 500s."""
    display_name = filename or zip_path.name
    if not zipfile.is_zipfile(zip_path):
        raise HTTPException(
            status_code=400,
            detail=(
                f"'{display_name}' is not a valid zip file. Export the project as a zip "
                "from the Designer (Project -> Export) or a gateway backup."
            ),
        )
    try:
        return PerspectiveProject.load(zip_path)
    except (FileNotFoundError, OSError, zipfile.BadZipFile, ValueError) as exc:
        # ValueError covers malformed content inside the zip: corrupt
        # view.json (json.JSONDecodeError) and schema-invalid views
        # (pydantic.ValidationError) are both ValueError subclasses. Anything
        # else is a genuine server bug and must surface as a 500, not be
        # blamed on the customer's upload.
        raise HTTPException(
            status_code=400, detail=f"Could not read project export '{display_name}': {exc}"
        ) from exc


async def _run_audit(file: UploadFile) -> AuditReport:
    """Validate, load, and audit an uploaded project zip; always cleans up the temp copy."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file was uploaded.")

    # Use the uploaded file's own basename (never the client-supplied path)
    # for the temp copy so the project name derived from it (see
    # PerspectiveProject.load) matches what the customer uploaded, e.g.
    # "MyProject.zip" -> project name "MyProject" instead of a generic
    # "project" placeholder.
    safe_basename = Path(file.filename).name or "project.zip"

    with tempfile.TemporaryDirectory(prefix="ignition-toolkit-audit-") as tmp:
        zip_path = Path(tmp) / safe_basename
        total_bytes = await _save_upload_to_temp(file, zip_path)
        if total_bytes == 0:
            raise HTTPException(status_code=400, detail="Uploaded file is empty.")

        project = _load_project_or_400(zip_path, file.filename)
        findings = RuleEngine(default_rules()).run(project)
        return generate_report(project.name, project.inventory(), findings)


@router.post("/perspective")
async def audit_perspective_project(file: UploadFile = File(...)) -> dict:
    """
    Run the static Perspective audit against an uploaded project export.

    Accepts a project export zip (Designer export or gateway backup), up to
    50 MB. The project is analysed against the seed rule pack (naming,
    layout, bindings, scripts, consistency, hygiene) and the temp copy is
    deleted before the response is returned.
    """
    report = await _run_audit(file)
    return report.to_dict()


@router.post("/perspective/markdown")
async def audit_perspective_project_markdown(file: UploadFile = File(...)) -> Response:
    """
    Same audit as ``POST /api/audit/perspective``, returned as a downloadable
    markdown report instead of JSON. Re-runs the audit against the same
    upload — nothing from a prior call is cached or persisted server-side.
    """
    report = await _run_audit(file)
    markdown = report.to_markdown()
    safe_name = (
        "".join(c if c.isalnum() or c in "-_" else "_" for c in report.project_name) or "project"
    )
    filename = f"{safe_name}-audit-report.md"
    return Response(
        content=markdown,
        media_type="text/markdown",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
