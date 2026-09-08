import os
import shutil
import subprocess
from typing import Optional


class FFmpegSubtitleBurnInProcessor:
    """Deterministic post-render subtitle burn-in stage for Core V1.

    This processor consumes an already-rendered MP4 plus a UTF-8 SRT file and
    emits a replacement MP4. It does not perform ASR, translation, or any
    provider/network call.
    """

    def __init__(self, ffmpeg_path: str = "ffmpeg"):
        self.ffmpeg_path = ffmpeg_path

    @staticmethod
    def _escape_subtitles_filter_path(path: str) -> str:
        normalized = os.path.abspath(path).replace("\\", "/")
        return normalized.replace(":", "\\:").replace("'", "\\'")

    def burn_in(self, input_file_path: str, srt_file_path: str, output_file_path: str) -> None:
        ffmpeg = shutil.which(self.ffmpeg_path)
        if not ffmpeg:
            raise RuntimeError(f"FFmpeg binary '{self.ffmpeg_path}' not found for subtitle burn-in")
        if not os.path.isfile(input_file_path):
            raise RuntimeError(f"Subtitle burn-in input video missing: {input_file_path}")
        if not os.path.isfile(srt_file_path):
            raise RuntimeError(f"Subtitle burn-in SRT missing: {srt_file_path}")

        escaped_srt = self._escape_subtitles_filter_path(srt_file_path)
        cmd = [
            ffmpeg,
            "-y",
            "-i",
            input_file_path,
            "-vf",
            f"subtitles=filename='{escaped_srt}'",
            "-c:v",
            "libx264",
            "-preset",
            "ultrafast",
            "-c:a",
            "copy",
            output_file_path,
        ]
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if result.returncode != 0:
            raise RuntimeError(
                f"FFmpeg subtitle burn-in failed with code {result.returncode}: {result.stderr}"
            )
        if not os.path.isfile(output_file_path) or os.path.getsize(output_file_path) <= 0:
            raise RuntimeError("FFmpeg subtitle burn-in completed without a usable output file")
