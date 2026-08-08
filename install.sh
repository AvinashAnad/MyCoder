#!/bin/bash
# Install MyCoder as a standalone command available system-wide.
#
# Run from the cloned repo root:
#   ./install.sh
#
# This will:
#   1. Install uv if not present
#   2. Create a venv and install all dependencies via uv
#   3. Create a launcher at ~/.local/bin/mycoder
#   4. Add ~/.local/bin to your PATH if not already there

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_DIR="$SCRIPT_DIR/.venv"
INSTALL_DIR="$HOME/.local/bin"

echo ""
echo "  ╔══════════════════════════════════════╗"
echo "  ║   MyCoder — Local AI Coding Agent    ║"
echo "  ╚══════════════════════════════════════╝"
echo ""

# --- Step 1: ensure uv ---
echo "[1/4] Checking for uv..."

if ! command -v uv &>/dev/null; then
    echo "      Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"
    if ! command -v uv &>/dev/null; then
        echo "  ✗ Failed to install uv. Install manually: https://docs.astral.sh/uv/"
        exit 1
    fi
fi

echo "      uv $(uv --version)"

# --- Step 2: venv ---
echo "[2/4] Creating venv..."

uv venv "$VENV_DIR" --python 3.10 2>/dev/null || uv venv "$VENV_DIR" 2>/dev/null || true
echo "      $VENV_DIR"

# --- Step 3: install deps ---
echo "[3/4] Installing MyCoder..."

uv pip install --python "$VENV_DIR/bin/python" -e "$SCRIPT_DIR" 2>&1 | tail -1
echo "      All dependencies installed."

# --- Step 4: launcher + PATH ---
echo "[4/4] Creating launcher..."

mkdir -p "$INSTALL_DIR"

cat > "$INSTALL_DIR/mycoder" << LAUNCHER
#!/bin/bash
exec "$VENV_DIR/bin/mycoder" "\$@"
LAUNCHER

chmod +x "$INSTALL_DIR/mycoder"

# Detect shell rc
if [[ "$SHELL" == */zsh ]]; then
    SHELL_RC="$HOME/.zshrc"
elif [[ "$SHELL" == */bash ]]; then
    SHELL_RC="$HOME/.bashrc"
else
    SHELL_RC="$HOME/.profile"
fi

if [[ ":$PATH:" != *":$INSTALL_DIR:"* ]]; then
    if ! grep -q "$INSTALL_DIR" "$SHELL_RC" 2>/dev/null; then
        echo "" >> "$SHELL_RC"
        echo "# MyCoder" >> "$SHELL_RC"
        echo "export PATH=\"$INSTALL_DIR:\$PATH\"" >> "$SHELL_RC"
    fi
    export PATH="$INSTALL_DIR:$PATH"
    echo "      Added $INSTALL_DIR to $SHELL_RC"
else
    echo "      PATH already configured."
fi

# --- Done ---
echo ""
echo "  ✓ MyCoder installed!"
echo ""
echo "  Open a new terminal, or run:  source $SHELL_RC"
echo "  Then launch from anywhere:    mycoder"
echo ""
