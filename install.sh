#!/usr/bin/env bash
# Install Mincut for the current user on Ubuntu.
set -euo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
data_home="${XDG_DATA_HOME:-$HOME/.local/share}"
autostart_dir="${XDG_CONFIG_HOME:-$HOME/.config}/autostart"

echo "==> Installing the Python package"
python3 -m pip install --user --upgrade "$here" ||
  python3 -m pip install --user --upgrade --break-system-packages "$here"

# The desktop session's PATH does not always contain ~/.local/bin, so the
# entries point at the binary by absolute path instead of the bare `mincut`.
if command -v mincut >/dev/null 2>&1; then
  mincut_bin="$(command -v mincut)"
else
  user_scripts="$(python3 -c 'import sysconfig; print(sysconfig.get_path("scripts", "posix_user"))')"
  mincut_bin="$user_scripts/mincut"
fi
[ -x "$mincut_bin" ] || mincut_bin="$HOME/.local/bin/mincut"

install_desktop_entry() {
  sed "s|^Exec=mincut$|Exec=\"$mincut_bin\"|" "$1" > "$2"
  chmod 644 "$2"
}

echo "==> Adding the application entry"
install -d "$data_home/applications" "$autostart_dir"
install_desktop_entry "$here/desktop/mincut.desktop" "$data_home/applications/mincut.desktop"
install_desktop_entry "$here/desktop/mincut-autostart.desktop" "$autostart_dir/mincut.desktop"

echo "==> Installing the icon"
icon_dir="$data_home/icons/hicolor/scalable/apps"
install -d "$icon_dir"
install -m 644 "$here/desktop/mincut.svg" "$icon_dir/mincut.svg"
gtk-update-icon-cache -q -t -f "$data_home/icons/hicolor" 2>/dev/null || true

if command -v gnome-extensions >/dev/null 2>&1; then
  echo "==> Installing the GNOME Shell bridge (needed on Wayland)"
  ext_dir="$data_home/gnome-shell/extensions/mincut@ubuntu-mincut"
  install -d "$ext_dir"
  install -m 644 "$here/gnome-extension/mincut@ubuntu-mincut/"* "$ext_dir/"
  gnome-extensions enable mincut@ubuntu-mincut 2>/dev/null ||
    echo "   Enable it after logging out and back in: gnome-extensions enable mincut@ubuntu-mincut"
fi

echo "==> Registering the keyboard shortcut"
"$mincut_bin" setup || true

echo
echo "Done. Start it now with: mincut"
echo "The bezel opens with Ctrl+Shift+V (change it in Preferences)."
