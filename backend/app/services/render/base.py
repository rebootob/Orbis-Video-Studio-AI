from abc import ABC, abstractmethod
from typing import Dict, Any, Callable, Optional


class RenderExecutor(ABC):
    """Abstract interface for video timeline render engines."""

    @abstractmethod
    def render_timeline(
        self,
        timeline_spec: Dict[str, Any],
        scratch_dir: str,
        output_file_path: str,
        progress_callback: Optional[Callable[[float], None]] = None,
    ) -> Dict[str, Any]:
        """
        Executes rendering for given assembly timeline specification.

        Args:
            timeline_spec: Dictionary containing placement specs, audio clips, duration, transition metadata.
            scratch_dir: Directory path on worker disk containing downloaded media assets.
            output_file_path: Target absolute path on worker disk for master MP4 output file.
            progress_callback: Optional callback receiving float percentage (0.0 to 100.0).

        Returns:
            Dict containing metadata: duration_seconds, file_size_bytes, video_codec, audio_codec, width, height, frame_rate.
        """
        pass
