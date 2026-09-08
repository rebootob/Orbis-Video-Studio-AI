import os
import shutil
import subprocess
import logging
from typing import Dict, Any, Callable, Optional
from app.services.render.base import RenderExecutor

logger = logging.getLogger(__name__)


class FFmpegRenderExecutor(RenderExecutor):
    """
    Concrete RenderExecutor executing video timeline assembly using FFmpeg CLI.
    Fails truthfully if FFmpeg binary is missing or if execution exits non-zero.
    No synthetic production fallbacks allowed in production execution.
    """

    def __init__(self, ffmpeg_path: str = "ffmpeg"):
        self.ffmpeg_path = ffmpeg_path

    def _has_ffmpeg(self) -> bool:
        return shutil.which(self.ffmpeg_path) is not None

    def validate_runtime(self) -> str:
        """Fail fast if the configured FFmpeg runtime is not executable."""
        resolved_path = shutil.which(self.ffmpeg_path)
        if not resolved_path:
            raise RuntimeError(f"FFmpeg binary '{self.ffmpeg_path}' not found on worker host system.")

        try:
            result = subprocess.run(
                [resolved_path, "-version"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=10,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise RuntimeError(f"FFmpeg runtime validation failed for '{resolved_path}': {exc}") from exc

        if result.returncode != 0:
            detail = (result.stderr or result.stdout or "unknown FFmpeg error").strip()
            raise RuntimeError(
                f"FFmpeg runtime validation failed for '{resolved_path}' with code {result.returncode}: {detail}"
            )

        return resolved_path

    def render_timeline(
        self,
        timeline_spec: Dict[str, Any],
        scratch_dir: str,
        output_file_path: str,
        progress_callback: Optional[Callable[[float], None]] = None,
    ) -> Dict[str, Any]:
        if not self._has_ffmpeg():
            raise RuntimeError(f"FFmpeg binary '{self.ffmpeg_path}' not found on worker host system.")

        os.makedirs(os.path.dirname(output_file_path), exist_ok=True)

        if progress_callback:
            progress_callback(10.0)

        placements = timeline_spec.get("placements", [])
        audio_clips = timeline_spec.get("audio_clips", [])
        total_duration = float(timeline_spec.get("total_duration", 10.0))
        render_profile = str(timeline_spec.get("render_profile", "MASTER_HD")).upper()
        render_meta = timeline_spec.get("render_metadata") or {}
        preset_snapshot = timeline_spec.get("preset_snapshot") or render_meta.get("preset_snapshot") or {}

        target_width = timeline_spec.get("target_width") or preset_snapshot.get("width")
        target_height = timeline_spec.get("target_height") or preset_snapshot.get("height")
        video_bitrate_kbps = timeline_spec.get("video_bitrate_kbps") or preset_snapshot.get("video_bitrate_kbps")
        framing_mode = str(timeline_spec.get("framing_mode") or preset_snapshot.get("framing_mode") or "fit").lower()

        if not target_width or not target_height:
            if render_profile in ("YT_MASTER_4K", "3840X2160"):
                target_width, target_height = 3840, 2160
            elif render_profile in ("TIKTOK_REELS_9X16", "1080X1920"):
                target_width, target_height = 1080, 1920
            elif render_profile in ("INSTAGRAM_SQUARE", "1080X1080"):
                target_width, target_height = 1080, 1080
            elif render_profile in ("LMS_WEB_720P", "1280X720"):
                target_width, target_height = 1280, 720
            else:
                target_width, target_height = 1920, 1080

        width = int(target_width)
        height = int(target_height)

        if progress_callback:
            progress_callback(30.0)

        cmd = [self.ffmpeg_path, "-y"]

        valid_placements = [
            p for p in placements if p.get("local_asset_path") and os.path.exists(p["local_asset_path"])
        ]
        audible_audio_clips = [
            ac for ac in audio_clips
            if ac.get("local_asset_path")
            and os.path.exists(ac["local_asset_path"])
            and not bool(ac.get("mute", False))
            and float(ac.get("volume", 1.0)) > 0
        ]

        for p in valid_placements:
            cmd.extend(["-i", p["local_asset_path"]])

        for ac in audible_audio_clips:
            cmd.extend(["-i", ac["local_asset_path"]])

        filter_parts = []
        has_video_map = False
        has_audio_map = False

        total_overlap = 0.0
        transition_specs = []
        if valid_placements:
            has_video_map = True
            for idx, p in enumerate(valid_placements):
                trim_in = float(p.get("trim_in", 0.0))
                eff_dur = float(p.get("effective_duration", 4.0))
                trim_out = trim_in + eff_dur
                if any(kw in framing_mode for kw in ("crop", "fill")):
                    filter_parts.append(
                        f"[{idx}:v]scale={width}:{height}:force_original_aspect_ratio=increase,"
                        f"crop={width}:{height},"
                        f"trim=start={trim_in}:end={trim_out},setpts=PTS-STARTPTS[v{idx}]"
                    )
                else:
                    filter_parts.append(
                        f"[{idx}:v]scale={width}:{height}:force_original_aspect_ratio=decrease,"
                        f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2,"
                        f"trim=start={trim_in}:end={trim_out},setpts=PTS-STARTPTS[v{idx}]"
                    )

            for i in range(len(valid_placements) - 1):
                trans = str(valid_placements[i].get("transition_to_next", "CUT")).upper()
                if trans in ("FADE", "DISSOLVE"):
                    d1 = float(valid_placements[i].get("effective_duration", 4.0))
                    d2 = float(valid_placements[i + 1].get("effective_duration", 4.0))
                    overlap = min(0.5, d1 / 2.0, d2 / 2.0)
                    total_overlap += overlap
                    transition_specs.append((trans, overlap))
                else:
                    transition_specs.append(("CUT", 0.0))

            raw_video_duration = sum(float(p.get("effective_duration", 4.0)) for p in valid_placements)
            final_timeline_duration = max(0.1, round(raw_video_duration - total_overlap, 4))

            if len(valid_placements) == 1:
                filter_parts.append("[v0]copy[vout]")
            elif all(t[0] == "CUT" for t in transition_specs):
                concat_inputs = "".join([f"[v{i}]" for i in range(len(valid_placements))])
                filter_parts.append(f"{concat_inputs}concat=n={len(valid_placements)}:v=1:a=0[vout]")
            else:
                curr_stream = "[v0]"
                curr_offset = float(valid_placements[0].get("effective_duration", 4.0))
                for i in range(len(valid_placements) - 1):
                    trans, overlap = transition_specs[i]
                    next_stream = f"[v{i+1}]"
                    out_stream = f"[vx{i+1}]" if i < len(valid_placements) - 2 else "[vout]"
                    next_dur = float(valid_placements[i + 1].get("effective_duration", 4.0))

                    if trans == "FADE":
                        offset = max(0.0, curr_offset - overlap)
                        filter_parts.append(
                            f"{curr_stream}{next_stream}xfade=transition=fade:duration={overlap:.2f}:offset={offset:.2f}{out_stream}"
                        )
                        curr_offset = curr_offset + next_dur - overlap
                    elif trans == "DISSOLVE":
                        offset = max(0.0, curr_offset - overlap)
                        filter_parts.append(
                            f"{curr_stream}{next_stream}xfade=transition=dissolve:duration={overlap:.2f}:offset={offset:.2f}{out_stream}"
                        )
                        curr_offset = curr_offset + next_dur - overlap
                    else:
                        offset = curr_offset
                        filter_parts.append(
                            f"{curr_stream}{next_stream}xfade=transition=fade:duration=0.001:offset={offset:.2f}{out_stream}"
                        )
                        curr_offset = curr_offset + next_dur
                    curr_stream = out_stream
        else:
            final_timeline_duration = total_duration

        audio_offset = len(valid_placements)
        if audible_audio_clips:
            has_audio_map = True
            for a_idx, ac in enumerate(audible_audio_clips):
                in_idx = audio_offset + a_idx
                start_time = float(ac.get("start_time", 0.0))
                delay_ms = int(start_time * 1000)
                vol = float(ac.get("volume", 1.0))
                fade_in = float(ac.get("fade_in", 0.0))
                fade_out = float(ac.get("fade_out", 0.0))
                clip_dur = float(ac["duration_seconds"]) if ac.get("duration_seconds") is not None else None

                af_parts = []
                if clip_dur is not None:
                    af_parts.append(f"atrim=end={clip_dur},asetpts=PTS-STARTPTS")
                af_parts.append(f"volume={vol}")

                if fade_in > 0:
                    af_parts.append(f"afade=t=in:st=0:d={fade_in}")
                if fade_out > 0:
                    effective_dur = clip_dur if clip_dur is not None else final_timeline_duration
                    fade_out_start = max(0.0, effective_dur - fade_out)
                    af_parts.append(f"afade=t=out:st={fade_out_start:.2f}:d={fade_out}")
                if delay_ms > 0:
                    af_parts.append(f"adelay={delay_ms}|{delay_ms}")

                audio_filter = f"[{in_idx}:a]" + ",".join(af_parts) + f"[a{a_idx}]"
                filter_parts.append(audio_filter)

            if len(audible_audio_clips) == 1:
                filter_parts.append("[a0]acopy[aout]")
            else:
                amix_inputs = "".join([f"[a{i}]" for i in range(len(audible_audio_clips))])
                filter_parts.append(
                    f"{amix_inputs}amix=inputs={len(audible_audio_clips)}:duration=longest:dropout_transition=2[aout]"
                )

        if filter_parts:
            filter_complex_str = ";".join(filter_parts)
            cmd.extend(["-filter_complex", filter_complex_str])
            if has_video_map:
                cmd.extend(["-map", "[vout]"])
            if has_audio_map:
                cmd.extend(["-map", "[aout]"])

        if not valid_placements:
            cmd.extend([
                "-f", "lavfi",
                "-i", f"color=c=black:s={width}x{height}:r=30:d={final_timeline_duration}",
                "-f", "lavfi",
                "-i", "anullsrc=r=44100:cl=stereo",
            ])

        cmd.extend([
            "-c:v", "libx264",
            "-preset", "ultrafast",
            "-tune", "zerolatency",
        ])
        if video_bitrate_kbps:
            cmd.extend(["-b:v", f"{int(video_bitrate_kbps)}k"])

        cmd.extend([
            "-c:a", "aac",
            "-t", str(final_timeline_duration),
            output_file_path,
        ])

        logger.info(f"Executing FFmpeg render command: {' '.join(cmd)}")
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

        if res.returncode != 0:
            raise RuntimeError(f"FFmpeg execution failed with code {res.returncode}: {res.stderr}")

        if progress_callback:
            progress_callback(80.0)

        if not os.path.exists(output_file_path):
            raise RuntimeError(f"FFmpeg execution completed but output file '{output_file_path}' was not generated.")

        file_size = os.path.getsize(output_file_path)

        if progress_callback:
            progress_callback(100.0)

        return {
            "duration_seconds": final_timeline_duration,
            "file_size_bytes": file_size,
            "video_codec": "h264",
            "audio_codec": "aac",
            "width": width,
            "height": height,
            "frame_rate": 30.0,
            "render_profile": render_profile,
            "placement_count": len(valid_placements),
            "audio_clip_count": len(audible_audio_clips),
            "transition_overlap_seconds": total_overlap,
            "filtergraph_used": ";".join(filter_parts) if filter_parts else None,
        }
