#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$ROOT_DIR/.venv"
LOCAL_BIN_DIR="${HOME}/.local/bin"
ENV_FILE="$ROOT_DIR/.env"
REMOVE_ENV=0
REMOVE_STATE=0
YES=0

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

rm -rf "$VENV_DIR"

for launcher in "$LOCAL_BIN_DIR/o2switch-cli" "$LOCAL_BIN_DIR/o2switch_cli"; do
  if [[ -e "$launcher" || -L "$launcher" ]]; then
    rm -f "$launcher"
  fi
done

if [[ "$REMOVE_ENV" -eq 1 ]]; then
  rm -f "$ENV_FILE"
fi

if [[ "$REMOVE_STATE" -eq 1 ]]; then
  rm -rf "$STATE_DIR"
fi

echo "==> Uninstall completed"
echo
echo "Shell note:"
echo "  If your current shell still resolves an old launcher path, run:"
echo "  hash -r"
echo "  or open a new shell session."
