#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$ROOT_DIR/.venv"
LOCAL_BIN_DIR="${HOME}/.local/bin"
COMPLETION_DIR="${HOME}/.local/share/bash-completion/completions"
ENV_FILE="$ROOT_DIR/.env"
REMOVE_ENV=0
REMOVE_STATE=0
YES=0
BASHRC_FILE="${HOME}/.bashrc"
BASHRC_MARKER_START="# >>> o2switch-cli >>>"
BASHRC_MARKER_END="# <<< o2switch-cli <<<"
COMPLETION_MARKER_START="# >>> o2switch-cli completion >>>"
COMPLETION_MARKER_END="# <<< o2switch-cli completion <<<"

remove_bashrc_block_by_markers() {
  local start_marker="$1"
  local end_marker="$2"
  local tmp_file
  if [[ ! -f "$BASHRC_FILE" ]] || ! grep -Fq "$start_marker" "$BASHRC_FILE"; then
    return
  fi
  tmp_file="$(mktemp)"
  awk -v start="$start_marker" -v end="$end_marker" '
    $0 == start { skip = 1; next }
    $0 == end { skip = 0; next }
    skip != 1 { print }
  ' "$BASHRC_FILE" > "$tmp_file"
  mv "$tmp_file" "$BASHRC_FILE"
}

remove_bashrc_path_block() {
  if [[ ! -f "$BASHRC_FILE" ]] || ! grep -Fq "$BASHRC_MARKER_START" "$BASHRC_FILE"; then
    return
  fi
  remove_bashrc_block_by_markers "$BASHRC_MARKER_START" "$BASHRC_MARKER_END"
  echo "==> Updated $BASHRC_FILE"
  echo "    Removed managed o2switch-cli PATH block"
}

remove_bashrc_completion_block() {
  if [[ ! -f "$BASHRC_FILE" ]] || ! grep -Fq "$COMPLETION_MARKER_START" "$BASHRC_FILE"; then
    return
  fi
  remove_bashrc_block_by_markers "$COMPLETION_MARKER_START" "$COMPLETION_MARKER_END"
  echo "==> Updated $BASHRC_FILE"
  echo "    Removed managed o2switch-cli completion block"
}

print_shell_refresh_note() {
  echo "==> Reload shell configuration"
  echo "    Run: source \"$BASHRC_FILE\" && hash -r"
}

default_audit_log_path() {
  if [[ -x "$VENV_DIR/bin/python" ]]; then
    "$VENV_DIR/bin/python" - <<'PY'
from pathlib import Path
from platformdirs import user_state_dir

print(Path(user_state_dir("o2switch-cli")) / "audit.jsonl")
PY
  else
    printf '%s\n' "${HOME}/.local/state/o2switch-cli/audit.jsonl"
  fi
}

usage() {
  cat <<'EOF'
Usage: ./uninstall.sh [OPTIONS]

Remove the local o2switch-cli installation created by ./install.sh.

Options:
  --purge-config   Also remove the repository .env file.
  --purge-state    Also remove the default audit log file and its state directory.
  --yes            Do not ask for confirmation.
  --help           Show this message and exit.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --purge-config)
      REMOVE_ENV=1
      shift
      ;;
    --purge-state)
      REMOVE_STATE=1
      shift
      ;;
    --yes)
      YES=1
      shift
      ;;
    --help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

AUDIT_LOG_PATH="$(default_audit_log_path)"
STATE_DIR="$(dirname "$AUDIT_LOG_PATH")"

if [[ "$YES" -ne 1 ]]; then
  echo "This will remove:"
  echo "  $VENV_DIR"
  echo "  $LOCAL_BIN_DIR/o2switch-cli"
  echo "  $LOCAL_BIN_DIR/o2switch_cli"
  echo "  $COMPLETION_DIR/o2switch-cli"
  echo "  $COMPLETION_DIR/o2switch_cli"
  if [[ "$REMOVE_ENV" -eq 1 ]]; then
    echo "  $ENV_FILE"
  fi
  if [[ "$REMOVE_STATE" -eq 1 ]]; then
    echo "  $STATE_DIR"
  fi
  read -r -p "Continue? [y/N] " reply
  case "${reply:-}" in
    y|Y|yes|YES) ;;
    *)
      echo "Uninstall cancelled."
      exit 0
      ;;
  esac
fi

if [[ -x "$VENV_DIR/bin/o2switch-cli" ]]; then
  if ! "$VENV_DIR/bin/o2switch-cli" completion remove --shell bash >/dev/null; then
    rm -f "$COMPLETION_DIR/o2switch-cli" "$COMPLETION_DIR/o2switch_cli"
    remove_bashrc_completion_block
  fi
else
  rm -f "$COMPLETION_DIR/o2switch-cli" "$COMPLETION_DIR/o2switch_cli"
  remove_bashrc_completion_block
fi

rm -rf "$VENV_DIR"

for launcher in "$LOCAL_BIN_DIR/o2switch-cli" "$LOCAL_BIN_DIR/o2switch_cli"; do
  if [[ -e "$launcher" || -L "$launcher" ]]; then
    rm -f "$launcher"
  fi
done

remove_bashrc_path_block

if [[ "$REMOVE_ENV" -eq 1 ]]; then
  rm -f "$ENV_FILE"
fi

if [[ "$REMOVE_STATE" -eq 1 ]]; then
  rm -rf "$STATE_DIR"
fi

echo "==> Uninstall completed"
print_shell_refresh_note
