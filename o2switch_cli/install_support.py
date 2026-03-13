from __future__ import annotations

from hashlib import sha256
from pathlib import Path


def compute_install_state(root_dir: Path, package_spec: str) -> str:
    resolved_root = root_dir.expanduser().resolve()
    pyproject_path = resolved_root / "pyproject.toml"

    hasher = sha256()
    hasher.update(str(resolved_root).encode("utf-8"))
    hasher.update(b"\0")
    hasher.update(package_spec.encode("utf-8"))
    hasher.update(b"\0")
    hasher.update(pyproject_path.read_bytes())
    return hasher.hexdigest()
