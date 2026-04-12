# 🦉 Odus — AI Linux Mentor

> Vision-native desktop assistant that captures your screen, analyzes it with Gemini, and fixes your Linux issues with one click.

Odus bridges the graphical-to-CLI gap with a context-aware, multimodal agent that functions inside a heavily sandboxed local environment.

## How It Works

```
Press Hotkey → Screen Captured → Gemini Analyzes → One-Click Fix
```

1. **Global Perception Trigger** — Press `Ctrl+Shift+O` from any app globally to immediately screenshot your active compositor via `mss` or `grim`.
2. **Contextual Analysis** — Uses Google's **Gemini 2.5 Flash** to identify visual UI anomalies, error dialogs, or shell stack traces. 
3. **Escalation & Tooling** — Evaluates logic dynamically. Uses native `FunctionDeclarations` (Tool Calling) vs brittle JSON parsing. Escalates reasoning automatically to **Gemini 2.5 Pro** if confidence score drops below 60%.
4. **Sandboxed Remediation** — Outputs heuristic, sandboxed repair commands intercepted by a strict deterministic Safety Gate before reaching your terminal.

## Prerequisites

- Python 3.11+
- Linux (X11 or Wayland environments)
- A [Gemini API key](https://aistudio.google.com/apikey) (Free Tier works)

**Wayland users:** Note that `grim` is prioritized for high-performance captures. `gnome-screenshot` is mapped as a secondary graphical fallback.

## Setup & Launch

Odus provides automated scripts to handle dependencies and environment setup.

### 1. Standard Installation
```bash
git clone https://github.com/kanishk57/odus.git && cd odus

# Create .env and add your GEMINI_API_KEY
cp .env.example .env
nano .env

# Launch the Desktop GUI automatically
./run.sh
```

### 2. GNOME Native Integration (Recommended)
For a seamless Wayland experience with system-level overlays:
```bash
./deploy.sh
```
*Note: You may need to log out and log back in after the first deployment to enable the shell extension.*

## Interface Modes

Odus offers two distinct ways to interact with the AI assistant.

### 1. Desktop GUI App (Qt)
A standalone application with a glassmorphic chat interface. Works globally on X11/Wayland.
- **Launch**: `./run.sh`
- **Best for**: Non-GNOME environments or standard windowed use.

### 2. GNOME Shell Extension (Native)
A high-performance bridge integrated into the compositor via GJS. 
- **Setup**: Run `./deploy.sh` to install the extension and start the background daemon.
- **Service Management**:
    - **View Logs**: `journalctl --user -u odus -f`
    - **Restart Service**: `systemctl --user restart odus`
- **Key Features**: native advice modals, zero-privilege input, and interactive shell follow-ups.

## Architecture & Internals

Odus relies on a decoupled, microservice-inspired architecture pattern powered by a fully asynchronous internal `Event Bus` system mapping state payloads. 

```text
odus/
├── perception/    # X11 (mss) + Wayland (grim/gnome-s) captures | pynput & evdev hooks
├── reasoning/     # Tool Calling schemas | Flash → Pro Escalation | Gemini 429 backoffs
├── action/        # Subprocess execution wrapping | Safety gates | DBus client
├── ui/            # PyQt6 app | Chat Interface | Mascot Sprite State Machine
└── ui_v2/         # Next-gen Sidebar UI & Editorial components
gnome-extension/   # GJS Bridge | GNOME Advice Modals | D-Bus interface
```

### Next-Gen Tech Stack

- **Frontend Core Protocol**: [PyQt6](https://pypi.org/project/PyQt6/) with `qasync` for asynchronous qt event loops, featuring Glassmorphism UI and powered by Google Fonts.
- **LLM Choreography**: `google-genai` SDK backing Dual-Model routines and Async generator multi-turn memory contexts. 
- **Telemetry Layer**: `mss` (X11 rapid dumps) / `grim` (Wayland). `PIL/Pillow` aggressively processes frames (downsampling ≤1280px + JPEG Q75) prior to transmission.
- **Resiliency Infrastructure**: `tenacity` drives intelligent SDK-level exponential timeout and HTTP 429 backoff recoveries natively.
- **Input Simulation (Advanced)**: Sandboxed OS simulations mapped through `PyAutoGUI` / `ydotool` arrays (e.g. `uinput` mapping).

## Three-Tier Safety System

Security isn't an afterthought. Every AI command acts defensively under Odus's regex sandbox before hitting user `$PATH`. Exhaustive execution records route to `~/.odus/audit.log` payload wrappers. 

| Tier | Threat Level | Execution Protocol | Examples |
|------|-------------|-------------------|----------|
| ✅ **Safe** | Low | Bypass Manual Checks | `ls`, `cat`, `systemctl status`, `ping`, `whoami` |
| ⚠️ **Caution** | **Medium (18 rules)** | **Halt.** Await explicit UI Dialog permission | `sudo apt install`, `systemctl restart`, `chmod +x` |
| 🚫 **Danger** | **Critical (14 rules)** | **Strictly blocked.** Will never be passed to bash | `rm -rf`, `dd`, `curl \| bash`, `chmod -R 777` |

## Running Tests

Odus supports rigorous verification across 50+ localized mocked endpoints testing timeout resilience, vision classification confidence drops, and permission gate bypassing attempts.

```bash
pytest tests/ -v
```

## License

MIT