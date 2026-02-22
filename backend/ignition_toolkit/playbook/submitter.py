"""
Playbook submitter - Submit playbooks to the GitHub library

Uses GitHub Git Trees/Commits API to create commits that add playbooks
to the central repository.
"""

import hashlib
import json
import logging
from pathlib import Path
from typing import Any

import httpx

from ignition_toolkit.core.paths import get_user_data_dir
from ignition_toolkit.playbook.registry import DEFAULT_REPO

logger = logging.getLogger(__name__)

GITHUB_API = "https://api.github.com"
SETTINGS_FILE = "github_settings.json"


def _get_settings_path() -> Path:
    """Get path to GitHub settings file."""
    return get_user_data_dir() / SETTINGS_FILE


def get_github_token() -> str | None:
    """Read GitHub PAT from settings file."""
    path = _get_settings_path()
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text())
        return data.get("github_token")
    except Exception:
        return None


def save_github_token(token: str) -> None:
    """Save GitHub PAT to settings file."""
    path = _get_settings_path()
    path.parent.mkdir(parents=True, exist_ok=True)

    # Read existing settings if any
    data: dict[str, Any] = {}
    if path.exists():
        try:
            data = json.loads(path.read_text())
        except Exception:
            pass

    data["github_token"] = token
    path.write_text(json.dumps(data, indent=2))
    logger.info("GitHub token saved")


def delete_github_token() -> None:
    """Remove GitHub PAT from settings file."""
    path = _get_settings_path()
    if not path.exists():
        return
    try:
        data = json.loads(path.read_text())
        data.pop("github_token", None)
        path.write_text(json.dumps(data, indent=2))
        logger.info("GitHub token removed")
    except Exception:
        pass


def get_token_preview() -> str | None:
    """Get a masked preview of the stored token (first 4 + last 4 chars)."""
    token = get_github_token()
    if not token:
        return None
    if len(token) <= 8:
        return "****"
    return f"{token[:4]}...{token[-4:]}"


