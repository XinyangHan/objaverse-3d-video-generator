# Objaverse 3D Video Generator

A data generator for 3D video reasoning tasks using [Blender](https://www.blender.org/) and [Objaverse](https://objaverse.allenai.org/). Produces videos of 3D objects with controlled camera motions, designed for evaluating next-frame prediction models.

## 4 Task Types

| Task | Objects | Camera Motion | Tests |
|------|---------|---------------|-------|
| `shape_extrapolation` | 1 | 360-degree orbit | Predict unseen backside angles |
| `occlusion_dynamics` | 2 | 360-degree orbit | Predict occlusion patterns |
| `depth_parallax` | 3 | Lateral pan | Predict depth-dependent parallax motion |
| `zoom_consistency` | 1 | Straight zoom | Predict appearance at closer distance |

## Demos

Each task produces a video with first/last frame + prompt. Demo samples are in [`examples/demos/`](examples/demos/).

| Task | First Frame | Last Frame | Video |
|------|-------------|------------|-------|
| **Shape Extrapolation** | <img src="examples/demos/shape_extrapolation/first_frame.png" width="150"> | <img src="examples/demos/shape_extrapolation/final_frame.png" width="150"> | [ground_truth.mp4](examples/demos/shape_extrapolation/ground_truth.mp4) |
| **Occlusion Dynamics** | <img src="examples/demos/occlusion_dynamics/first_frame.png" width="150"> | <img src="examples/demos/occlusion_dynamics/final_frame.png" width="150"> | [ground_truth.mp4](examples/demos/occlusion_dynamics/ground_truth.mp4) |
| **Depth Parallax** | <img src="examples/demos/depth_parallax/first_frame.png" width="150"> | <img src="examples/demos/depth_parallax/final_frame.png" width="150"> | [ground_truth.mp4](examples/demos/depth_parallax/ground_truth.mp4) |
| **Zoom Consistency** | <img src="examples/demos/zoom_consistency/first_frame.png" width="150"> | <img src="examples/demos/zoom_consistency/final_frame.png" width="150"> | [ground_truth.mp4](examples/demos/zoom_consistency/ground_truth.mp4) |

## Quick Start

```bash
# 1. Install
pip install -e .

# 2. Install Blender 3.6 (one-time)
wget https://download.blender.org/release/Blender3.6/blender-3.6.0-linux-x64.tar.xz
tar xf blender-3.6.0-linux-x64.tar.xz -C /tmp/

# 3. Generate samples
python examples/generate.py --task shape_extrapolation --num-samples 100
python examples/generate.py --task all --num-samples 400  # 100 per task
```

## Output Format

Each sample is saved to `data/questions/{task}_task/{task_id}/`:

```
shape_extrapolation_000000/
├── first_frame.png       # First frame
├── final_frame.png       # Last frame
├── prompt.txt            # Task description
└── ground_truth.mp4      # Full video (1024x1024, 16fps, 4s)
```

## Configuration

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--task` | required | Task type or `all` |
| `--num-samples` | required | Number of videos to generate |
| `--resolution` | 1024 | Video resolution (NxN) |
| `--fps` | 16 | Frames per second |
| `--duration` | 4.0 | Video length in seconds |
| `--workers` | 16 | Parallel Blender processes |
| `--seed` | None | Random seed |
| `--objects` | bundled | Path to custom object list |

## 3D Object Assets

Bundled with 4,867 verified Objaverse UIDs (`assets/good_objects.txt`). On first run, objects are downloaded via the Objaverse API and cached locally (~5GB).

## Requirements

- Python 3.8+
- Blender 3.6+ (headless binary, not a pip package)
