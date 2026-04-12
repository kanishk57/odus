import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import Clutter from 'gi://Clutter';
import Shell from 'gi://Shell';
import St from 'gi://St';
import * as PanelMenu from 'resource:///org/gnome/shell/ui/panelMenu.js';
import * as Dialog from 'resource:///org/gnome/shell/ui/dialog.js';
import * as ModalDialog from 'resource:///org/gnome/shell/ui/modalDialog.js';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';

export class OdusPresentation {
    constructor() {
        this._indicator = null;
        this._thinkingModal = null;
        this._thinkingLabel = null;
        this._thinkingProgressFill = null;
        this._thinkingTimeoutId = 0;
        this._thinkingStep = 0;
    }

    createPanelButton(onActivate) {
        this.destroyPanelButton();

        this._indicator = new PanelMenu.Button(0.0, 'Odus Trigger', false);

        const icon = new St.Icon({
            icon_name: 'face-smile-symbolic',
            style_class: 'system-status-icon',
        });

        this._indicator.add_child(icon);
        this._indicator.connect('button-press-event', () => {
            onActivate();
            return Clutter.EVENT_STOP;
        });

        Main.panel.addToStatusArea('odus-bridge', this._indicator);
        return this._indicator;
    }

    destroyPanelButton() {
        if (!this._indicator)
            return;

        this._indicator.destroy();
        this._indicator = null;
    }

    showThinking() {
        if (this._thinkingModal)
            return;

        Main.notify('Odus', 'Getting advice...');

        this._thinkingStep = 0;
        this._thinkingModal = new ModalDialog.ModalDialog({
            destroyOnClose: false,
            shellReactive: false,
            actionMode: Shell.ActionMode.SYSTEM_MODAL,
            styleClass: 'odus-modal',
        });

        const badge = new St.Label({
            text: 'Thinking',
            style: `
                color: #8be9fd;
                background-color: rgba(255, 255, 255, 0.06);
                border: 1px solid #8be9fd;
                border-radius: 999px;
                padding: 6px 12px;
                margin-bottom: 10px;
                font-size: 12px;
                font-weight: 600;
            `,
        });

        const title = new St.Label({
            text: 'Odus is thinking',
            style: 'font-size: 18px; font-weight: 700; color: white; margin-bottom: 4px;',
        });

        this._thinkingLabel = new St.Label({
            text: 'Analyzing your screen...',
            style: 'color: rgba(255,255,255,0.78); font-size: 14px; margin-bottom: 14px;',
        });

        const progressTrack = new St.Widget({
            style: 'width: 320px; height: 10px; border-radius: 999px; background-color: rgba(255,255,255,0.14);',
        });
        this._thinkingProgressFill = new St.Widget({
            style: 'height: 10px; border-radius: 999px; background: linear-gradient(90deg, #8be9fd, #bd93f9);',
        });
        this._thinkingProgressFill.set_width(72);
        progressTrack.add_child(this._thinkingProgressFill);

        const foot = new St.Label({
            text: 'You can keep typing while I inspect the screenshot.',
            style: 'margin-top: 12px; color: rgba(255,255,255,0.55); font-size: 12px;',
        });

        const layout = new St.BoxLayout({
            vertical: true,
            style: 'padding: 4px 0 2px 0;',
        });
        layout.add_child(badge);
        layout.add_child(title);
        layout.add_child(this._thinkingLabel);
        layout.add_child(progressTrack);
        layout.add_child(foot);
        this._thinkingModal.contentLayout.add_child(layout);

        this._thinkingModal.addButton({
            label: 'Hide',
            action: () => this.hideThinking(),
        });

        this._thinkingModal.connect('closed', () => this.hideThinking());
        this._thinkingModal.open(global.get_current_time(), true);

        this._thinkingTimeoutId = GLib.timeout_add(GLib.PRIORITY_DEFAULT, 120, () => {
            if (!this._thinkingModal || !this._thinkingProgressFill || !this._thinkingLabel)
                return GLib.SOURCE_REMOVE;

            this._thinkingStep = (this._thinkingStep + 1) % 18;
            const pct = 18 + ((this._thinkingStep * 6) % 74);
            this._thinkingProgressFill.set_width(Math.max(72, Math.floor(320 * pct / 100)));
            const dots = '.'.repeat((this._thinkingStep % 3) + 1);
            this._thinkingLabel.text = `Analyzing${dots}`;
            return GLib.SOURCE_CONTINUE;
        });
    }

    hideThinking() {
        const modal = this._thinkingModal;
        if (!modal)
            return;

        this._thinkingModal = null;

        if (this._thinkingTimeoutId) {
            GLib.source_remove(this._thinkingTimeoutId);
            this._thinkingTimeoutId = 0;
        }

        try {
            modal.close(global.get_current_time());
        } catch (e) {
            // ignore close errors during teardown
        }

        modal.destroy();
        this._thinkingLabel = null;
        this._thinkingProgressFill = null;
    }

