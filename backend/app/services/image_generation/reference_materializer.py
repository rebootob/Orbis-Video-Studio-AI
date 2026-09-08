"""Provider-neutral materialization of canonical Orbis image references.

ContinuityMapper intentionally stores durable asset download references rather
than provider payload bytes. Production image adapters can call this boundary to
materialize the referenced object at dispatch time without persisting base64 or
presigned credentials in GenerationJob payloads.
"""
import re
import uuid
from typing import Tuple

from app.db.session import SessionLocal
from app.models.asset import Asset
from app.models.scene import Scene
from app.models.shot import Shot
from app.models.story import Story
from app.services.storage.factory import get_storage_provider

_CANONICAL_ASSET_URL = re.compile(
    r"^/assets/(?P<asset_id>[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-5][0-9a-fA-F]{3}-[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12})/download$"
)
_SUPPORTED_REFERENCE_MIME_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_REFERENCE_IMAGE_BYTES = 8 * 1024 * 1024


class ReferenceMaterializationError(ValueError):
    pass


def _resolve_shot_project_id(db, shot: Shot):
    scene = db.get(Scene, shot.scene_id)
    if not scene:
        return None
    if scene.project_id:
        return scene.project_id
    if scene.story_id:
        story = db.get(Story, scene.story_id)
        return story.project_id if story else None
    return None


def materialize_reference_image(url: str, shot_id: str) -> Tuple[bytes, str]:
    """Resolve one canonical Orbis asset reference to bounded image bytes.

    Fail closed for non-canonical URLs, cross-project assets, unsupported media,
    missing storage objects, and oversized inline references.
    """
    match = _CANONICAL_ASSET_URL.fullmatch(str(url or ""))
    if not match:
        raise ReferenceMaterializationError("REFERENCE_URL_UNSUPPORTED")
    try:
        asset_id = uuid.UUID(match.group("asset_id"))
        canonical_shot_id = uuid.UUID(str(shot_id))
    except ValueError as exc:
        raise ReferenceMaterializationError("REFERENCE_ID_INVALID") from exc

    with SessionLocal() as db:
        shot = db.get(Shot, canonical_shot_id)
        asset = db.get(Asset, asset_id)
        if not shot or not asset:
            raise ReferenceMaterializationError("REFERENCE_NOT_FOUND")
        project_id = _resolve_shot_project_id(db, shot)
        if not project_id or asset.project_id != project_id:
            raise ReferenceMaterializationError("REFERENCE_PROJECT_MISMATCH")
        if asset.content_type not in _SUPPORTED_REFERENCE_MIME_TYPES:
            raise ReferenceMaterializationError("REFERENCE_MIME_UNSUPPORTED")
        if asset.file_size_bytes is not None and asset.file_size_bytes > MAX_REFERENCE_IMAGE_BYTES:
            raise ReferenceMaterializationError("REFERENCE_TOO_LARGE")
        bucket = asset.storage_bucket
        key = asset.storage_key
        content_type = asset.content_type

    payload = get_storage_provider().get_object(bucket, key)
    if not payload:
        raise ReferenceMaterializationError("REFERENCE_EMPTY")
    if len(payload) > MAX_REFERENCE_IMAGE_BYTES:
        raise ReferenceMaterializationError("REFERENCE_TOO_LARGE")
    return payload, content_type
