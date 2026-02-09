"""
Unified Blender rendering script for all 4 task types.

Runs as a Blender subprocess — self-contained, no external imports.

Usage (called by shared/renderer.py, not directly):
    blender --background --python shared/blender_render.py -- \
        --task_config '{"task_type":"shape_extrapolation",...}' \
        --object_paths '["path1.glb"]' \
        --output_dir /path/to/output
"""

import argparse
import json
import math
import sys
from pathlib import Path

try:
    import bpy
    import mathutils
except ImportError:
    print("Error: Must run inside Blender")
    sys.exit(1)


# ============================================================
# Scene Setup
# ============================================================

def reset_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def setup_render_settings(resolution=1024):
    scene = bpy.context.scene
    scene.render.resolution_x = resolution
    scene.render.resolution_y = resolution
    scene.render.resolution_percentage = 100
    scene.render.engine = "BLENDER_EEVEE"
    scene.eevee.taa_render_samples = 8
    scene.eevee.use_gtao = True
    scene.eevee.use_ssr = False
    scene.eevee.use_bloom = False
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.film_transparent = False


def setup_background(color=(0.15, 0.15, 0.18)):
    world = bpy.data.worlds.new("Background")
    bpy.context.scene.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes.get("Background")
    if bg:
        bg.inputs["Color"].default_value = (*color, 1.0)
        bg.inputs["Strength"].default_value = 1.0


def setup_ground_plane(z=-1.2):
    bpy.ops.mesh.primitive_plane_add(size=30, location=(0, 0, z))
    plane = bpy.context.active_object
    plane.name = "GroundPlane"
    mat = bpy.data.materials.new(name="GroundMat")
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = (0.35, 0.35, 0.38, 1.0)
        bsdf.inputs["Roughness"].default_value = 0.85
    plane.data.materials.append(mat)


def setup_lighting(energy=5.0):
    bpy.ops.object.light_add(type="SUN", location=(5, -5, 10))
    key = bpy.context.active_object
    key.name = "KeyLight"
    key.data.energy = energy
    key.rotation_euler = (math.radians(45), 0, math.radians(-45))

    bpy.ops.object.light_add(type="SUN", location=(-5, -5, 5))
    fill = bpy.context.active_object
    fill.name = "FillLight"
    fill.data.energy = energy * 0.5
    fill.rotation_euler = (math.radians(45), 0, math.radians(135))

    bpy.ops.object.light_add(type="SUN", location=(0, 5, 5))
    rim = bpy.context.active_object
    rim.name = "RimLight"
    rim.data.energy = energy * 0.8
    rim.rotation_euler = (math.radians(-45), 0, math.radians(180))


def setup_camera(distance=3.5, elevation=25.0):
    bpy.ops.object.camera_add()
    camera = bpy.context.active_object
    camera.name = "RenderCamera"
    elev_rad = math.radians(elevation)
    x = distance * math.cos(elev_rad)
    z = distance * math.sin(elev_rad)
    camera.location = (x, 0, z)
    direction = mathutils.Vector((0, 0, 0)) - camera.location
    rot_quat = direction.to_track_quat("-Z", "Y")
    camera.rotation_euler = rot_quat.to_euler()
    bpy.context.scene.camera = camera
    camera.data.lens = 35
    camera.data.sensor_width = 32
    return camera


# ============================================================
# Object Import
# ============================================================

def import_object(filepath):
    filepath = str(filepath)
    if filepath.endswith(".glb") or filepath.endswith(".gltf"):
        bpy.ops.import_scene.gltf(filepath=filepath)
    elif filepath.endswith(".obj"):
        bpy.ops.import_scene.obj(filepath=filepath)
    else:
        raise ValueError(f"Unsupported format: {filepath}")
    return [obj for obj in bpy.context.selected_objects if obj.type == "MESH"]


def ensure_visible_material(obj):
    if obj.type != "MESH":
        return
    if not obj.data.materials or all(m is None for m in obj.data.materials):
        mat = bpy.data.materials.new(name="DefaultVisible")
        mat.use_nodes = True
        bsdf = mat.node_tree.nodes.get("Principled BSDF")
        if bsdf:
            bsdf.inputs["Base Color"].default_value = (0.6, 0.45, 0.3, 1.0)
            bsdf.inputs["Roughness"].default_value = 0.5
        obj.data.materials.append(mat)


