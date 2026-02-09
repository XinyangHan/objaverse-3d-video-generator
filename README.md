# Objaverse 3D Video Generator

A data generator for 3D video reasoning tasks using [Blender](https://www.blender.org/) and [Objaverse](https://objaverse.allenai.org/). Produces videos of 3D objects with controlled camera motions, designed for evaluating next-frame prediction models.

---

## Demos

| Task | First Frame | Last Frame | Video |
|------|-------------|------------|-------|
| **Shape Extrapolation** | <img src="examples/demos/shape_extrapolation/first_frame.png" width="150"> | <img src="examples/demos/shape_extrapolation/final_frame.png" width="150"> | [ground_truth.mp4](examples/demos/shape_extrapolation/ground_truth.mp4) |
| **Occlusion Dynamics** | <img src="examples/demos/occlusion_dynamics/first_frame.png" width="150"> | <img src="examples/demos/occlusion_dynamics/final_frame.png" width="150"> | [ground_truth.mp4](examples/demos/occlusion_dynamics/ground_truth.mp4) |
| **Depth Parallax** | <img src="examples/demos/depth_parallax/first_frame.png" width="150"> | <img src="examples/demos/depth_parallax/final_frame.png" width="150"> | [ground_truth.mp4](examples/demos/depth_parallax/ground_truth.mp4) |
| **Zoom Consistency** | <img src="examples/demos/zoom_consistency/first_frame.png" width="150"> | <img src="examples/demos/zoom_consistency/final_frame.png" width="150"> | [ground_truth.mp4](examples/demos/zoom_consistency/ground_truth.mp4) |

Demo samples are in [`examples/demos/`](examples/demos/).

---

## Quick Start

### Step 1: Install Python Dependencies

```bash
# Clone the repository
git clone https://github.com/XinyangHan/objaverse-3d-video-generator.git
cd objaverse-3d-video-generator

# Install Python dependencies
pip install -r requirements.txt
# OR install in editable mode
pip install -e .
```

### Step 2: Install Blender 3.6+

#### macOS (Homebrew)
```bash
brew install --cask blender
```

#### Linux
```bash
wget https://download.blender.org/release/Blender3.6/blender-3.6.0-linux-x64.tar.xz
tar xf blender-3.6.0-linux-x64.tar.xz -C /tmp/
```

#### Verify Installation
```bash
blender --version  # Should show Blender 3.6.0 or higher
```

### Step 3: Fix SSL Certificate (macOS with Python.org Python)

If you installed Python from python.org, you may need to install SSL certificates:

```bash
# Python 3.12
/Applications/Python\ 3.12/Install\ Certificates.command

# Python 3.11
/Applications/Python\ 3.11/Install\ Certificates.command
```

Or double-click `Install Certificates.command` in the Python folder in Applications.

### Step 4: Generate Samples

```bash
# Generate 10 samples (first run will download 3D objects, ~5GB, may take hours)
python examples/generate.py --task shape_extrapolation --num-samples 10

# Generate all task types
python examples/generate.py --task all --num-samples 40  # 10 per task
```

**First Run Note**: The first execution will download 4,867 3D models from Objaverse (~5GB). This is a one-time download and will be cached in `~/.objaverse/`. Subsequent runs will use the cached files.

---

## Available Tasks

### Shape Extrapolation Task (3D形状外推)

A 3D spatial reasoning task where a camera orbits around a single object. The model must predict the unseen backside.

**Task Description:**
- **Input:** Video of a camera orbiting 270 degrees around a 3D object (first 75% of frames)
- **Output:** Predict the remaining 90 degrees of rotation showing the unseen backside of the object

**Example Prompt:**
> "A camera orbits 360 degrees around a 3D object. Given the first 75% of the video (270 degrees of rotation), predict what the object looks like from the remaining unseen angles. Generate the final 25% of frames showing the back side of the object."

**Usage:**
```bash
python examples/generate.py --task shape_extrapolation --num-samples 100
python examples/generate.py --task shape_extrapolation --num-samples 100 --seed 42 --workers 8
```

**Configuration Options:**
| Parameter | Default | Description |
|-----------|---------|-------------|
| `camera_distance` | 3.5 | Distance from camera to object |
| `camera_elevation` | 25.0 | Camera elevation angle (degrees) |
| `rotations` | 1.0 | Number of full orbits |
| `resolution` | 1024 | Video resolution (NxN) |
| `fps` | 16 | Frames per second |
| `duration` | 4.0 | Video length in seconds |

**Output Structure:**
```
data/questions/shape_extrapolation_task/{task_id}/
├── first_frame.png       # First frame of orbit (front view)
├── final_frame.png       # Last frame of orbit (back to front)
├── prompt.txt            # Task instructions
└── ground_truth.mp4      # Full 360-degree orbit video
```

---

### Occlusion Dynamics Task (3D遮挡动态)

A 3D reasoning task with two objects where the camera orbits around both. The model must predict how occlusion patterns change.

**Task Description:**
- **Input:** Video of a camera orbiting 270 degrees around two 3D objects (first 75% of frames)
- **Output:** Predict the remaining frames showing how one object progressively occludes the other

**Example Prompt:**
> "A camera orbits around two 3D objects. As the camera moves, one object progressively occludes the other. Given the first 75% of the video, predict how the occlusion pattern changes in the remaining frames."

**Usage:**
```bash
python examples/generate.py --task occlusion_dynamics --num-samples 100
```

**Configuration Options:**
| Parameter | Default | Description |
|-----------|---------|-------------|
| `camera_distance` | 4.5 | Distance from camera to scene center |
| `camera_elevation` | 20.0 | Camera elevation angle (degrees) |
| `object_positions` | [[0.8,0,0],[-0.8,0,0]] | Positions of the two objects |
| `object_scales` | [1.5, 1.5] | Scale factors for each object |
| `resolution` | 1024 | Video resolution (NxN) |

**Output Structure:**
```
data/questions/occlusion_dynamics_task/{task_id}/
├── first_frame.png       # Initial view of both objects
├── final_frame.png       # Final view showing occlusion state
├── prompt.txt            # Task instructions
└── ground_truth.mp4      # Full orbit video with occlusion changes
```

---

### Depth Parallax Task (3D深度视差)

A 3D depth reasoning task with three objects at different depths. A lateral camera pan reveals parallax motion.

**Task Description:**
- **Input:** Video of a camera panning laterally across three objects at different depths (first 75% of frames)
- **Output:** Predict the remaining frames, where near objects move faster than far objects (parallax effect)

**Example Prompt:**
> "A camera moves laterally across a scene containing three 3D objects at different depths. Near objects appear to move faster than far objects (parallax effect). Given the first 75% of the camera's lateral movement, predict the remaining frames."

**Usage:**
```bash
python examples/generate.py --task depth_parallax --num-samples 100
```

**Configuration Options:**
| Parameter | Default | Description |
|-----------|---------|-------------|
| `camera_distance` | 3.0 | Base camera distance |
| `lateral_range` | 3.5 | Total lateral movement range |
| `camera_forward_distance` | 5.5 | Camera forward offset |
| `camera_height` | 1.8 | Camera height |
| `object_positions` | [[-1,-0.5,0],[0.3,1,0],[1.2,2.5,0]] | Positions at increasing depths |
| `object_scales` | [1.8, 1.8, 1.8] | Scale factors |
| `resolution` | 1024 | Video resolution (NxN) |

**Output Structure:**
```
data/questions/depth_parallax_task/{task_id}/
├── first_frame.png       # Left-most camera position
├── final_frame.png       # Right-most camera position
├── prompt.txt            # Task instructions
└── ground_truth.mp4      # Full lateral pan video
```

---

### Zoom Consistency Task (3D缩放一致性)

A 3D consistency task where the camera zooms steadily toward a single object. The model must predict appearance at closer range.

**Task Description:**
- **Input:** Video of a camera zooming toward a 3D object from a fixed angle (first 75% of frames)
- **Output:** Predict the remaining frames showing the object at closer range with increasing detail

**Example Prompt:**
> "A camera zooms steadily toward a 3D object from a fixed angle. Given the first 75% of the zoom sequence, predict the remaining frames showing the object at closer range with increasing detail."

**Usage:**
```bash
python examples/generate.py --task zoom_consistency --num-samples 100
```

**Configuration Options:**
| Parameter | Default | Description |
|-----------|---------|-------------|
| `camera_elevation` | 20.0 | Camera elevation angle (degrees) |
| `camera_azimuth` | 15.0 | Camera azimuth angle (degrees) |
| `start_distance` | 4.0 | Starting camera distance |
| `end_distance` | 1.8 | Final camera distance (closest) |
| `resolution` | 1024 | Video resolution (NxN) |
| `fps` | 16 | Frames per second |
| `duration` | 4.0 | Video length in seconds |

**Output Structure:**
```
data/questions/zoom_consistency_task/{task_id}/
├── first_frame.png       # Far view of object
├── final_frame.png       # Close-up view of object
├── prompt.txt            # Task instructions
└── ground_truth.mp4      # Full zoom-in video
```

---

## Global Configuration

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--task` | required | Task type (`shape_extrapolation`, `occlusion_dynamics`, `depth_parallax`, `zoom_consistency`, or `all`) |
| `--num-samples` | required | Number of videos to generate |
| `--resolution` | 1024 | Video resolution (NxN) |
| `--fps` | 16 | Frames per second |
| `--duration` | 4.0 | Video length in seconds |
| `--workers` | 16 | Parallel Blender processes |
| `--seed` | None | Random seed for reproducibility |
| `--objects` | bundled | Path to custom object list |
| `--blender` | auto-detect | Path to Blender binary |
| `--output` | `data/questions` | Output directory |

---

## 3D Object Assets

Bundled with 4,867 verified [Objaverse](https://objaverse.allenai.org/) UIDs (`assets/good_objects.txt`). On first run, objects are downloaded via the Objaverse API and cached locally (~5GB).

To use custom objects, provide a file with one Objaverse UID (or absolute `.glb` path) per line:
```bash
python examples/generate.py --task all --num-samples 100 --objects my_objects.txt
```

---

## Project Structure

```
objaverse-3d-video-generator/
├── core/                          # Core framework (from template-data-generator)
│   ├── base_generator.py         # Abstract base class + GenerationConfig
│   ├── schemas.py                # TaskPair data model
│   └── output_writer.py          # File output utilities
├── shared/                        # Shared Blender rendering pipeline
│   ├── blender_render.py         # Blender-internal script (runs as subprocess)
│   ├── renderer.py               # Python-side Blender subprocess caller
│   └── objects.py                # Objaverse UID resolver + object loader
├── tasks/                         # Task-specific configs, prompts, generators
│   ├── shape_extrapolation.py
│   ├── occlusion_dynamics.py
│   ├── depth_parallax.py
│   └── zoom_consistency.py
├── assets/
│   └── good_objects.txt          # 4,867 verified Objaverse UIDs
├── examples/
│   ├── generate.py               # Unified entry point
│   └── demos/                    # Demo samples (1 per task)
├── requirements.txt
├── setup.py
└── README.md
```

---

## Requirements

- Python 3.8+
- Blender 3.6+ (headless binary, not a pip package)
- ~5GB disk for Objaverse object cache (first run)

---

## License

MIT License. See [LICENSE](LICENSE) for details.
