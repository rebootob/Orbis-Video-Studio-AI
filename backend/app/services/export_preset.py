import json
import hashlib
from typing import Dict, Any, List, Optional
from fastapi import HTTPException


SYSTEM_EXPORT_PRESETS: Dict[str, Dict[str, Any]] = {
    "YT_MASTER_4K": {
        "preset_id": "YT_MASTER_4K",
        "target_platform": "YouTube Master",
        "aspect_ratio": "16:9",
        "width": 3840,
        "height": 2160,
        "video_codec": "h264",
        "video_profile": "high",
        "audio_codec": "aac",
        "audio_bitrate_kbps": 320,
        "video_bitrate_kbps": 25000,
        "estimated_cost_usd": 0.50,
        "framing_mode": "NATIVE_16X9",
    },
    "YT_STANDARD_1080P": {
        "preset_id": "YT_STANDARD_1080P",
        "target_platform": "YouTube Standard",
        "aspect_ratio": "16:9",
        "width": 1920,
        "height": 1080,
        "video_codec": "h264",
        "video_profile": "main",
        "audio_codec": "aac",
        "audio_bitrate_kbps": 192,
        "video_bitrate_kbps": 10000,
        "estimated_cost_usd": 0.50,
        "framing_mode": "NATIVE_16X9",
    },
    "TIKTOK_REELS_9X16": {
        "preset_id": "TIKTOK_REELS_9X16",
        "target_platform": "TikTok / Shorts / Reels",
        "aspect_ratio": "9:16",
        "width": 1080,
        "height": 1920,
        "video_codec": "h264",
        "video_profile": "main",
        "audio_codec": "aac",
        "audio_bitrate_kbps": 192,
        "video_bitrate_kbps": 8000,
        "estimated_cost_usd": 0.50,
        "framing_mode": "CENTER_CROP_PAD",
    },
    "INSTAGRAM_SQUARE": {
        "preset_id": "INSTAGRAM_SQUARE",
        "target_platform": "Instagram Feed",
        "aspect_ratio": "1:1",
        "width": 1080,
        "height": 1080,
        "video_codec": "h264",
        "video_profile": "main",
        "audio_codec": "aac",
        "audio_bitrate_kbps": 160,
        "video_bitrate_kbps": 6000,
        "estimated_cost_usd": 0.50,
        "framing_mode": "PILLARBOX_CROP",
    },
    "LMS_WEB_720P": {
        "preset_id": "LMS_WEB_720P",
        "target_platform": "Corporate LMS / Web",
        "aspect_ratio": "16:9",
        "width": 1280,
        "height": 720,
        "video_codec": "h264",
        "video_profile": "baseline",
        "audio_codec": "aac",
        "audio_bitrate_kbps": 128,
        "video_bitrate_kbps": 3000,
        "estimated_cost_usd": 0.50,
        "framing_mode": "NATIVE_16X9",
    },
}


class ExportPresetService:
    @classmethod
    def list_presets(cls) -> List[Dict[str, Any]]:
        return list(SYSTEM_EXPORT_PRESETS.values())

    @classmethod
    def get_preset(cls, preset_id: str) -> Dict[str, Any]:
        preset = SYSTEM_EXPORT_PRESETS.get(preset_id.upper())
        if not preset:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown export preset '{preset_id}'. Allowed presets: {list(SYSTEM_EXPORT_PRESETS.keys())}",
            )
        return dict(preset)

    @classmethod
    def compute_preset_snapshot_hash(cls, preset_snapshot: Dict[str, Any]) -> str:
        serialized = json.dumps(preset_snapshot, sort_keys=True)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()[:12]

    @classmethod
    def compute_render_variant_key(cls, preset_id: str, preset_snapshot: Dict[str, Any]) -> str:
        if preset_id.upper() in ("MASTER", "MASTER_HD"):
            return "MASTER"
        snapshot_hash = cls.compute_preset_snapshot_hash(preset_snapshot)
        return f"{preset_id.upper()}:{snapshot_hash}"
