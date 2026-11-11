#!/usr/bin/env bash
# Install Mincut for the current user on Ubuntu.
set -euo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
data_home="${XDG_DATA_HOME:-$HOME/.local/share}"
autostart_dir="${XDG_CONFIG_HOME:-$HOME/.config}/autostart"

echo "==> Installing the Python package"
python3 -m pip install --user --upgrade "$here" ||
  python3 -m pip install --user --upgrade --break-system-packages "$here"

echo "==> Adding the application entry"
install -d "$data_home/applications" "$autostart_dir"
install -m 644 "$here/desktop/mincut.desktop" "$data_home/applications/mincut.desktop"
install -m 644 "$here/desktop/mincut-autostart.desktop" "$autostart_dir/mincut.desktop"

if command -v gnome-extensions >/dev/null 2>&1; then
  echo "==> Installing the GNOME Shell bridge (needed on Wayland)"
  ext_dir="$data_home/gnome-shell/extensions/mincut@ubuntu-mincut"
  install -d "$ext_dir"
  install -m 644 "$here/gnome-extension/mincut@ubuntu-mincut/"* "$ext_dir/"
  gnome-extensions enable mincut@ubuntu-mincut 2>/dev/null ||
    echo "   Enable it after logging out and back in: gnome-extensions enable mincut@ubuntu-mincut"
fi

echo "==> Registering the keyboard shortcut"
"$HOME/.local/bin/mincut" setup || true

echo
echo "Done. Start it now with: mincut"
echo "The bezel opens with Ctrl+Shift+V (change it in Preferences)."