async def submit_playbook(
    yaml_content: str,
    playbook_path: str,
    metadata: dict[str, Any],
) -> dict[str, Any]:
    """
    Submit a playbook to the GitHub library via Git Trees/Commits API.

    Creates a single commit with:
    - The YAML file at library/{domain}/{filename}.yaml
    - Updated playbooks-index.json with new entry

    Args:
        yaml_content: The YAML content of the playbook
        playbook_path: The playbook path (e.g., "gateway/my_playbook.yaml")
        metadata: Dict with keys: name, version, description, domain, author, tags, group, release_notes

    Returns:
        Dict with commit_url, sha, message
    """
    token = get_github_token()
    if not token:
        raise ValueError("GitHub token not configured. Please set your GitHub PAT in Settings > Integrations.")

    domain = metadata.get("domain", "gateway")
    filename = playbook_path.split("/")[-1]
    library_path = f"library/{domain}/{filename}"

    # Calculate checksum
    checksum = hashlib.sha256(yaml_content.encode()).hexdigest()

    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        # 1. Get the default branch ref
        ref_resp = await client.get(
            f"{GITHUB_API}/repos/{DEFAULT_REPO}/git/ref/heads/main",
            headers=headers,
        )
        if ref_resp.status_code == 404:
            raise ValueError(f"Repository {DEFAULT_REPO} not found or no access. Check your token permissions.")
        ref_resp.raise_for_status()
        base_sha = ref_resp.json()["object"]["sha"]

        # 2. Get the base tree
        commit_resp = await client.get(
            f"{GITHUB_API}/repos/{DEFAULT_REPO}/git/commits/{base_sha}",
            headers=headers,
        )
        commit_resp.raise_for_status()
        base_tree_sha = commit_resp.json()["tree"]["sha"]

        # 3. Try to get existing playbooks-index.json
        index_content: dict[str, Any] = {"playbooks": []}
        index_resp = await client.get(
            f"{GITHUB_API}/repos/{DEFAULT_REPO}/contents/playbooks-index.json",
            headers=headers,
        )
        if index_resp.status_code == 200:
            import base64
            content_b64 = index_resp.json()["content"]
            index_content = json.loads(base64.b64decode(content_b64))

        # 4. Update index with new entry (or update existing)
        download_url = f"https://raw.githubusercontent.com/{DEFAULT_REPO}/main/{library_path}"
        new_entry = {
            "playbook_path": f"{domain}/{filename.replace('.yaml', '')}",
            "version": metadata.get("version", "1.0"),
            "domain": domain,
            "description": metadata.get("description", ""),
            "author": metadata.get("author", "Community"),
            "tags": metadata.get("tags", []),
            "group": metadata.get("group", ""),
            "release_notes": metadata.get("release_notes"),
            "checksum": checksum,
            "download_url": download_url,
            "verified": False,
            "verified_by": None,
            "size_bytes": len(yaml_content.encode()),
        }

        # Remove existing entry for same path if it exists
        existing_playbooks = [
            p for p in index_content.get("playbooks", [])
            if p.get("playbook_path") != new_entry["playbook_path"]
        ]
        existing_playbooks.append(new_entry)
        index_content["playbooks"] = existing_playbooks

        updated_index = json.dumps(index_content, indent=2)

        # 5. Create blobs for both files
        yaml_blob_resp = await client.post(
            f"{GITHUB_API}/repos/{DEFAULT_REPO}/git/blobs",
            headers=headers,
            json={"content": yaml_content, "encoding": "utf-8"},
        )
        yaml_blob_resp.raise_for_status()
        yaml_blob_sha = yaml_blob_resp.json()["sha"]

        index_blob_resp = await client.post(
            f"{GITHUB_API}/repos/{DEFAULT_REPO}/git/blobs",
            headers=headers,
            json={"content": updated_index, "encoding": "utf-8"},
        )
        index_blob_resp.raise_for_status()
        index_blob_sha = index_blob_resp.json()["sha"]

        # 6. Create tree with both files
        tree_resp = await client.post(
            f"{GITHUB_API}/repos/{DEFAULT_REPO}/git/trees",
            headers=headers,
            json={
                "base_tree": base_tree_sha,
                "tree": [
                    {
                        "path": library_path,
                        "mode": "100644",
                        "type": "blob",
                        "sha": yaml_blob_sha,
                    },
                    {
                        "path": "playbooks-index.json",
                        "mode": "100644",
                        "type": "blob",
                        "sha": index_blob_sha,
                    },
                ],
            },
        )
        tree_resp.raise_for_status()
        new_tree_sha = tree_resp.json()["sha"]

        # 7. Create commit
        name = metadata.get("name", filename)
        commit_message = f"Add playbook: {name}\n\nSubmitted via Ignition Toolbox"
        if metadata.get("release_notes"):
            commit_message += f"\n\n{metadata['release_notes']}"

        new_commit_resp = await client.post(
            f"{GITHUB_API}/repos/{DEFAULT_REPO}/git/commits",
            headers=headers,
            json={
                "message": commit_message,
                "tree": new_tree_sha,
                "parents": [base_sha],
            },
        )
        new_commit_resp.raise_for_status()
        new_commit_sha = new_commit_resp.json()["sha"]

        # 8. Update ref
        update_ref_resp = await client.patch(
            f"{GITHUB_API}/repos/{DEFAULT_REPO}/git/refs/heads/main",
            headers=headers,
            json={"sha": new_commit_sha},
        )
        update_ref_resp.raise_for_status()

        commit_url = f"https://github.com/{DEFAULT_REPO}/commit/{new_commit_sha}"
        logger.info(f"Playbook submitted: {commit_url}")

        return {
            "commit_url": commit_url,
            "sha": new_commit_sha,
            "message": f"Playbook '{name}' submitted successfully",
            "library_path": library_path,
        }
