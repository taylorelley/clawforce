"""Role template endpoints (built-in + user-authored custom templates)."""

import logging
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status

from specops.apis.agents._schemas import CustomAgentTemplateRequest
from specops.apis.users import _require_admin
from specops.auth import get_current_user
from specops.core.services.agent_template_service import (
    CustomAgentTemplateError,
    CustomAgentTemplateService,
    builtin_role_ids,
)
from specops.core.storage import StorageBackend
from specops.deps import get_skill_registry, get_storage
from specops_lib.config.helpers import redact

logger = logging.getLogger(__name__)

_ROOT = Path(__file__).resolve().parents[3]
_ROLES_TEMPLATES_DIR = _ROOT / "marketplace" / "roles"

router = APIRouter(tags=["templates"])


def _iter_role_templates():
    """Yield built-in role template dirs (excluding internal dirs like _shared)."""
    if not _ROLES_TEMPLATES_DIR.is_dir():
        return
    for entry in sorted(_ROLES_TEMPLATES_DIR.iterdir()):
        if entry.is_dir() and not entry.name.startswith((".", "_")):
            yield entry


def _builtin_summary(entry: Path) -> dict[str, Any]:
    return {
        "value": entry.name,
        "label": entry.name.replace("-", " ").title(),
        "custom": False,
        "editable": False,
    }


def _custom_summary(template_id: str, label_override: str | None = None) -> dict[str, Any]:
    label = label_override or template_id.removeprefix("custom-").replace("-", " ").title()
    return {
        "value": template_id,
        "label": label,
        "custom": True,
        "editable": True,
    }


def _make_skill_resolver(registry):
    """Return a function ``slug -> SKILL.md content | None`` over the self-hosted catalog."""

    def resolver(slug: str) -> str | None:
        entry = registry.get_entry(slug) if registry and hasattr(registry, "get_entry") else None
        if not entry:
            return None
        content = entry.get("skill_content")
        return str(content) if content else None

    return resolver


def _collect_files_with_content(base: Path) -> list[dict[str, str]]:
    """Read files under ``base`` for the detail view.

    The agent.yaml config file may contain secrets (mcp_servers env values,
    channel tokens, provider api keys); we replace its content with a redacted
    summary instead of dumping raw YAML so a normal template fetch never leaks
    them.
    """
    out: list[dict[str, str]] = []
    if not base.is_dir():
        return out
    for p in sorted(base.rglob("*")):
        if p.is_file():
            rel = str(p.relative_to(base)).replace("\\", "/")
            if rel == "config/agent.yaml":
                content = "# (redacted — fetch the structured payload via GET /api/templates/{id} instead)"
            else:
                try:
                    content = p.read_text(encoding="utf-8", errors="replace")
                except Exception:
                    content = "(binary or unreadable)"
            out.append({"path": rel, "content": content})
    return out


