# Mincut

A clipboard manager for Ubuntu with a single idea behind it: your clipboard
history should be one keystroke away and gone again the moment you are done
with it.

Copy as usual. When you need something you copied earlier, press
**Ctrl+Shift+V** and a translucent panel — the *bezel* — opens in the middle of
the screen with your history. Step through it with the arrow keys, press
Return, and the clipping is pasted into whatever you were working in.

![The bezel](docs/bezel.png)

Built for Ubuntu 26.04.1 LTS (GNOME 50), but it runs on any Ubuntu from 22.04
onwards, on Wayland or X11.

## Install

### What you need

| | Ubuntu 22.04+ with Wayland (GNOME) | Ubuntu with X11 |
| --- | --- | --- |
| Python | 3.10 or newer | 3.10 or newer |
| Toolkit | `python3-pyqt6` (or `pip install PyQt6`) | same |
| Clipboard | GNOME Shell bridge, bundled here | `xclip` |
| Paste | nothing extra (uses the shell) | `xdotool` |
| Global hotkey | registered as a desktop shortcut | `python-xlib` (grabbed directly) |

```bash
# Wayland session
sudo apt install python3-pyqt6 git

# X11 session
sudo apt install python3-pyqt6 git xclip xdotool
python3 -m pip install --user python-xlib
```

Optional, Wayland only: `sudo apt install ydotool` if you want Mincut to press
Ctrl+V for you after you pick a clipping. Without it the clipping is still
placed on the clipboard — you just press Ctrl+V yourself.

### Quick install

```bash
git clone https://github.com/joe7lopes/Ubuntu-mincut.git
cd Ubuntu-mincut
./install.sh
mincut
```

`install.sh` does four things, and prints each one as it goes:

1. installs the package for your user (`pip install --user`, falling back to
   `--break-system-packages` where the distro Python refuses user installs);
2. adds `mincut.desktop` to your applications menu and to autostart;
3. copies the GNOME Shell bridge into
   `~/.local/share/gnome-shell/extensions/mincut@ubuntu-mincut/` and enables it;
4. registers the **Ctrl+Shift+V** shortcut, pointing at `mincut toggle`.

### Manual install, step by step

Use this if you would rather see every step, or if `install.sh` stops halfway.

```bash
# 1. the application
git clone https://github.com/joe7lopes/Ubuntu-mincut.git
cd Ubuntu-mincut
python3 -m pip install --user --break-system-packages -e .[x11]   # [x11] only on X11

# 2. menu entry + autostart
mkdir -p ~/.local/share/applications ~/.config/autostart
cp desktop/mincut.desktop ~/.local/share/applications/
cp desktop/mincut-autostart.desktop ~/.config/autostart/mincut.desktop
mkdir -p ~/.local/share/icons/hicolor/scalable/apps
cp desktop/mincut.svg ~/.local/share/icons/hicolor/scalable/apps/

# 3. the Wayland clipboard bridge (skip on X11)
mkdir -p ~/.local/share/gnome-shell/extensions/mincut@ubuntu-mincut
cp gnome-extension/mincut@ubuntu-mincut/* \
   ~/.local/share/gnome-shell/extensions/mincut@ubuntu-mincut/
```

Then **log out and back in** — GNOME only scans the extensions directory at
login — and enable it:

```bash
gnome-extensions enable mincut@ubuntu-mincut
```

```bash
# 4. the hotkey
mincut setup      # writes a GNOME custom shortcut calling `mincut toggle`
mincut            # start the app
```

On X11, step 4 is unnecessary: the running instance grabs the key combination
itself as soon as it starts, provided `python-xlib` is installed.

### First run

`mincut` starts in the tray with no window — that is expected. Copy a few
things, then press **Ctrl+Shift+V** and the bezel opens. Pick a clipping with
the arrow keys and press **Return**.

To change the hotkey, the panel size, the opacity, how many clippings are kept
or whether favourites are used at all, open **Preferences** from the tray menu
(or run `mincut prefs`). Settings are written to
`~/.config/mincut/config.json`; history and favourites live in
`~/.local/share/mincut/clips.json`. They are written when you change a setting
or quit the application, so a fresh install leaves nothing behind yet.

### Check that it is set up correctly

```bash
mincut status          # prints the effective settings and the config path
gsettings get org.gnome.settings-daemon.plugins.media-keys custom-keybindings
```

The second command should list a path ending in `custom-keybindings/mincut/`.
On Wayland, `gnome-extensions list --enabled | grep mincut` should print the
bridge.

### Troubleshooting

**The hotkey does nothing.** Run `mincut setup` again, then check for a
clashing binding: Settings → Keyboard → View and Customise Shortcuts →
Custom Shortcuts. Many terminals use Ctrl+Shift+V for "paste as plain text",
which is harmless — the bezel opens on top — but if another application has
taken the *global* shortcut, give Mincut a different one in Preferences and run
`mincut setup` afterwards.

