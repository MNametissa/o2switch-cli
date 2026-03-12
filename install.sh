#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$ROOT_DIR/.venv"
PYTHON_BIN="${PYTHON_BIN:-python3}"
PACKAGE_SPEC="."
RUN_SETUP=1
TEST_API=0
ENV_FILE=".env"

usage() {
  cat <<'EOF'
Usage: ./install.sh [OPTIONS]

Bootstrap o2switch-cli in a local virtual environment and optionally run the setup wizard.

Options:
  --dev             Install development dependencies too.
  --skip-setup      Do not launch `o2switch-cli config init` after install.
  --test-api        Ask the setup command to test API access after writing credentials.
  --env-file PATH   Write credentials to PATH instead of .env.
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
echo "  $VENV_DIR/bin/o2switch-cli --help"
echo "  $VENV_DIR/bin/o2switch-cli config show"
