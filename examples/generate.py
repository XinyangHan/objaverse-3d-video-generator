#!/usr/bin/env python3
"""
Objaverse 3D Video Reasoning Data Generator

Generates video reasoning tasks using Blender + Objaverse 3D objects.

Usage:
    python examples/generate.py --task shape_extrapolation --num-samples 100
    python examples/generate.py --task occlusion_dynamics --num-samples 100
    python examples/generate.py --task depth_parallax --num-samples 100
    python examples/generate.py --task zoom_consistency --num-samples 100
    python examples/generate.py --task all --num-samples 400  # 100 per task
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core import OutputWriter
from tasks import get_task, TASK_NAMES


def run_task(task_name, args):
    """Run a single task generator."""
    task_module = get_task(task_name)

    config = task_module.TaskConfig(
        num_samples=args.num_samples,
        random_seed=args.seed,
        output_dir=Path(args.output),
        image_size=(args.resolution, args.resolution),
        fps=args.fps,
        duration=args.duration,
        workers=args.workers,
        blender_path=args.blender,
        object_list=args.objects,
    )

    generator = task_module.TaskGenerator(config)
    tasks = generator.generate_dataset()

    writer = OutputWriter(Path(args.output))
    writer.write_dataset(tasks)

    print(f"  -> {len(tasks)} tasks in {args.output}/{config.domain}_task/")
    return len(tasks)


def main():
    parser = argparse.ArgumentParser(
        description="Generate 3D video reasoning tasks",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"Available tasks: {', '.join(TASK_NAMES)}, all",
    )
    parser.add_argument("--task", type=str, required=True,
                        help=f"Task type: {', '.join(TASK_NAMES)}, or 'all'")
    parser.add_argument("--num-samples", type=int, required=True,
                        help="Number of samples (split evenly for 'all')")
    parser.add_argument("--output", type=str, default="data/questions")
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--workers", type=int, default=16)
    parser.add_argument("--resolution", type=int, default=1024)
    parser.add_argument("--fps", type=int, default=16)
    parser.add_argument("--duration", type=float, default=4.0)
    parser.add_argument("--blender", type=str, default=None)
    parser.add_argument("--objects", type=str, default=None)

    args = parser.parse_args()

    print(f"Objaverse 3D Video Generator")
    print(f"  Task: {args.task}")
    print(f"  Samples: {args.num_samples}")
    print(f"  Resolution: {args.resolution}x{args.resolution}, {args.fps}fps x {args.duration}s")
    print()

    if args.task == "all":
        per_task = args.num_samples // len(TASK_NAMES)
        total = 0
        for name in TASK_NAMES:
            print(f"=== {name} ({per_task} samples) ===")
            args.num_samples = per_task
            total += run_task(name, args)
        print(f"\nTotal: {total} tasks across {len(TASK_NAMES)} types")
    else:
        run_task(args.task, args)

    print("Done!")


if __name__ == "__main__":
    main()
