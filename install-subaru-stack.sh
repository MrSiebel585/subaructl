#!/bin/bash
set -euo pipefail

USERNAME=$(logname)

if [ "$EUID" -ne 0 ]; then
  exec sudo "$BASH" "$0" "$@"
fi

SOURCE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET_DIR="/opt/subaru"

echo "Installing Subaru ECU Stack v1.0 from $SOURCE_DIR to $TARGET_DIR..."

if [ ! -d "$SOURCE_DIR/tactrix" ] || [ ! -d "$SOURCE_DIR/FastECU" ]; then
  echo "Source must contain tactrix/, FastECU/ etc. Run from project root."
  exit 1
fi

if [ -d "$TARGET_DIR" ]; then
  echo "Backup existing..."
  mv "$TARGET_DIR" "$TARGET_DIR.backup.$(date +%Y%m%d_%H%M%S)"
fi

rsync -av --exclude='.git*' --exclude='install-subaru-stack.sh*' "$SOURCE_DIR/" "$TARGET_DIR/"

chown -R "$USERNAME:$USERNAME" "$TARGET_DIR"

chmod +x "$TARGET_DIR"/subaructl "$TARGET_DIR"/bin/* "$TARGET_DIR"/blackpearlctl "$TARGET_DIR"/autorun_bt_elm327.sh "$TARGET_DIR"/ssm2csv_run.sh "$TARGET_DIR"/imprezadash/*.sh

# Ensure serial permissions
usermod -a -G dialout "$USERNAME"
echo "Added $USERNAME to dialout group for serial access. Log out and log back in to apply."

# Symlinks - core project tools only (skip venv bins to avoid conflicts)
ln -sf "$TARGET_DIR/subaructl" /usr/local/bin/subaructl
ln -sf "$TARGET_DIR/blackpearlctl" /usr/local/bin/blackpearlctl
ln -sf "$TARGET_DIR/bin/bp-*.sh" /usr/local/bin/
ln -sf "$TARGET_DIR/imprezadash/imprezadash.sh" /usr/local/bin/imprezadash 2>/dev/null || ln -sf "$TARGET_DIR/imprezadash/main.py" /usr/local/bin/imprezadash

# Man & desktop
mkdir -p /usr/local/man/man1
cp "$TARGET_DIR/subaructl.1" /usr/local/man/man1/
mandb
cp "$TARGET_DIR/WRX_Dash.desktop" /usr/share/applications/

# Venvs
for proj in imprezadash ecuextractor wrxloggerwarningsystem; do
  if [ -d "$TARGET_DIR/$proj" ]; then
    pushd "$TARGET_DIR/$proj" 
    python3 -m venv .venv
    . .venv/bin/activate
    pip install --upgrade pip
    for req in requirements*.txt pyproject.toml; do
      [ -f "$req" ] && pip install -r "$req" || pip install -e . || true
    done
    popd
  fi
done

# FastECU
pushd "$TARGET_DIR/FastECU"
apt-get update -qq
apt-get install -y -qq qtbase5-dev qttools5-dev-tools build-essential libusb-1.0-0-dev zlib1g-dev xz-utils
qmake FastECU.pro
make clean
make -j"$(nproc)"
# Install to local
mkdir -p "$TARGET_DIR/FastECU/bin"
cp FastECU "$TARGET_DIR/FastECU/bin/"
popd

# Services
for svc in "$TARGET_DIR"/ecu_maps/*.service "$TARGET_DIR"/tactrix/services/*.service; do
  [ -f "$svc" ] && cp "$svc" /etc/systemd/system/ && systemctl enable "$(basename "$svc" .service)"
done
systemctl daemon-reload

echo 'export PATH="/opt/subaru/bin:$PATH"' >> "/home/$USERNAME/.bashrc"

echo "[✓] Subaru Stack installed!"
echo "Log out/in for PATH."
echo "Test: subaructl --help | blackpearlctl detect"

