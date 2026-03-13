from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

COMMAND_NAMES: tuple[str, str] = ("o2switch-cli", "o2switch_cli")
BASHRC_MARKER_START = "# >>> o2switch-cli completion >>>"
BASHRC_MARKER_END = "# <<< o2switch-cli completion <<<"


def default_bash_completion_dir() -> Path:
    return Path.home() / ".local" / "share" / "bash-completion" / "completions"


def default_bashrc_path() -> Path:
    return Path.home() / ".bashrc"


def bash_completion_script(command_name: str) -> str:
    normalized = command_name.replace("-", "_")
    function_name = f"_{normalized}_completion"
    completion_var = f"_{normalized.upper()}_COMPLETE"
    return (
        f"{function_name}() {{\n"
        "    local IFS=$'\\n'\n"
        "    COMPREPLY=( $( env COMP_WORDS=\"${COMP_WORDS[*]}\" \\\n"
        "                   COMP_CWORD=$COMP_CWORD \\\n"
        f"                   {completion_var}=complete_bash $1 ) )\n"
        "    return 0\n"
        "}\n"
        "\n"
        f"complete -o default -F {function_name} {command_name}\n"
    )


def managed_bashrc_block(
    *,
    completion_dir: Path | None = None,
    command_names: Sequence[str] = COMMAND_NAMES,
) -> str:
    resolved_completion_dir = completion_dir or default_bash_completion_dir()
    source_lines: list[str] = []
    for command_name in command_names:
        command_path = (resolved_completion_dir / command_name).expanduser()
        source_lines.append(f'    [[ -r "{command_path}" ]] && source "{command_path}"')
    rendered_lines = "\n".join(source_lines)
    return (
        f"{BASHRC_MARKER_START}\n"
        'if [[ -n "${BASH_VERSION:-}" ]]; then\n'
        f"{rendered_lines}\n"
        "fi\n"
        f"{BASHRC_MARKER_END}\n"
    )


def _strip_managed_bashrc_block(text: str) -> str:
    lines = text.splitlines()
    kept: list[str] = []
    skip = False
    for line in lines:
        if line == BASHRC_MARKER_START:
            skip = True
            continue
        if line == BASHRC_MARKER_END:
            skip = False
            continue
        if not skip:
            kept.append(line)
    return "\n".join(kept).rstrip() + ("\n" if kept else "")


def ensure_bashrc_block(
    *,
    bashrc_path: Path | None = None,
    completion_dir: Path | None = None,
    command_names: Sequence[str] = COMMAND_NAMES,
) -> Path:
    resolved_bashrc = (bashrc_path or default_bashrc_path()).expanduser()
    resolved_bashrc.parent.mkdir(parents=True, exist_ok=True)
    current = resolved_bashrc.read_text() if resolved_bashrc.exists() else ""
    stripped = _strip_managed_bashrc_block(current)
    block = managed_bashrc_block(completion_dir=completion_dir, command_names=command_names)
    rendered = stripped.rstrip()
    if rendered:
        rendered = f"{rendered}\n\n{block}"
    else:
        rendered = block
    resolved_bashrc.write_text(rendered)
    return resolved_bashrc


def remove_bashrc_block(*, bashrc_path: Path | None = None) -> Path:
    resolved_bashrc = (bashrc_path or default_bashrc_path()).expanduser()
    if not resolved_bashrc.exists():
        return resolved_bashrc
    stripped = _strip_managed_bashrc_block(resolved_bashrc.read_text())
    resolved_bashrc.write_text(stripped)
    return resolved_bashrc


def install_bash_completion(
    *,
    completion_dir: Path | None = None,
    bashrc_path: Path | None = None,
    command_names: Sequence[str] = COMMAND_NAMES,
) -> list[Path]:
    resolved_completion_dir = (completion_dir or default_bash_completion_dir()).expanduser()
    resolved_completion_dir.mkdir(parents=True, exist_ok=True)
    written_files: list[Path] = []
    for command_name in command_names:
        target = resolved_completion_dir / command_name
        target.write_text(bash_completion_script(command_name))
        written_files.append(target)
    ensure_bashrc_block(
        bashrc_path=bashrc_path,
        completion_dir=resolved_completion_dir,
        command_names=command_names,
    )
    return written_files


def remove_bash_completion(
    *,
    completion_dir: Path | None = None,
    bashrc_path: Path | None = None,
    command_names: Sequence[str] = COMMAND_NAMES,
) -> list[Path]:
    resolved_completion_dir = (completion_dir or default_bash_completion_dir()).expanduser()
    removed_files: list[Path] = []
    for command_name in command_names:
        target = resolved_completion_dir / command_name
        if target.exists():
            target.unlink()
            removed_files.append(target)
    remove_bashrc_block(bashrc_path=bashrc_path)
    return removed_files
