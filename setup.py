from setuptools import setup, find_packages
from pathlib import Path

readme = Path("README.md").read_text() if Path("README.md").exists() else ""
requirements = []
if Path("requirements.txt").exists():
    with open("requirements.txt") as f:
        requirements = [line.strip() for line in f if line.strip() and not line.startswith("#")]

setup(
    name="objaverse-3d-video-generator",
    version="1.0.0",
    description="3D video reasoning task generator using Blender + Objaverse",
    long_description=readme,
    long_description_content_type="text/markdown",
    packages=find_packages(include=["core", "core.*", "shared", "shared.*", "tasks", "tasks.*"]),
    python_requires=">=3.8",
    install_requires=requirements,
)
