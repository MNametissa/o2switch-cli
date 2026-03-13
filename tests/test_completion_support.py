from __future__ import annotations

from pathlib import Path

from o2switch_cli.cli.completion_support import (
    COMMAND_NAMES,
    bash_completion_script,
    install_bash_completion,
    remove_bash_completion,
)


def test_bash_completion_script_uses_expected_command_and_env_var() -> None:
    script = bash_completion_script("o2switch-cli")
    assert "_o2switch_cli_completion()" in script
    assert "_O2SWITCH_CLI_COMPLETE=complete_bash" in script
    assert "complete -o default -F _o2switch_cli_completion o2switch-cli" in script


def test_install_and_remove_bash_completion_manage_files_and_bashrc(tmp_path: Path) -> None:
    completion_dir = tmp_path / "completions"
    bashrc_path = tmp_path / ".bashrc"

    written = install_bash_completion(completion_dir=completion_dir, bashrc_path=bashrc_path)

    assert [path.name for path in written] == list(COMMAND_NAMES)
    for path in written:
        assert path.exists()
        assert "complete -o default" in path.read_text()

    bashrc = bashrc_path.read_text()
    assert "# >>> o2switch-cli completion >>>" in bashrc
    assert str(completion_dir / "o2switch-cli") in bashrc
    assert str(completion_dir / "o2switch_cli") in bashrc
    assert "['" not in bashrc
    assert '[[ -r "' in bashrc
    assert 'source "' in bashrc

    removed = remove_bash_completion(completion_dir=completion_dir, bashrc_path=bashrc_path)

    assert {path.name for path in removed} == set(COMMAND_NAMES)
    assert not (completion_dir / "o2switch-cli").exists()
    assert not (completion_dir / "o2switch_cli").exists()
    assert "# >>> o2switch-cli completion >>>" not in bashrc_path.read_text()


def test_managed_bashrc_block_renders_shell_lines_not_python_list(tmp_path: Path) -> None:
    completion_dir = tmp_path / "completions"
    block = install_bash_completion(completion_dir=completion_dir, bashrc_path=tmp_path / ".bashrc")
    del block
    rendered = (tmp_path / ".bashrc").read_text()
    assert "['" not in rendered
    assert ", '" not in rendered
