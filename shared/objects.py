"""Object loader: resolves Objaverse UIDs to local .glb paths."""

from pathlib import Path
from typing import List, Optional

_PACKAGE_DIR = Path(__file__).resolve().parent.parent
_DEFAULT_ASSETS = _PACKAGE_DIR / "assets" / "good_objects.txt"


def load_objects(object_list: Optional[str] = None) -> List[str]:
    """
    Load 3D object paths.

    If object_list points to a file with absolute .glb paths, uses them directly.
    If it contains Objaverse UIDs (32-char hex), resolves via objaverse API.
    """
    path = Path(object_list) if object_list else _DEFAULT_ASSETS
    if not path.exists():
        raise FileNotFoundError(f"Object list not found: {path}")

    with open(path) as f:
        lines = [line.strip() for line in f if line.strip()]

    if not lines:
        raise ValueError(f"Empty object list: {path}")

    # Detect format: absolute paths vs UIDs
    sample = lines[0]
    if "/" in sample or sample.endswith(".glb"):
        # Already absolute paths
        valid = [p for p in lines if Path(p).exists()]
        if not valid:
            raise FileNotFoundError(f"No valid .glb files found from {path}")
        return valid

    # Objaverse UIDs — resolve to local paths
    import objaverse

    print(f"Resolving {len(lines)} Objaverse UIDs to local paths...")
    uid_to_path = objaverse.load_objects(uids=lines, download_processes=8)

    valid = []
    for uid in lines:
        p = uid_to_path.get(uid)
        if p and Path(p).exists():
            valid.append(str(p))

    if not valid:
        raise FileNotFoundError("No objects could be resolved. Check Objaverse cache.")

    print(f"  Resolved {len(valid)}/{len(lines)} objects")
    return valid
