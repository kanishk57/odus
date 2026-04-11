# 🦉 Odus — AI Linux Mentor

> Vision-native desktop assistant that captures your screen, analyzes it with Gemini, and fixes your Linux issues with one click.

## How It Works

```
Press Hotkey → Screen Captured → Gemini Analyzes → One-Click Fix
```

1. **Capture** — Press `Ctrl+Shift+O` from any app to screenshot your screen
2. **Analyze** — Gemini 2.5 Vision identifies errors, misconfigs, and issues
3. **Fix** — Suggested commands run through a 3-tier safety gate before execution

## Prerequisites

- Python 3.11+
- Linux (X11 or Wayland)
- A [Gemini API key](https://aistudio.google.com/apikey) (free tier works)

**Wayland users** — install a screen capture tool:
```bash
# For wlroots compositors (Sway, Hyprland):
sudo apt install grim

# For GNOME Wayland:
# gnome-screenshot is usually preinstalled
```

## Setup

```bash
# 1. Clone the repo
git clone https://github.com/kanishk57/odus.git
cd odus

# 2. Create a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 3. Install dependencies (pick one)
pip install -e ".[dev]"        # editable install (recommended for devs)
# OR
pip install -r requirements.txt  # plain install

# 4. Configure your API key
cp .env.example .env
nano .env                      # paste your GEMINI_API_KEY

# 5. Launch
python -m odus.main
```

Get a free API key at [aistudio.google.com/apikey](https://aistudio.google.com/apikey)

## Architecture

```
odus/
├── perception/    # Screen capture (X11 + Wayland) + global hotkey
├── reasoning/     # Gemini Vision client + agentic loop + prompts
├── action/        # Sandboxed executor + 3-tier safety gate
└── ui/            # Flet desktop app + mascot + Ghost Terminal
```

All layers communicate via an **async event bus** — zero coupling between modules.

## Safety System

| Tier | Action | Examples |
|------|--------|----------|
| ✅ Safe | Auto-execute | `ls`, `cat`, `systemctl status`, `ping` |
| ⚠️ Caution | User confirms | `sudo apt install`, `systemctl restart` |
| 🚫 Danger | **Always blocked** | `rm -rf`, `dd`, `curl\|bash`, `chmod 777` |

## Tech Stack

- **UI**: [Flet](https://flet.dev) (Flutter-powered Python desktop)
- **AI**: [Gemini 2.5 Flash/Pro](https://ai.google.dev) via `google-genai`
- **Capture**: `mss` (X11) + `grim` (Wayland)
- **Hotkey**: `pynput`

## Running Tests

```bash
pytest tests/ -v   # 53 tests
```

## License

MIT