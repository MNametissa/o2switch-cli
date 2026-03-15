from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from o2switch_cli.cli.main import app

runner = CliRunner()


def test_completion_show_outputs_bash_script() -> None:
    result = runner.invoke(app, ["completion", "show"])
    assert result.exit_code == 0
    assert "_O2SWITCH_CLI_COMPLETE=complete_bash" in result.output
    assert "complete -o default -F _o2switch_cli_completion o2switch-cli" in result.output


def test_completion_install_and_remove_support_json_output(tmp_path: Path) -> None:
    completion_dir = tmp_path / "completions"
    bashrc_path = tmp_path / ".bashrc"

    install_result = runner.invoke(
        app,
        [
            "--json",
            "completion",
            "install",
            "--completion-dir",
            str(completion_dir),
            "--bashrc-path",
            str(bashrc_path),
        ],
    )
    install_payload = json.loads(install_result.output)
    assert install_result.exit_code == 0
    assert install_payload["shell"] == "bash"
    assert (completion_dir / "o2switch-cli").exists()
    assert not (completion_dir / "o2switch_cli").exists()

    remove_result = runner.invoke(
        app,
        [
            "--json",
            "completion",
            "remove",
            "--completion-dir",
            str(completion_dir),
            "--bashrc-path",
            str(bashrc_path),
        ],
    )
    remove_payload = json.loads(remove_result.output)
    assert remove_result.exit_code == 0
    assert remove_payload["shell"] == "bash"
    assert not (completion_dir / "o2switch-cli").exists()
    assert not (completion_dir / "o2switch_cli").exists()
