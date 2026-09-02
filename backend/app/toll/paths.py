"""Shared filesystem-path resolution for the toll layer."""

from pathlib import Path

from app.core.config import get_settings

DEMO_VIDEO = "demo_video.mp4"


def videos_dir() -> Path:
    """Folder served at /videos and read by the pipeline for the demo camera.

    Defaults to the project's ``videos/`` when ANPR_TOLL_VIDEOS_DIR is unset.
    Resolved to an absolute path so the pipeline (which runs from a different
    working directory) can open the file.
    """
    settings = get_settings()
    if settings.toll_videos_dir:
        return Path(settings.toll_videos_dir).resolve()
    # this file: <project>/backend/app/toll/paths.py
    # parents: [toll, app, backend, <project>]
    root = Path(__file__).resolve().parents[3]
    return (root / "videos").resolve()


def demo_video_path() -> str:
    return str(videos_dir() / DEMO_VIDEO)
