"""Depth Parallax: 3 objects at different depths, lateral camera."""

import random
import tempfile
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import List, Optional

from PIL import Image
from pydantic import Field

from core import BaseGenerator, GenerationConfig, TaskPair
from shared.renderer import find_blender, render_with_retry
from shared.objects import load_objects

# ---- Config ----

class TaskConfig(GenerationConfig):
    domain: str = Field(default="depth_parallax")
    image_size: tuple[int, int] = Field(default=(1024, 1024))
    fps: int = Field(default=16)
    duration: float = Field(default=4.0)
    camera_distance: float = Field(default=3.0)
    camera_elevation: float = Field(default=20.0)
    lateral_range: float = Field(default=3.5)
    camera_forward_distance: float = Field(default=5.5)
    camera_height: float = Field(default=1.8)
    look_at: list = Field(default=[0.1, 1.0, 0])
    object_positions: list = Field(default=[[-1.0, -0.5, 0], [0.3, 1.0, 0], [1.2, 2.5, 0]])
    object_scales: list = Field(default=[1.8, 1.8, 1.8])
    workers: int = Field(default=16)
    blender_path: Optional[str] = Field(default=None)
    timeout: int = Field(default=600)
    min_video_size: int = Field(default=50_000)
    max_retries: int = Field(default=3)
    object_list: Optional[str] = Field(default=None)

# ---- Prompts ----

PROMPTS = [
    "A camera moves laterally across a scene containing three 3D objects at different depths. Near objects appear to move faster than far objects (parallax effect). Given the first 75% of the camera's lateral movement, predict the remaining frames.",
    "Three 3D objects are placed at different distances from the camera. The camera slides from left to right, creating a depth parallax effect. Predict the final 25% of the video based on the depth relationships observed so far.",
    "This video shows a lateral camera pan across a scene with objects at varying depths. Closer objects shift more in the frame than distant ones. Generate the remaining frames, maintaining correct parallax motion for each depth layer.",
    "Watch a camera translate sideways through a 3D scene. Objects at different distances move at different apparent speeds due to depth parallax. Predict the next frames showing the correct relative motion of near and far objects.",
]

def get_prompt() -> str:
    return random.choice(PROMPTS)

# ---- Generator ----

NUM_OBJECTS = 3

def _build_task_config(config: TaskConfig) -> dict:
    return {
        "task_type": "depth_parallax",
        "resolution": config.image_size[0],
        "fps": config.fps,
        "duration": config.duration,
        "camera_distance": config.camera_distance,
        "camera_elevation": config.camera_elevation,
        "lateral_range": config.lateral_range,
        "camera_forward_distance": config.camera_forward_distance,
        "camera_height": config.camera_height,
        "look_at": config.look_at,
        "object_positions": config.object_positions,
        "object_scales": config.object_scales,
    }


def _render_one(args):
    task_id, blender, all_objs, task_cfg, min_sz, retries, timeout, work_dir = args
    out = Path(work_dir) / task_id
    out.mkdir(parents=True, exist_ok=True)
    objs = random.sample(all_objs, min(NUM_OBJECTS, len(all_objs)))
    ok = render_with_retry(blender, task_cfg, objs, all_objs, str(out),
                           NUM_OBJECTS, min_sz, retries, timeout)
    return {"task_id": task_id, "output_dir": str(out), "success": ok}


class TaskGenerator(BaseGenerator):
    def __init__(self, config: TaskConfig):
        super().__init__(config)
        self.blender = find_blender(config.blender_path)
        self.objects = load_objects(config.object_list)
        self._work_dir = tempfile.mkdtemp(prefix="depth_para_")
        self._task_cfg = _build_task_config(config)
        print(f"Blender: {self.blender}")
        print(f"Objects: {len(self.objects)} verified 3D models")

    def generate_task_pair(self, task_id: str) -> TaskPair:
        result = _render_one((
            task_id, self.blender, self.objects, self._task_cfg,
            self.config.min_video_size, self.config.max_retries,
            self.config.timeout, self._work_dir,
        ))
        return self._result_to_pair(result)

    def generate_dataset(self) -> List[TaskPair]:
        n = self.config.num_samples
        workers = min(self.config.workers, n)
        print(f"\nGenerating {n} samples with {workers} parallel workers...")

        args_list = [
            (f"{self.config.domain}_{i:06d}", self.blender, self.objects,
             self._task_cfg, self.config.min_video_size, self.config.max_retries,
             self.config.timeout, self._work_dir)
            for i in range(n)
        ]

        pairs, ok, fail = [], 0, 0
        t0 = time.time()
        with ProcessPoolExecutor(max_workers=workers) as ex:
            futs = {ex.submit(_render_one, a): a[0] for a in args_list}
            for fut in as_completed(futs):
                r = fut.result()
                if r["success"]:
                    pairs.append(self._result_to_pair(r))
                    ok += 1
                else:
                    fail += 1
                done = ok + fail
                if done % 10 == 0 or done == n:
                    el = time.time() - t0
                    rate = done / el if el > 0 else 0
                    eta = (n - done) / rate / 60 if rate > 0 else 0
                    print(f"  [{done}/{n}] ok={ok} fail={fail} rate={rate:.2f}/s ETA={eta:.1f}min")
        print(f"\nDone in {(time.time()-t0)/60:.1f}min. Success: {ok}/{n} ({100*ok/max(n,1):.1f}%)")
        return pairs

    def _result_to_pair(self, result):
        if not result["success"]:
            blank = Image.new("RGB", self.config.image_size, (0, 0, 0))
            return TaskPair(task_id=result["task_id"], domain=self.config.domain,
                            prompt=get_prompt(), first_image=blank, final_image=blank)
        d = Path(result["output_dir"])
        return TaskPair(
            task_id=result["task_id"], domain=self.config.domain, prompt=get_prompt(),
            first_image=Image.open(d / "first_frame.png").convert("RGB"),
            final_image=Image.open(d / "final_frame.png").convert("RGB"),
            ground_truth_video=str(d / "ground_truth.mp4"),
        )