**The bezel opens but the history is empty on Wayland.** The Shell bridge is not
running. Confirm the extension is enabled, and remember that a freshly copied
extension only loads after a log out and back in. On X11, install `xclip` —
without it Mincut can write the clipboard but cannot watch it.

**Nothing is pasted after pressing Return.** The clipping is on the clipboard,
but the desktop will not accept a simulated Ctrl+V: install `xdotool` on X11 or
`ydotool` on Wayland. Otherwise press Ctrl+V yourself — Mincut tells you so in a
notification.

**No tray icon.** GNOME needs AppIndicator support:
`sudo apt install gnome-shell-extension-appindicator`, then log out and back in.
The hotkey and the bezel work regardless of the tray.

**`mincut: command not found`.** User installs land in `~/.local/bin`, which
some login shells do not add to `PATH`. Add it:

```bash
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
```

**It does not start at login.** Check that
`~/.config/autostart/mincut.desktop` exists and that the command inside it
resolves — an autostart entry pointing at `mincut` fails silently if
`~/.local/bin` is not on the `PATH` that GNOME uses.

### Uninstall

```bash
mincut quit
python3 -m pip uninstall mincut
rm -f ~/.local/share/applications/mincut.desktop \
      ~/.config/autostart/mincut.desktop \
      ~/.local/share/icons/hicolor/scalable/apps/mincut.svg
gnome-extensions disable mincut@ubuntu-mincut
rm -rf ~/.local/share/gnome-shell/extensions/mincut@ubuntu-mincut
rm -rf ~/.config/mincut ~/.local/share/mincut     # history and settings
```

## Keys in the bezel

| Key | Action |
| --- | --- |
| Down / Right | Move backward in history (older) |
| Up / Left | Move forward in history (newer) |
| Return | Paste the clipping and close |
| Enter | Move the clipping to the front and close |
| Esc | Close without pasting, keeping the position |
| Home / End | Jump to the most / least recent clipping |
| PgDn / PgUp | Move ten clippings at a time |
| Backspace / Del | Delete the clipping and close |
| 1 … 9, 0 | Jump to position 1–9, or 10 |
| s / S | Save the clipping to a file on the Desktop (S also removes it) |
| f | Switch between history and favourites (the bezel turns warm yellow) |
| F | Move the clipping into favourites and close |
| Mouse wheel, click left/right edge | Same as the arrow keys |

## The menu

The tray icon lists the most recent clippings, and offers **Merge All**
(joins the whole history, oldest first, into one clipping), **Clear All**,
**Pause tracking** for when you are copying passwords, and **Preferences**.

![Preferences](docs/preferences.png)

## Favourites

Press **F** on a clipping to keep it in a separate store that does not rotate
away. Press **f** inside the bezel to switch to it — the panel is tinted yellow
so you can always tell which store you are looking at.

![Favourites](docs/bezel-favorites.png)

## How it works on Wayland

Wayland does not let one application read another application's selection, so
the clipboard has to be reported from inside the shell. `gnome-extension/`
contains a small GNOME Shell extension (`mincut@ubuntu-mincut`) that watches
clipboard changes and hands them to the application over D-Bus, on
`org.mincut.App`. The application itself still owns the history, the bezel and
the settings; the extension is a sensor, not a second copy of the app.

On X11 (`xclip`) and on wlroots compositors (`wl-clipboard`) Mincut polls the
selection directly and no extension is needed.

The keyboard shortcut is registered the same way you would do it yourself in
Settings → Keyboard → Custom Shortcuts, pointing at `mincut toggle`. Under X11
the running instance grabs the key combination directly.

## Files

| Path | Contents |
| --- | --- |
| `~/.config/mincut/config.json` | all settings |
| `~/.local/share/mincut/clips.json` | history and favourites |

## Development

```bash
python3 -m pip install -e .[test]
python3 -m pytest
QT_QPA_PLATFORM=offscreen python3 scripts/render_screenshots.py
```

`scripts/render_screenshots.py` draws the screenshots in `docs/` without a
display, which is also the fastest way to check a change to the bezel layout.

Code map:

| Module | Responsibility |
| --- | --- |
| `mincut/store.py` | clips, history rotation, favourites, persistence format |
| `mincut/keys.py` | every keystroke in the bezel → an action (no GUI imports) |
| `mincut/bezel.py` | the painted panel, its animation and input |
| `mincut/app.py` | controller: clipboard watching, tray, paste, D-Bus |
| `mincut/clipboard.py` | X11 / wlroots / Qt clipboard backends, paste simulation |
| `mincut/hotkey.py` | key grabs on X11, custom keybindings on Wayland |
| `mincut/prefs.py` | preferences dialog |

The store and the key handling are deliberately free of toolkit imports, so
they are tested directly; `tests/test_app_smoke.py` boots the whole
application offscreen and exercises copy → bezel → paste.

## License

MIT — see [LICENSE](LICENSE).
