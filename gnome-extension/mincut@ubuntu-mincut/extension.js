// Feeds clipboard changes from GNOME Shell to the Mincut application.
//
// On Wayland a client may only read the selection it owns, so a clipboard
// manager cannot poll like it does on X11.  The shell can see every change;
// this bridges that signal over D-Bus.

import GLib from 'gi://GLib';
import Gio from 'gi://Gio';
import Meta from 'gi://Meta';
import St from 'gi://St';

import {Extension} from 'resource:///org/gnome/shell/extensions/extension.js';

const APP_BUS = 'org.mincut.App';
const APP_PATH = '/org/mincut/App';
const APP_IFACE = 'org.mincut.App';
const SHELL_PATH = '/org/mincut/Shell';

const SHELL_INTERFACE = `
<node>
  <interface name="org.mincut.Shell">
    <method name="SetClipboard">
      <arg type="s" direction="in" name="text"/>
      <arg type="b" direction="out" name="ok"/>
    </method>
    <method name="ReadClipboard">
      <arg type="s" direction="out" name="text"/>
    </method>
  </interface>
</node>`;

export default class MincutBridgeExtension extends Extension {
    enable() {
        this._clipboard = St.Clipboard.get_default();

        this._proxy = new Gio.DBusProxy({
            g_connection: Gio.DBus.session,
            g_name: APP_BUS,
            g_object_path: APP_PATH,
            g_interface_name: APP_IFACE,
            g_flags: Gio.DBusProxyFlags.DO_NOT_AUTO_START,
        });
        this._proxy.init_async(GLib.PRIORITY_DEFAULT, null, null);

        // GNOME 45 dropped St.Clipboard's "owner-changed" signal; the shell
        // reports selection ownership through Meta.Selection instead.
        this._selection = global.display.get_selection();
        this._handler = this._selection.connect('owner-changed', (selection, selectionType) => {
            if (selectionType !== Meta.SelectionType.SELECTION_CLIPBOARD)
                return;
            this._clipboard.get_text(St.ClipboardType.CLIPBOARD, (_c, text) => {
                if (!text)
                    return;
                this._proxy?.ClipboardChangedRemote(text, () => {});
            });
        });

        this._exported = Gio.DBusExportedObject.wrapJSObject(SHELL_INTERFACE, this);
        this._exported.export(Gio.DBus.session, SHELL_PATH);
    }

    disable() {
        if (this._selection && this._handler)
            this._selection.disconnect(this._handler);
        this._selection = null;
        this._handler = 0;
        this._clipboard = null;
        if (this._exported) {
            this._exported.unexport();
            this._exported = null;
        }
        this._proxy = null;
    }

    // -- org.mincut.Shell ------------------------------------------------
    SetClipboard(text) {
        this._clipboard.set_text(St.ClipboardType.CLIPBOARD, text);
        return true;
    }

    ReadClipboard() {
        let value = '';
        this._clipboard.get_text(St.ClipboardType.CLIPBOARD, (_c, text) => {
            value = text ?? '';
        });
        return value;
    }
}
