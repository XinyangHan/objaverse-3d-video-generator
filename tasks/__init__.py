"""Task registry."""

from . import shape_extrapolation, occlusion_dynamics, depth_parallax, zoom_consistency

TASK_REGISTRY = {
    "shape_extrapolation": shape_extrapolation,
    "occlusion_dynamics": occlusion_dynamics,
    "depth_parallax": depth_parallax,
    "zoom_consistency": zoom_consistency,
}

TASK_NAMES = list(TASK_REGISTRY.keys())


def get_task(name: str):
    """Get task module by name. Returns module with TaskConfig, TaskGenerator, get_prompt."""
    if name not in TASK_REGISTRY:
        raise ValueError(f"Unknown task: {name}. Available: {TASK_NAMES}")
    return TASK_REGISTRY[name]