def _redact_template_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Return a copy of a custom template payload with secret fields redacted.

    Drives off the ``secret_fields`` declarations on the underlying Pydantic
    models (channels, providers, etc.) via :func:`specops_lib.config.helpers.redact`.
    """
    if not payload:
        return payload
    redacted = dict(payload)
    if isinstance(payload.get("channels"), dict):
        redacted["channels"] = redact(payload["channels"], path=("channels",))
    if isinstance(payload.get("tools"), dict):
        redacted["tools"] = redact(payload["tools"], path=("tools",))
    # mcp_servers env / headers values may contain installation secrets.
    mcp = payload.get("mcp_servers")
    if isinstance(mcp, dict):
        redacted_mcp: dict[str, Any] = {}
        for key, server in mcp.items():
            if not isinstance(server, dict):
                redacted_mcp[key] = server
                continue
            entry = dict(server)
            if isinstance(entry.get("env"), dict):
                entry["env"] = {k: "***" for k in entry["env"]}
            if isinstance(entry.get("headers"), dict):
                entry["headers"] = {k: "***" for k in entry["headers"]}
            redacted_mcp[key] = entry
        redacted["mcp_servers"] = redacted_mcp
    return redacted


@router.get("/api/templates")
def list_templates(
    _: dict = Depends(get_current_user),
    storage: StorageBackend = Depends(get_storage),
):
    """List built-in role templates merged with user-authored custom templates."""
    builtins = [_builtin_summary(entry) for entry in _iter_role_templates()]
    builtin_names = {b["value"] for b in builtins}

    service = CustomAgentTemplateService(storage)
    custom_entries = []
    for template_id in service.list_ids():
        if template_id in builtin_names:
            continue
        summary = service.get(template_id) or {}
        label = summary.get("name") or template_id.removeprefix("custom-").replace("-", " ").title()
        custom_entries.append(_custom_summary(template_id, label))

    templates = builtins + custom_entries
    templates.sort(key=lambda t: (0 if t["value"] == "default" else 1, t["label"].lower()))
    return templates


@router.get("/api/templates/custom")
def list_custom_templates(
    _: dict = Depends(get_current_user),
    storage: StorageBackend = Depends(get_storage),
):
    """Return user-authored custom templates (secret-bearing fields redacted)."""
    service = CustomAgentTemplateService(storage)
    out: list[dict[str, Any]] = []
    for template_id in service.list_ids():
        payload = service.get(template_id)
        if payload:
            out.append(_redact_template_payload(payload))
    return out


@router.get("/api/templates/{template_id}")
def get_template_detail(
    template_id: str,
    _: dict = Depends(get_current_user),
    storage: StorageBackend = Depends(get_storage),
):
    """Return file setup (profile + workspace) with contents for a role template.

    Built-in roles win over custom templates if a slug somehow appears in both.
    """
    if template_id.startswith((".", "_")):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found")

    role_dir = _ROLES_TEMPLATES_DIR / template_id
    is_custom = False
    if not role_dir.is_dir():
        custom_service = CustomAgentTemplateService(storage)
        custom_dir = custom_service.template_dir(template_id)
        if not custom_dir:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found")
        role_dir = custom_dir
        is_custom = True

    label = template_id.replace("-", " ").title()
    response = {
        "value": template_id,
        "label": label,
        "custom": is_custom,
        "editable": is_custom,
        "profileFiles": _collect_files_with_content(role_dir / "profile"),
        "workspaceFiles": _collect_files_with_content(role_dir / "workspace"),
    }
    if is_custom:
        # Surface the structured payload for the edit form (with secrets redacted).
        custom_service = CustomAgentTemplateService(storage)
        payload = custom_service.get(template_id)
        if payload:
            response["payload"] = _redact_template_payload(payload)
    return response


@router.post("/api/templates", status_code=status.HTTP_201_CREATED)
def create_custom_template(
    body: CustomAgentTemplateRequest,
    current: dict = Depends(get_current_user),
    storage: StorageBackend = Depends(get_storage),
    registry=Depends(get_skill_registry),
):
    """Create a new custom agent template (admin only)."""
    _require_admin(current)
    service = CustomAgentTemplateService(storage)
    if body.id in builtin_role_ids():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Template id '{body.id}' collides with a built-in role",
        )
    payload = body.model_dump(by_alias=False, exclude_none=False)
    try:
        return service.create(payload, _make_skill_resolver(registry))
    except CustomAgentTemplateError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc


@router.put("/api/templates/{template_id}")
def update_custom_template(
    template_id: str,
    body: CustomAgentTemplateRequest,
    current: dict = Depends(get_current_user),
    storage: StorageBackend = Depends(get_storage),
    registry=Depends(get_skill_registry),
):
    """Update an existing custom agent template (admin only)."""
    _require_admin(current)
    if body.id != template_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="URL id and body id must match",
        )
    if template_id in builtin_role_ids():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Built-in templates cannot be modified",
        )
    service = CustomAgentTemplateService(storage)
    payload = body.model_dump(by_alias=False, exclude_none=False)
    try:
        return service.update(template_id, payload, _make_skill_resolver(registry))
    except CustomAgentTemplateError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc


@router.delete("/api/templates/{template_id}")
def delete_custom_template(
    template_id: str,
    current: dict = Depends(get_current_user),
    storage: StorageBackend = Depends(get_storage),
):
    """Delete a custom agent template (admin only; built-ins cannot be deleted)."""
    _require_admin(current)
    if template_id in builtin_role_ids():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Built-in templates cannot be deleted",
        )
    service = CustomAgentTemplateService(storage)
    if not service.delete(template_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Custom template '{template_id}' not found",
        )
    return {"ok": True, "id": template_id}