def import_single_object(path, target_size=2.0):
    bpy.ops.object.select_all(action='DESELECT')
    objects = import_object(path)
    if not objects:
        return []

    for obj in objects:
        ensure_visible_material(obj)

    all_verts = []
    for obj in objects:
        for v in obj.data.vertices:
            all_verts.append(obj.matrix_world @ v.co)

    total_verts = sum(len(obj.data.vertices) for obj in objects)
    if total_verts < 4:
        print(f"  REJECT: too few vertices ({total_verts})")
        return []

    if all_verts:
        mn = [min(v[j] for v in all_verts) for j in range(3)]
        mx = [max(v[j] for v in all_verts) for j in range(3)]
        center = [(mn[j] + mx[j]) / 2 for j in range(3)]
        dims = [mx[j] - mn[j] for j in range(3)]
        size = max(dims)

        if size < 0.001:
            print(f"  REJECT: degenerate object (size={size})")
            return []

        if size > 0:
            sf = target_size / size
            for obj in objects:
                obj.location.x -= center[0]
                obj.location.y -= center[1]
                obj.location.z -= center[2]
                obj.scale *= sf
    return objects


def import_and_place_objects(object_paths, positions, scales):
    all_groups = []
    for i, path in enumerate(object_paths):
        bpy.ops.object.select_all(action='DESELECT')
        objects = import_object(path)
        if not objects:
            continue

        for obj in objects:
            ensure_visible_material(obj)

        bpy.ops.object.empty_add(type='PLAIN_AXES')
        parent = bpy.context.active_object
        parent.name = f"Object_{i}"
        for obj in objects:
            obj.parent = parent

        all_verts = []
        for obj in objects:
            if obj.type == "MESH":
                for v in obj.data.vertices:
                    all_verts.append(obj.matrix_world @ v.co)

        if all_verts:
            mn = [min(v[j] for v in all_verts) for j in range(3)]
            mx = [max(v[j] for v in all_verts) for j in range(3)]
            center = [(mn[j] + mx[j]) / 2 for j in range(3)]
            size = max(mx[j] - mn[j] for j in range(3))

            if size > 0:
                target_scale = scales[i] if i < len(scales) else 1.5
                sf = target_scale / size
                parent.location = (-center[0]*sf, -center[1]*sf, -center[2]*sf)
                parent.scale = (sf, sf, sf)

        if i < len(positions):
            pos = positions[i]
            parent.location.x += pos[0]
            parent.location.y += pos[1]
            parent.location.z += pos[2]

        all_groups.append((parent, objects))
    return all_groups


# ============================================================
# Animations
# ============================================================

def create_orbit_animation(camera, num_frames, config):
    """360-degree orbit (shape_extrapolation, occlusion_dynamics)."""
    scene = bpy.context.scene
    scene.frame_start = 1
    scene.frame_end = num_frames

    distance = config.get("camera_distance", 3.5)
    elevation = config.get("camera_elevation", 25.0)
    elev_rad = math.radians(elevation)
    rotations = config.get("rotations", 1.0)

    for frame in range(1, num_frames + 1):
        scene.frame_set(frame)
        progress = (frame - 1) / num_frames
        azimuth = progress * rotations * 2 * math.pi

        x = distance * math.cos(elev_rad) * math.cos(azimuth)
        y = distance * math.cos(elev_rad) * math.sin(azimuth)
        z = distance * math.sin(elev_rad)

        camera.location = (x, y, z)
        direction = mathutils.Vector((0, 0, 0)) - camera.location
        rot_quat = direction.to_track_quat("-Z", "Y")
        camera.rotation_euler = rot_quat.to_euler()

        camera.keyframe_insert(data_path="location", frame=frame)
        camera.keyframe_insert(data_path="rotation_euler", frame=frame)


def create_parallax_animation(camera, num_frames, config):
    """Lateral camera movement (depth_parallax)."""
    scene = bpy.context.scene
    scene.frame_start = 1
    scene.frame_end = num_frames

    lateral_range = config.get("lateral_range", 3.5)
    camera_y = config.get("camera_forward_distance", 5.5)
    camera_z = config.get("camera_height", 1.8)
    look_at = mathutils.Vector(config.get("look_at", [0.1, 1.0, 0]))

    for frame in range(1, num_frames + 1):
        scene.frame_set(frame)
        progress = (frame - 1) / num_frames
        x = -lateral_range / 2 + lateral_range * progress
        y = -camera_y
        z = camera_z

        camera.location = (x, y, z)
        direction = look_at - camera.location
        rot_quat = direction.to_track_quat("-Z", "Y")
        camera.rotation_euler = rot_quat.to_euler()

        camera.keyframe_insert(data_path="location", frame=frame)
        camera.keyframe_insert(data_path="rotation_euler", frame=frame)


