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

        # Compute placement transition overlaps
        total_overlap = 0.0
        transition_specs = []
        if placements:
            for i in range(len(placements) - 1):
                trans = str(placements[i].get("transition_to_next", "CUT")).upper()
                if trans in ("FADE", "DISSOLVE"):
                    d1 = float(placements[i].get("effective_duration", 4.0))
                    d2 = float(placements[i + 1].get("effective_duration", 4.0))
                    overlap = min(0.5, d1 / 2.0, d2 / 2.0)
                    total_overlap += overlap
                    transition_specs.append((trans, overlap))
                else:
                    transition_specs.append(("CUT", 0.0))
            raw_video_duration = sum(float(p.get("effective_duration", 4.0)) for p in placements)
            final_timeline_duration = max(0.1, round(raw_video_duration - total_overlap, 4))
        else:
            final_timeline_duration = total_duration

        audible_audio_clips = []
        for ac in audio_clips:
            if not bool(ac.get("mute", False)) and float(ac.get("volume", 1.0)) > 0:
                fade_out = float(ac.get("fade_out", 0.0))
                clip_dur = float(ac["duration_seconds"]) if ac.get("duration_seconds") is not None else None
                effective_dur = clip_dur if clip_dur is not None else final_timeline_duration
                fade_out_start = max(0.0, effective_dur - fade_out) if fade_out > 0 else 0.0
                ac_copy = dict(ac)
                ac_copy["calculated_fade_out_start"] = fade_out_start
                audible_audio_clips.append(ac_copy)

        import json
        payload_data = {
            "total_duration": final_timeline_duration,
            "placement_count": len(placements),
            "placements": placements,
            "audio_clip_count": len(audible_audio_clips),
            "audio_clips": audible_audio_clips,
            "transition_overlap_seconds": total_overlap,
            "transition_specs": transition_specs,
            "marker": f"ORBIS_SYNTHETIC_RENDER_DURATION_{final_timeline_duration}",
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
            "duration_seconds": final_timeline_duration,
            "file_size_bytes": file_size,
            "video_codec": "h264",
            "audio_codec": "aac",
            "width": 1920,
            "height": 1080,
            "frame_rate": 30.0,
            "render_profile": timeline_spec.get("render_profile", "MASTER_HD"),
            "placement_count": len(placements),
            "audio_clip_count": len(audible_audio_clips),
            "transition_overlap_seconds": total_overlap,
        }
