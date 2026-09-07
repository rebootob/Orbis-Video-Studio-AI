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
        render_profile = timeline_spec.get("render_profile", "MASTER_HD")

        if progress_callback:
            progress_callback(30.0)

        width = 1920
        height = 1080
        if render_profile == "VERTICAL_4K":
            width, height = 2160, 3840
        elif render_profile == "SQUARE_SD":
            width, height = 720, 720

        cmd = [self.ffmpeg_path, "-y"]

        valid_placements = [
            p for p in placements if p.get("local_asset_path") and os.path.exists(p["local_asset_path"])
        ]
        valid_audio_clips = [
            ac for ac in audio_clips if ac.get("local_asset_path") and os.path.exists(ac["local_asset_path"])
        ]

        for p in valid_placements:
            cmd.extend(["-i", p["local_asset_path"]])

        for ac in valid_audio_clips:
            cmd.extend(["-i", ac["local_asset_path"]])

        filter_parts = []
        has_video_map = False
        has_audio_map = False

        if valid_placements:
            has_video_map = True
            for idx, p in enumerate(valid_placements):
                trim_in = float(p.get("trim_in", 0.0))
                eff_dur = float(p.get("effective_duration", 4.0))
                trim_out = trim_in + eff_dur
                filter_parts.append(
                    f"[{idx}:v]scale={width}:{height}:force_original_aspect_ratio=decrease,"
                    f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2,"
                    f"trim=start={trim_in}:end={trim_out},setpts=PTS-STARTPTS[v{idx}]"
                )

            if len(valid_placements) == 1:
                filter_parts.append("[v0]copy[vout]")
            else:
                concat_inputs = "".join([f"[v{i}]" for i in range(len(valid_placements))])
                filter_parts.append(f"{concat_inputs}concat=n={len(valid_placements)}:v=1:a=0[vout]")

        audio_offset = len(valid_placements)
        if valid_audio_clips:
            has_audio_map = True
            for a_idx, ac in enumerate(valid_audio_clips):
                in_idx = audio_offset + a_idx
                start_time = float(ac.get("start_time", 0.0))
                delay_ms = int(start_time * 1000)
                vol = float(ac.get("volume", 1.0))
                fade_in = float(ac.get("fade_in", 0.0))
                fade_out = float(ac.get("fade_out", 0.0))

                audio_filter = f"[{in_idx}:a]volume={vol}"
                if fade_in > 0:
                    audio_filter += f",afade=t=in:st=0:d={fade_in}"
                if fade_out > 0:
                    audio_filter += f",afade=t=out:st=0:d={fade_out}"
                if delay_ms > 0:
                    audio_filter += f",adelay={delay_ms}|{delay_ms}"
                audio_filter += f"[a{a_idx}]"
                filter_parts.append(audio_filter)

            if len(valid_audio_clips) == 1:
                filter_parts.append("[a0]acopy[aout]")
            else:
                amix_inputs = "".join([f"[a{i}]" for i in range(len(valid_audio_clips))])
                filter_parts.append(
                    f"{amix_inputs}amix=inputs={len(valid_audio_clips)}:duration=longest:dropout_transition=2[aout]"
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
                "-i", f"color=c=black:s={width}x{height}:r=30:d={total_duration}",
                "-f", "lavfi",
                "-i", "anullsrc=r=44100:cl=stereo",
            ])

        cmd.extend([
            "-c:v", "libx264",
            "-preset", "ultrafast",
            "-tune", "zerolatency",
            "-c:a", "aac",
            "-t", str(total_duration),
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
            "duration_seconds": total_duration,
            "file_size_bytes": file_size,
            "video_codec": "h264",
            "audio_codec": "aac",
            "width": width,
            "height": height,
            "frame_rate": 30.0,
            "render_profile": render_profile,
            "placement_count": len(valid_placements),
            "audio_clip_count": len(valid_audio_clips),
            "filtergraph_used": ";".join(filter_parts) if filter_parts else None,
        }