def create_zoom_animation(camera, num_frames, config):
    """Pure zoom toward object (zoom_consistency)."""
    scene = bpy.context.scene
    scene.frame_start = 1
    scene.frame_end = num_frames

    start_distance = config.get("start_distance", 4.0)
    end_distance = config.get("end_distance", 1.8)
    elevation = config.get("camera_elevation", 20.0)
    azimuth = config.get("camera_azimuth", 15.0)
    elev_rad = math.radians(elevation)
    azim_rad = math.radians(azimuth)

    for frame in range(1, num_frames + 1):
        scene.frame_set(frame)
        progress = (frame - 1) / num_frames
        smooth_progress = 0.5 - 0.5 * math.cos(progress * math.pi)
        distance = start_distance + (end_distance - start_distance) * smooth_progress

        x = distance * math.cos(elev_rad) * math.cos(azim_rad)
        y = distance * math.cos(elev_rad) * math.sin(azim_rad)
        z = distance * math.sin(elev_rad)

        camera.location = (x, y, z)
        direction = mathutils.Vector((0, 0, 0)) - camera.location
        rot_quat = direction.to_track_quat("-Z", "Y")
        camera.rotation_euler = rot_quat.to_euler()

        camera.keyframe_insert(data_path="location", frame=frame)
        camera.keyframe_insert(data_path="rotation_euler", frame=frame)


# ============================================================
# Render
# ============================================================

def render_video(output_path, fps=16):
    scene = bpy.context.scene
    scene.render.image_settings.file_format = "FFMPEG"
    scene.render.ffmpeg.format = "MPEG4"
    scene.render.ffmpeg.codec = "H264"
    scene.render.ffmpeg.constant_rate_factor = "MEDIUM"
    scene.render.fps = fps
    scene.render.filepath = output_path
    bpy.ops.render.render(animation=True)


def save_keyframes(output_dir, num_frames):
    scene = bpy.context.scene
    for name, idx in [("first_frame.png", 1), ("final_frame.png", num_frames)]:
        scene.frame_set(idx)
        scene.render.filepath = str(Path(output_dir) / name)
        scene.render.image_settings.file_format = "PNG"
        bpy.ops.render.render(write_still=True)


# ============================================================
# Main
# ============================================================

def main():
    argv = sys.argv
    if "--" in argv:
        argv = argv[argv.index("--") + 1:]
    else:
        argv = []

    parser = argparse.ArgumentParser()
    parser.add_argument("--task_config", type=str, required=True)
    parser.add_argument("--object_paths", type=str, required=True)
    parser.add_argument("--output_dir", type=str, required=True)
    args = parser.parse_args(argv)

    config = json.loads(args.task_config)
    object_paths = json.loads(args.object_paths)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    task_type = config.get("task_type", "shape_extrapolation")
    resolution = config.get("resolution", 1024)
    fps = config.get("fps", 16)
    duration = config.get("duration", 4.0)
    num_frames = int(fps * duration)

    print(f"Task: {task_type}")
    print(f"  Objects: {len(object_paths)}, Resolution: {resolution}, Frames: {num_frames}")

    # Setup scene
    reset_scene()
    setup_render_settings(resolution=resolution)
    setup_background()
    setup_ground_plane()
    setup_lighting()

    # Import objects
    if task_type in ("shape_extrapolation", "zoom_consistency"):
        objects = import_single_object(object_paths[0], target_size=2.0)
        if not objects:
            print("IMPORT_FAILED")
            sys.exit(1)
    else:
        positions = config.get("object_positions", [])
        scales = config.get("object_scales", [])
        object_groups = import_and_place_objects(object_paths, positions, scales)
        if not object_groups:
            print("IMPORT_FAILED")
            sys.exit(1)

    # Camera
    camera = setup_camera(
        distance=config.get("camera_distance", 3.5),
        elevation=config.get("camera_elevation", 25.0),
    )

    # Animation
    if task_type in ("shape_extrapolation", "occlusion_dynamics"):
        create_orbit_animation(camera, num_frames, config)
    elif task_type == "depth_parallax":
        create_parallax_animation(camera, num_frames, config)
    elif task_type == "zoom_consistency":
        create_zoom_animation(camera, num_frames, config)
    else:
        print(f"Unknown task type: {task_type}")
        sys.exit(1)

    # Render
    print("Rendering video...")
    render_video(str(output_dir / "ground_truth.mp4"), fps=fps)

    print("Saving keyframes...")
    save_keyframes(output_dir, num_frames)

    # Metadata
    metadata = {
        "task_type": task_type,
        "num_objects": len(object_paths),
        "resolution": resolution,
        "fps": fps,
        "duration": duration,
        "num_frames": num_frames,
        "config": config,
    }
    (output_dir / "metadata.json").write_text(json.dumps(metadata, indent=2))

    print("RENDER_SUCCESS")


if __name__ == "__main__":
    main()
