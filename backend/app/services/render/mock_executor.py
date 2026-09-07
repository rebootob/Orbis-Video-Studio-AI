import os
from typing import Dict, Any, Callable, Optional
from app.services.render.base import RenderExecutor


class MockRenderExecutor(RenderExecutor):
    """
    Test double for RenderExecutor used in unit and integration tests.
    Generates synthetic MP4 file output on scratch disk.
    """

    def __init__(self, should_fail: bool = False, fail_message: str = "Mock render execution failure"):
        self.should_fail = should_fail
        self.fail_message = fail_message

    def render_timeline(
        self,
        timeline_spec: Dict[str, Any],
        scratch_dir: str,
        output_file_path: str,
        progress_callback: Optional[Callable[[float], None]] = None,
    ) -> Dict[str, Any]:
        if self.should_fail:
            raise RuntimeError(self.fail_message)

        os.makedirs(os.path.dirname(output_file_path), exist_ok=True)

        if progress_callback:
            progress_callback(25.0)
            progress_callback(50.0)
            progress_callback(75.0)

        total_duration = float(timeline_spec.get("total_duration", 10.0))
        placements = timeline_spec.get("placements", [])
        audio_clips = timeline_spec.get("audio_clips", [])

        import json
        payload_data = {
            "total_duration": total_duration,
            "placement_count": len(placements),
            "placements": placements,
            "audio_clip_count": len(audio_clips),
            "audio_clips": audio_clips,
            "marker": f"ORBIS_SYNTHETIC_RENDER_DURATION_{total_duration}",
        }
        payload = json.dumps(payload_data).encode("utf-8")
        mdat_hdr = (len(payload) + 8).to_bytes(4, "big") + b"mdat"
        ftyp = b"\x00\x00\x00\x1cftypisom\x00\x00\x02\x00isomiso2avc1mp41"
        with open(output_file_path, "wb") as f:
            f.write(ftyp)
            f.write(mdat_hdr)
            f.write(payload)

        if progress_callback:
            progress_callback(100.0)

        file_size = os.path.getsize(output_file_path)

        return {
            "duration_seconds": total_duration,
            "file_size_bytes": file_size,
            "video_codec": "h264",
            "audio_codec": "aac",
            "width": 1920,
            "height": 1080,
            "frame_rate": 30.0,
            "render_profile": timeline_spec.get("render_profile", "MASTER_HD"),
            "placement_count": len(placements),
            "audio_clip_count": len(audio_clips),
        }
