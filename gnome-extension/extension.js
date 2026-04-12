import Gio from 'gi://Gio';
import GioUnix from 'gi://GioUnix?version=2.0';
import GLib from 'gi://GLib';
import Clutter from 'gi://Clutter';
import Meta from 'gi://Meta';
import Shell from 'gi://Shell';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import { Extension } from 'resource:///org/gnome/shell/extensions/extension.js';
import { OdusPresentation } from './ui/presentation.js';

console.log('[OdusBridge] ESM Module Loaded Successfully');

const DBUS_XML = `
<!DOCTYPE node PUBLIC "-//freedesktop//DTD D-BUS Object Introspection 1.0//EN"
 "http://www.freedesktop.org/standards/dbus/1.0/introspect.dtd">
<node>
  <interface name="org.gnome.Odus">
    <method name="RegisterClient">
      <arg type="s" name="token" direction="in"/>
      <arg type="b" name="success" direction="out"/>
    </method>
    <method name="InjectKeystroke">
      <arg type="s" name="keysym" direction="in"/>
    </method>
    <method name="SetMascotState">
      <arg type="s" name="state" direction="in"/>
    </method>
    <method name="RequestActionApproval">
      <arg type="s" name="payload" direction="in"/>
      <arg type="b" name="approved" direction="out"/>
    </method>
    <method name="CaptureScreen">
      <annotation name="org.gtk.GDBus.C.UnixFD" value="true"/>
      <arg type="h" name="fd" direction="out"/>
    </method>
    <signal name="HotkeyTriggered"/>
  </interface>
</node>
`;

const ACTIVATION_SHORTCUT_KEY = 'odus-activation-shortcut';
export default class OdusBridge extends Extension {
    constructor(metadata) {
        super(metadata);
        this._dbusConnection = null;
        this._dbusInterfaceInfo = null;
        this._dbusRegistrationId = null;
        this._virtualKeyboard = null;
        this._authenticatedBusName = null;
        this._expectedToken = null;
        this._busNameId = null;
        this._screenshot = null;
        this._settings = null;
        this._ui = new OdusPresentation();
    }

    enable() {
        console.log('[OdusBridge] Initializing...');
        
        try {
            // 1. Load/Generate Authentication Token
            this._loadOrCreateToken();

            // 2. Initialize Virtual Keyboard
            const seat = Clutter.get_default_backend().get_default_seat();
            this._virtualKeyboard = seat.create_virtual_device(Clutter.InputDeviceType.KEYBOARD_DEVICE);
            console.log('[OdusBridge] Virtual keyboard initialized');

            // 3. Initialize Screenshot functionality
            this._screenshot = new Shell.Screenshot();
            console.log('[OdusBridge] Screenshot functionality initialized');

            // 4. Register the activation shortcut before exporting D-Bus.
            this._settings = this.getSettings();
            Main.wm.addKeybinding(
                ACTIVATION_SHORTCUT_KEY,
                this._settings,
                Meta.KeyBindingFlags.NONE,
                Shell.ActionMode.ALL,
                this._onActivationShortcut.bind(this)
            );

            // 5. Export D-Bus interface.
            this._dbusInterfaceInfo = Gio.DBusNodeInfo.new_for_xml(DBUS_XML).interfaces[0];
 
            this._busNameId = Gio.bus_own_name(
                Gio.BusType.SESSION,
                'org.gnome.Odus',
                Gio.BusNameOwnerFlags.NONE,
                (connection, name) => {
                    this._dbusConnection = connection;
                    this._dbusRegistrationId = connection.register_object(
                        '/org/gnome/Odus',
                        this._dbusInterfaceInfo,
                        this._handleMethodCall.bind(this),
                        null,
                        null
                    );
                    console.log(`[OdusBridge] Bus acquired: ${name}`);
                    console.log('[OdusBridge] D-Bus interface exported at /org/gnome/Odus');
                },
                (connection, name) => {
                    console.log(`[OdusBridge] Name acquired: ${name}`);
                },
                (connection, name) => {
                    if (this._dbusConnection && this._dbusRegistrationId) {
                        this._dbusConnection.unregister_object(this._dbusRegistrationId);
                        this._dbusRegistrationId = null;
                    }
 
                    this._dbusConnection = null;
                    console.log(`[OdusBridge] Name lost: ${name}`);
                }
            );

            this._ui.createPanelButton(() => this._onActivationShortcut());
            console.log('[OdusBridge] Top panel button added');

        } catch (e) {
            console.error(`[OdusBridge] CRITICAL failure during enable: ${e.message}`);
        }
    }

