from __future__ import annotations

from pathlib import Path

from o2switch_cli.install_support import compute_install_state


def test_compute_install_state_changes_with_package_spec(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text("[project]\nname = 'demo'\n")
    base = compute_install_state(tmp_path, ".")
    dev = compute_install_state(tmp_path, ".[dev]")
    assert base != dev


def test_compute_install_state_changes_with_pyproject_content(tmp_path: Path) -> None:
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text("[project]\nname = 'demo'\n")
    before = compute_install_state(tmp_path, ".")
    pyproject.write_text("[project]\nname = 'demo'\nversion = '0.2.0'\n")
    after = compute_install_state(tmp_path, ".")
    assert before != after
