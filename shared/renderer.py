"""Python-side Blender subprocess caller with retry logic."""

import json
import random
import shutil
import subprocess
from pathlib import Path
from typing import List, Optional

_PACKAGE_DIR = Path(__file__).resolve().parent.parent
_BLENDER_SCRIPT = str(_PACKAGE_DIR / "shared" / "blender_render.py")


def find_blender(blender_path: Optional[str] = None) -> str:
    """Find Blender binary."""
    if blender_path and Path(blender_path).exists():
        return blender_path

    candidates = [
        "/tmp/blender-3.6.0-linux-x64/blender",
        "/usr/local/bin/blender",
        "/usr/bin/blender",
        shutil.which("blender"),
    ]
    for path in candidates:
        if path and Path(path).exists():
            return str(path)

    raise FileNotFoundError(
        "Blender not found. Install Blender 3.6+ or pass --blender path.\n"
        "Quick install:\n"
        "  wget https://download.blender.org/release/Blender3.6/blender-3.6.0-linux-x64.tar.xz\n"
        "  tar xf blender-3.6.0-linux-x64.tar.xz -C /tmp/"
    )


def render_video_task(
    blender_path: str,
    task_config: dict,
    object_paths: List[str],
    output_dir: str,
    timeout: int = 600,
) -> bool:
    """
    Call Blender subprocess to render one video.

    Args:
        blender_path: Path to Blender binary
        task_config: Dict with task_type, resolution, fps, duration, camera params
        object_paths: List of .glb file paths
        output_dir: Where to save output files
        timeout: Subprocess timeout in seconds

    Returns:
        True if render succeeded
    """
    cmd = [
        blender_path, "--background",
        "--python", _BLENDER_SCRIPT, "--",
        "--task_config", json.dumps(task_config),
        "--object_paths", json.dumps(object_paths),
        "--output_dir", output_dir,
    ]
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout
        )
        return result.returncode == 0 and "RENDER_SUCCESS" in result.stdout
    except (subprocess.TimeoutExpired, Exception):
        return False


def render_with_retry(
    blender_path: str,
    task_config: dict,
    object_paths: List[str],
    all_objects: List[str],
    output_dir: str,
    num_objects: int = 1,
    min_video_size: int = 50_000,
    max_retries: int = 3,
    timeout: int = 600,
) -> bool:
    """
    Render with automatic retry using different objects on failure.

    Returns True if a valid video (> min_video_size bytes) was produced.
    """
    out = Path(output_dir)
    current_objs = object_paths

    for attempt in range(max_retries):
        # Clean previous attempt
        for f in out.glob("*"):
            f.unlink()

        success = render_video_task(
            blender_path, task_config, current_objs, str(out), timeout
        )

        video_file = out / "ground_truth.mp4"
        if success and video_file.exists() and video_file.stat().st_size > min_video_size:
            return True

        # Retry with different objects
        if attempt < max_retries - 1 and all_objects:
            current_objs = random.sample(
                all_objects, min(num_objects, len(all_objects))
            )

    return False
