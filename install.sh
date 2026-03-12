#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$ROOT_DIR/.venv"
PYTHON_BIN="${PYTHON_BIN:-python3}"
PACKAGE_SPEC="."
RUN_SETUP=1
TEST_API=0
ENV_FILE=".env"
LINK_LOCAL_BIN=1
LOCAL_BIN_DIR="${HOME}/.local/bin"
BASHRC_FILE="${HOME}/.bashrc"
BASHRC_MARKER_START="# >>> o2switch-cli >>>"
BASHRC_MARKER_END="# <<< o2switch-cli <<<"

managed_bashrc_block() {
  cat <<'EOF'
# >>> o2switch-cli >>>
if [[ ":$PATH:" != *":$HOME/.local/bin:"* ]]; then
  export PATH="$HOME/.local/bin:$PATH"
fi
# <<< o2switch-cli <<<
EOF
}

bashrc_has_local_bin_path() {
  [[ -f "$BASHRC_FILE" ]] && grep -Eq '(\$HOME|\$\{HOME\}|~)/\.local/bin' "$BASHRC_FILE"
}

ensure_bashrc_path_block() {
  mkdir -p "$(dirname "$BASHRC_FILE")"
  touch "$BASHRC_FILE"
  if grep -Fq "$BASHRC_MARKER_START" "$BASHRC_FILE"; then
    return
  fi
  if bashrc_has_local_bin_path; then
    echo "==> Detected existing ~/.local/bin PATH config in $BASHRC_FILE"
    return
  fi
  {
    printf '\n'
    managed_bashrc_block
    printf '\n'
  } >> "$BASHRC_FILE"
  echo "==> Updated $BASHRC_FILE"
  echo "    Added managed PATH block for ~/.local/bin"
}

print_shell_refresh_note() {
  echo "==> Reload shell configuration"
  echo "    Run: source \"$BASHRC_FILE\" && hash -r"
}

usage() {
  cat <<'EOF'
Usage: ./install.sh [OPTIONS]

Bootstrap o2switch-cli in a local virtual environment and optionally run the setup wizard.

Options:
  --dev             Install development dependencies too.
  --skip-setup      Do not launch `o2switch-cli config init` after install.
  --test-api        Ask the setup command to test API access after writing credentials.
  --env-file PATH   Write credentials to PATH instead of .env.
  --no-link         Do not publish launchers into ~/.local/bin.
  --help            Show this message and exit.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dev)
      PACKAGE_SPEC=".[dev]"
      shift
      ;;
    --skip-setup)
      RUN_SETUP=0
      shift
      ;;
    --test-api)
      TEST_API=1
      shift
      ;;
    --env-file)
      ENV_FILE="$2"
      shift 2
      ;;
    --no-link)
      LINK_LOCAL_BIN=0
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

echo "==> Creating virtual environment in $VENV_DIR"
"$PYTHON_BIN" -m venv "$VENV_DIR"

echo "==> Installing o2switch-cli"
"$VENV_DIR/bin/python" -m pip install --upgrade pip
if [[ "$PACKAGE_SPEC" == ".[dev]" ]]; then
  "$VENV_DIR/bin/python" -m pip install -e "${ROOT_DIR}[dev]"
else
  "$VENV_DIR/bin/python" -m pip install -e "$ROOT_DIR"
fi

echo "==> Installed successfully"
echo "    Binary: $VENV_DIR/bin/o2switch-cli"

if [[ "$LINK_LOCAL_BIN" -eq 1 ]]; then
  mkdir -p "$LOCAL_BIN_DIR"
  ln -sfn "$VENV_DIR/bin/o2switch-cli" "$LOCAL_BIN_DIR/o2switch-cli"
  ln -sfn "$VENV_DIR/bin/o2switch_cli" "$LOCAL_BIN_DIR/o2switch_cli"
  ensure_bashrc_path_block
  echo "==> Published launchers"
  echo "    $LOCAL_BIN_DIR/o2switch-cli"
  echo "    $LOCAL_BIN_DIR/o2switch_cli"
  case ":$PATH:" in
    *":$LOCAL_BIN_DIR:"*) ;;
    *)
      echo "==> Warning: $LOCAL_BIN_DIR is not active in the current shell PATH"
      print_shell_refresh_note
      ;;
  esac
fi

if [[ "$RUN_SETUP" -eq 1 ]]; then
  if [[ -t 0 ]]; then
    echo "==> Launching setup wizard"
    SETUP_ARGS=(config init --path "$ENV_FILE")
    if [[ "$TEST_API" -eq 1 ]]; then
      SETUP_ARGS+=(--test-api)
    fi
    "$VENV_DIR/bin/o2switch-cli" "${SETUP_ARGS[@]}"
  else
    echo "==> Non-interactive shell detected, skipping setup wizard"
    echo "    Run: $VENV_DIR/bin/o2switch-cli config init --path $ENV_FILE"
  fi
fi

echo
echo "Next steps:"
if [[ "$LINK_LOCAL_BIN" -eq 1 ]]; then
  echo "  o2switch-cli --help"
  echo "  o2switch_cli --help"
  echo "  o2switch-cli config show"
  echo "  ./uninstall.sh"
else
  echo "  $VENV_DIR/bin/o2switch-cli --help"
  echo "  $VENV_DIR/bin/o2switch-cli config show"
  echo "  ./uninstall.sh"
fi
print_shell_refresh_note