    async showAdviceModal(payload, { onAskFollowUp } = {}) {
        this.hideThinking();

        const summary = payload?.summary || '';
        const explanation = payload?.explanation || '';
        const followUp = payload?.follow_up || '';
        const command = payload?.command || '';
        const kind = payload?.kind || (command ? 'advice' : 'info');
        const retryAfter = payload?.retry_after;

        const title = summary || (kind === 'rate_limit' ? 'Rate limit reached' : 'Odus advice');
        const body = this._formatBody({ explanation, followUp, command, kind, retryAfter });

        try {
            return await new Promise(resolve => {
                let finished = false;

                const modal = new ModalDialog.ModalDialog({
                    destroyOnClose: false,
                    shellReactive: false,
                    actionMode: Shell.ActionMode.SYSTEM_MODAL,
                    styleClass: 'odus-modal',
                });

                const finish = approved => {
                    if (finished)
                        return;
                    finished = true;

                    try {
                        modal.close(global.get_current_time());
                    } catch (e) {
                        // ignore close errors during shutdown
                    }
                    modal.destroy();
                    resolve(approved);
                };

                const badge = new St.Label({
                    text: this._badgeText(kind, command, retryAfter),
                    style: `
                        color: ${this._badgeColor(kind)};
                        background-color: rgba(255, 255, 255, 0.06);
                        border: 1px solid ${this._badgeColor(kind)};
                        border-radius: 999px;
                        padding: 6px 12px;
                        margin-bottom: 10px;
                        font-size: 12px;
                        font-weight: 600;
                    `,
                });
                modal.contentLayout.add_child(badge);

                const content = new Dialog.MessageDialogContent({
                    title,
                    description: body,
                });
                modal.contentLayout.add_child(content);

                const chatSection = new St.BoxLayout({
                    vertical: true,
                    style: 'spacing: 8px; margin-top: 8px;',
                });

                const chatLabel = new St.Label({
                    text: kind === 'rate_limit' ? 'Ask Odus after the retry window:' : 'Ask Odus a follow-up:',
                    style: 'color: white; font-size: 14px; font-weight: 600;',
                });
                chatSection.add_child(chatLabel);

                const entry = new St.Entry({
                    style_class: 'search-entry',
                    hint_text: kind === 'rate_limit' ? 'Try again later...' : 'Type a reply or question...',
                    can_focus: true,
                    x_expand: true,
                });
                entry.clutter_text.set_single_line_mode(true);
                entry.clutter_text.connect('activate', () => sendFollowUp());
                chatSection.add_child(entry);
                modal.contentLayout.add_child(chatSection);
                modal.setInitialKeyFocus(entry);

                const sendFollowUp = async () => {
                    const query = entry.get_text().trim();
                    if (!query) {
                        return;
                    }

                    if (onAskFollowUp) {
                        try {
                            await onAskFollowUp(query);
                        } catch (e) {
                            Main.notifyError('Odus', e.message);
                        }
                    }

                    finish(false);
                };

                modal.addButton({
                    label: 'Ask Odus',
                    action: () => void sendFollowUp(),
                });

                if (command) {
                    modal.addButton({
                        label: 'Allow',
                        isDefault: true,
                        action: () => finish(true),
                    });
                    modal.addButton({
                        label: 'Deny',
                        action: () => finish(false),
                    });
                } else {
                    modal.addButton({
                        label: kind === 'rate_limit' ? 'Close' : 'Done',
                        isDefault: true,
                        action: () => finish(false),
                    });
                }

                try {
                    modal.connect('closed', () => finish(false));
                    modal.open(global.get_current_time(), true);
                } catch (e) {
                    this._notifyFallback(title, body, kind);
                    resolve(false);
                }
            });
        } catch (e) {
            this._notifyFallback(title, body, kind);
            return false;
        }
    }

    _formatBody({ explanation, followUp, command, kind, retryAfter }) {
        const sections = [
            `What Odus found:\n${explanation || 'No explanation available yet.'}`,
            followUp ? `Next step:\n${followUp}` : '',
            command ? `Suggested command:\n${command}` : (kind === 'rate_limit'
                ? `Odus will retry after the backoff window${retryAfter ? ` (${retryAfter.toFixed(0)}s)` : ''}.`
                : 'No command suggested yet.'),
        ].filter(Boolean);

        return sections.join('\n\n');
    }

    _badgeText(kind, command, retryAfter) {
        if (kind === 'rate_limit')
            return retryAfter ? `Rate limited • retry in ${retryAfter.toFixed(0)}s` : 'Rate limited';
        if (kind === 'error')
            return 'Analysis error';
        return command ? 'Command ready' : 'Advice ready';
    }

    _badgeColor(kind) {
        if (kind === 'rate_limit')
            return '#ffb86c';
        if (kind === 'error')
            return '#ff7b72';
        return '#8be9fd';
    }

    _notifyFallback(title, body, kind) {
        if (kind === 'rate_limit' || kind === 'error')
            Main.notifyError(title, body);
        else
            Main.notify(title, body);
    }
}
