from typing import Set
from fastapi import HTTPException, status


CORE_V1_VIDEO_MODES: Set[str] = {
    "STORY",
    "SHORT",
    "LOOP",
    "SCENE",
}

ARCHITECTURE_READY_VIDEO_MODES: Set[str] = {
    "PRODUCT",
    "EXPLAINER",
    "PRESENTER",
    "MONTAGE",
}

ALLOWED_SHOT_TYPES: Set[str] = {
    "AI_GENERATED",
    "IMPORTED_VIDEO",
    "IMPORTED_IMAGE",
    "RECORDED_FOOTAGE",
    "STOCK_ASSET",
    "MIXED",
}

ALLOWED_LOCK_TARGETS: Set[str] = {
    "SCRIPT",
    "SCENE",
    "SHOT",
    "CHARACTER",
    "LOCATION",
    "VOICE",
    "TIMING",
}


def validate_video_mode(video_mode: str) -> str:
    if not video_mode or not isinstance(video_mode, str):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid video mode: mode cannot be empty",
        )
    normalized = video_mode.strip().upper()
    if normalized in ARCHITECTURE_READY_VIDEO_MODES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Video mode '{normalized}' is architecture-ready only and not supported in Core V1. Supported modes: STORY, SHORT, LOOP, SCENE.",
        )
    if normalized not in CORE_V1_VIDEO_MODES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported video mode '{video_mode}'. Allowed Core V1 modes: {', '.join(sorted(CORE_V1_VIDEO_MODES))}.",
        )
    return normalized


def validate_shot_type(shot_type: str) -> str:
    if not shot_type or not isinstance(shot_type, str):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid shot type: type cannot be empty",
        )
    normalized = shot_type.strip().upper()
    if normalized not in ALLOWED_SHOT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported shot type '{shot_type}'. Allowed types: {', '.join(sorted(ALLOWED_SHOT_TYPES))}.",
        )
    return normalized


def validate_lock_target(entity_type: str) -> str:
    if not entity_type or not isinstance(entity_type, str):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid lock target: entity type cannot be empty",
        )
    normalized = entity_type.strip().upper()
    if normalized not in ALLOWED_LOCK_TARGETS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported lock target '{entity_type}'. Allowed targets: {', '.join(sorted(ALLOWED_LOCK_TARGETS))}.",
        )
    return normalized
