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

## Setup

```bash
# 1. Clone the repo
git clone https://github.com/kanishk57/odus.git
cd odus

# 2. Create an isolated virtual dependency graph
python3 -m venv .venv
source .venv/bin/activate

# 3. Install core dependencies
pip install -e ".[dev]"

# 4. Integrate your GenAI Auth token
cp .env.example .env
nano .env                      # paste your GEMINI_API_KEY

# 5. Launch the Orchestrator
python -m odus.main
```

## Architecture & Internals

Odus relies on a decoupled, microservice-inspired architecture pattern powered by a fully asynchronous internal `Event Bus` system mapping state payloads. 

```text
odus/
├── perception/    # X11 (mss) + Wayland (grim/gnome-s) captures | pynput & evdev hooks
├── reasoning/     # Tool Calling schemas | Flash → Pro Escalation | Tenacity Rate limit backoffs
├── action/        # Subprocess execution wrapping | 10k/5k trunacting limits | Safety gates
└── ui/            # PyQt6 app | Chat Interface | Mascot Sprite State Machine | async streaming
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