"""Shape Extrapolation: single object, 360-degree orbit."""

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
    domain: str = Field(default="shape_extrapolation")
    image_size: tuple[int, int] = Field(default=(1024, 1024))
    fps: int = Field(default=16)
    duration: float = Field(default=4.0)
    camera_distance: float = Field(default=3.5)
    camera_elevation: float = Field(default=25.0)
    rotations: float = Field(default=1.0)
    workers: int = Field(default=16)
    blender_path: Optional[str] = Field(default=None)
    timeout: int = Field(default=600)
    min_video_size: int = Field(default=50_000)
    max_retries: int = Field(default=3)
    object_list: Optional[str] = Field(default=None)


# ---- Prompts ----

PROMPTS = [
    "A camera orbits 360 degrees around a 3D object. Given the first 75% of the video (270 degrees of rotation), predict what the object looks like from the remaining unseen angles. Generate the final 25% of frames showing the back side of the object.",
    "This video shows a 3D object being viewed from a camera that rotates around it. The video captures the first three-quarters of a full orbit. Predict the next-frame sequence that completes the remaining quarter of the orbit, revealing the previously unseen side of the object.",
    "A 3D object is filmed by a camera performing a circular orbit. You are shown 75% of the rotation. Extrapolate the object's appearance for the remaining 25% of angles to complete the full 360-degree view.",
    "Watch a camera slowly orbit around a single 3D object. The video shows 270 degrees of the orbit. Your task is to predict the final 90 degrees of rotation, showing what the back of the object looks like based on the geometry and textures visible so far.",
    "A single 3D object is captured by an orbiting camera. Given the majority of the orbit as context, generate the remaining frames that complete the full rotation around the object.",
]

def get_prompt() -> str:
    return random.choice(PROMPTS)


# ---- Generator ----

NUM_OBJECTS = 1

def _build_task_config(config: TaskConfig) -> dict:
    return {
        "task_type": "shape_extrapolation",
        "resolution": config.image_size[0],
        "fps": config.fps,
        "duration": config.duration,
        "camera_distance": config.camera_distance,
        "camera_elevation": config.camera_elevation,
        "rotations": config.rotations,
    }


def _render_one(args):
    task_id, blender, all_objs, task_cfg, min_sz, retries, timeout, work_dir = args
    out = Path(work_dir) / task_id
    out.mkdir(parents=True, exist_ok=True)
    obj = [random.choice(all_objs)]
    ok = render_with_retry(blender, task_cfg, obj, all_objs, str(out),
                           NUM_OBJECTS, min_sz, retries, timeout)
    return {"task_id": task_id, "output_dir": str(out), "success": ok}


class TaskGenerator(BaseGenerator):
    def __init__(self, config: TaskConfig):
        super().__init__(config)
        self.blender = find_blender(config.blender_path)
        self.objects = load_objects(config.object_list)
        self._work_dir = tempfile.mkdtemp(prefix="shape_extrap_")
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

        return self._parallel_render(args_list, workers, n)

    def _parallel_render(self, args_list, workers, n):
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