    disable() {
        console.log(`[OdusBridge] Disabling extension`);

        this._ui.destroyPanelButton();
        this._ui.hideThinking();
 
        Main.wm.removeKeybinding(ACTIVATION_SHORTCUT_KEY);

        if (this._dbusConnection && this._dbusRegistrationId) {
            this._dbusConnection.unregister_object(this._dbusRegistrationId);
            this._dbusRegistrationId = null;
            this._dbusConnection = null;
        }

        if (this._busNameId) {
            Gio.bus_unown_name(this._busNameId);
            this._busNameId = null;
        }

        this._virtualKeyboard = null;
        this._authenticatedBusName = null;
        this._dbusInterfaceInfo = null;
        this._settings = null;
    }

    _onActivationShortcut() {
        console.log('[OdusBridge] Activation shortcut triggered');
        this._ui.showThinking();

        if (!this._dbusConnection)
            return;

        this._dbusConnection.emit_signal(
            null,
            '/org/gnome/Odus',
            'org.gnome.Odus',
            'HotkeyTriggered',
            null
        );
    }

    _loadOrCreateToken() {
        try {
            const runtimeDir = GLib.get_user_runtime_dir();
            const odusDir = GLib.build_filenamev([runtimeDir, 'odus']);
            const tokenPath = GLib.build_filenamev([odusDir, 'token']);

            if (!GLib.file_test(odusDir, GLib.FileTest.IS_DIR)) {
                GLib.mkdir_with_parents(odusDir, 0o700);
            }

            if (!GLib.file_test(tokenPath, GLib.FileTest.EXISTS)) {
                this._expectedToken = GLib.uuid_string_random();
                if (!GLib.file_set_contents(tokenPath, this._expectedToken)) {
                    throw new Error(`Failed to write token to ${tokenPath}`);
                }
                GLib.chmod(tokenPath, 0o600);
            } else {
                const [success, contents] = GLib.file_get_contents(tokenPath);
                if (success) {
                    this._expectedToken = new TextDecoder().decode(contents).trim();
                } else {
                    throw new Error(`Failed to read token from ${tokenPath}`);
                }
            }

            if (!this._expectedToken)
                throw new Error('Token is empty after loading/generation');

            console.log('[OdusBridge] Authentication token verified');
        } catch (e) {
            console.error(`[OdusBridge] _loadOrCreateToken failure: ${e.message}`);
            if (!this._expectedToken) {
                this._expectedToken = GLib.uuid_string_random();
                console.log('[OdusBridge] Using fallback ephemeral token');
            }
        }
    }

    _verifyCaller(sender) {
        if (this._authenticatedBusName && sender === this._authenticatedBusName)
            return;

        if (!this._authenticatedBusName) {
            throw new Error('Caller not authenticated. Please call RegisterClient(token) first.');
        }

        throw new Error('Caller does not match the authenticated D-Bus client.');
    }

    _returnVoid(invocation) {
        invocation.return_value(new GLib.Variant('()', []));
    }

    _returnError(invocation, error) {
        const message = error instanceof Error ? error.message : String(error);
        invocation.return_dbus_error('org.gnome.Odus.Error', message);
    }

    _handleMethodCall(_connection, sender, _objectPath, _interfaceName, methodName, parameters, invocation) {
        this._dispatchMethodCall(sender, methodName, parameters, invocation).catch(error => {
            this._returnError(invocation, error);
        });
    }

    async _dispatchMethodCall(sender, methodName, parameters, invocation) {
        const args = parameters.deepUnpack();

        switch (methodName) {
        case 'RegisterClient': {
            const success = this.RegisterClient(args[0], sender);
            invocation.return_value(new GLib.Variant('(b)', [success]));
            return;
        }
        case 'InjectKeystroke':
            this._verifyCaller(sender);
            this.InjectKeystroke(args[0]);
            this._returnVoid(invocation);
            return;
        case 'SetMascotState':
            this._verifyCaller(sender);
            this.SetMascotState(args[0]);
            this._returnVoid(invocation);
            return;
        case 'RequestActionApproval': {
            this._verifyCaller(sender);
            const approved = await this.RequestActionApproval(args[0]);
            invocation.return_value(new GLib.Variant('(b)', [approved]));
            return;
        }
        case 'CaptureScreen': {
            this._verifyCaller(sender);
            const [fdIndex, fdList] = await this.CaptureScreen();
            invocation.return_value_with_unix_fd_list(new GLib.Variant('(h)', [fdIndex]), fdList);
            return;
        }
        default:
            invocation.return_error_literal(
                Gio.DBusError,
                Gio.DBusError.UNKNOWN_METHOD,
                `Unknown method: ${methodName}`
            );
        }
    }

    RegisterClient(token, sender) {
        if (token === this._expectedToken) {
            console.log(`[OdusBridge] Authenticated client: ${sender}`);
            this._authenticatedBusName = sender;
            return true;
        }

        console.warn('[OdusBridge] Authentication failed');
        return false;
    }

    InjectKeystroke(keysymName) {
        const keyval = Clutter.keysym_from_name(keysymName);
        if (keyval === Clutter.KEY_VoidSymbol) {
            console.error(`[OdusBridge] Invalid keysym: ${keysymName}`);
            return;
        }

        console.log(`[OdusBridge] Injecting: ${keysymName} (${keyval})`);
        
        const time = GLib.get_monotonic_time() / 1000;
        this._virtualKeyboard.notify_keyval(time, keyval, Clutter.KeyState.PRESSED);
        this._virtualKeyboard.notify_keyval(time + 1, keyval, Clutter.KeyState.RELEASED);
    }

    SetMascotState(state) {
        console.log(`[OdusBridge] Mascot state requested: ${state}`);
    }

    RequestActionApproval(payload) {
        let parsed = {};

        try {
            parsed = JSON.parse(payload);
        } catch (e) {
            console.error(`[OdusBridge] Invalid approval payload: ${e.message}`);
        }

        const summary = parsed.summary || '';
        const explanation = parsed.explanation || '';
        const followUp = parsed.follow_up || '';
        const command = parsed.command || '';
        const kind = parsed.kind || (command ? 'advice' : 'info');
        const retryAfter = parsed.retry_after;

        console.log(`[OdusBridge] Requesting advice modal for: ${command || 'follow-up chat'}`);

        return this._ui.showAdviceModal(
            {
                summary,
                explanation,
                follow_up: followUp,
                command,
                kind,
                retry_after: retryAfter,
            },
            {
                onAskFollowUp: async query => {
                    await Gio.DBus.session.call(
                        'org.gnome.Odus.Control',
                        '/org/gnome/Odus/Control',
                        'org.gnome.Odus.Control',
                        'SubmitQuery',
                        new GLib.Variant('(s)', [query]),
                        null,
                        Gio.DBusCallFlags.NONE,
                        -1,
                        null
                    );
                    console.log(`[OdusBridge] Follow-up query sent: ${query}`);
                },
            }
        );
    }

    async CaptureScreen() {
        if (!this._screenshot) {
            throw new Error('Screenshot functionality not available');
        }

        const [fd, tempPath] = GLib.file_open_tmp('odus_capture_XXXXXX');
        const stream = GioUnix.OutputStream.new(fd, false);

        try {
            GLib.unlink(tempPath);
        } catch (e) {
            console.warn(`[OdusBridge] Failed to unlink temp capture file ${tempPath}: ${e.message}`);
        }

        const success = await new Promise((resolve, reject) => {
            this._screenshot.screenshot(true, stream, (obj, res) => {
                try {
                    const [result] = obj.screenshot_finish(res);
                    resolve(result);
                } catch (e) {
                    reject(e);
                } finally {
                    stream.close(null);
                }
            });
        });

        if (!success) {
            throw new Error('Screenshot capture failed');
        }

        const fdList = new Gio.UnixFDList();
        const fdIndex = fdList.append(fd);
        return [fdIndex, fdList];
    }
}
