# DEV 3 — UI/UX & Mascot Developer

> **You own:** `odus/ui/` and `assets/`

---

## ✅ What's Already Implemented

### UI Layer — `odus/ui/`

| File | Feature | Status | Notes |
|------|---------|--------|-------|
| `theme.py` | `Colors` class — full dark mode palette | ✅ Done | 20+ color tokens including terminal-specific colors |
| `theme.py` | `Fonts` class — Inter + JetBrains Mono | ✅ Done | Loaded via Google Fonts CDN |
| `theme.py` | `FontSizes` scale (XS→XXL) | ✅ Done | 11px to 28px |
| `theme.py` | `Spacing`, `Radii`, `Shadows`, `Layout` | ✅ Done | Complete design token system |
| `mascot.py` | `MascotState` enum (5 states) | ✅ Done | IDLE, THINKING, SUCCESS, ERROR, WARNING |
| `mascot.py` | `MascotController` Flet control | ✅ Done | Emoji placeholders, auto-updates on state change |
| `mascot.py` | State transition method `set_state()` | ✅ Done | Updates icon, message, progress ring visibility |
| `ghost_terminal.py` | `GhostTerminal` container | ✅ Done | Scrollable, auto-scroll, monospace, header bar |
| `ghost_terminal.py` | Color-coded entry types | ✅ Done | `add_info`, `add_success`, `add_error`, `add_warning`, `add_command`, `add_output` |
| `ghost_terminal.py` | Timestamps on every entry | ✅ Done | HH:MM:SS format |
| `ghost_terminal.py` | Clear button | ✅ Done | Header bar "Clear" button |
| `ghost_terminal.py` | Divider lines | ✅ Done | `add_divider()` for visual separation |
| `components.py` | `safety_badge()` | ✅ Done | Color-coded tier badge (green/yellow/red) |
| `components.py` | `confirm_dialog()` | ✅ Done | Modal with command preview, explanation, Fix it!/Cancel |
| `components.py` | `status_chip()` | ✅ Done | Small status indicators for the status bar |
| `app.py` | `OdusApp` class | ✅ Done | Landscape layout with sidebar + main panel |
| `app.py` | Sidebar layout | ✅ Done | Branding header, mascot, hotkey hint |
| `app.py` | Main panel layout | ✅ Done | Analysis header + Ghost Terminal |
| `app.py` | Event bus wiring | ✅ Done | Handles ALL event types from the bus |
| `app.py` | Welcome message | ✅ Done | Shows on app launch |
| `app.py` | Confirmation dialog flow | ✅ Done | Opens dialog on `CONFIRM_REQUIRED`, emits `USER_CONFIRMED`/`USER_DENIED` |

### Known Issue from First Launch

The app launched successfully! But there are some Flet deprecation/GTK warnings in the log:

```
DeprecationWarning: app() is deprecated since version 0.80.0. Use run() instead.
Gdk-Message: Unable to load from the cursor theme
Gtk-CRITICAL: gtk_window_get_position: assertion 'GTK_IS_WINDOW (window)' failed
```

**Fix needed in `main.py`:**
```python
# Change this (line 52):
ft.app(target=app_main)

# To this:
ft.run(target=app_main)
```

The GTK warnings are cosmetic (Flet/Flutter issue on Wayland) and can be ignored.

---

## 🔲 What's Left To Build

### Priority 0 — Must Have for MVP (by Hour 12)

#### 1. Fix the `ft.app()` Deprecation

**Where:** `odus/main.py` (line 52)

**Change:** `ft.app(target=app_main)` → `ft.run(target=app_main)`

---

#### 2. Replace Emoji Mascot with Proper Sprites

**Where:** `odus/ui/mascot.py` + `assets/mascot/`

**Current state:** The mascot uses emoji placeholders (🦉, 🔍, ✅, ❌, ⚠️). Replace with actual image assets.

**Options (pick one):**
1. **Generated sprites** — Use an AI image generator to create 5 owl mascot states
2. **SVG icons** — Use a consistent icon set (e.g., Lucide, Phosphor)
3. **Animated Lottie** — Use Lottie JSON animations for smooth transitions

**To use images in Flet:**
```python
# In mascot.py, replace ft.Text with ft.Image:
self._icon = ft.Image(
    src="assets/mascot/idle.png",
    width=120,
    height=120,
    fit=ft.ImageFit.CONTAIN,
)

# On state change:
def set_state(self, state: MascotState):
    self._icon.src = f"assets/mascot/{state.value}.png"
    self._icon.update()
```

**Sizing:** Aim for 120×120px sprites. The sidebar is 260px wide.

---

#### 3. Add "Thinking" Animation

**Where:** `odus/ui/mascot.py`

**Current state:** The progress ring appears during THINKING, but it's static feeling.

**Improvements:**
```python
# Option A: Animated text dots
self._thinking_text = ft.Text("Analyzing", size=FontSizes.SM)
# Run an async loop that cycles "Analyzing.", "Analyzing..", "Analyzing..."

# Option B: Pulsing opacity animation
self._icon.animate_opacity = ft.Animation(duration=800, curve=ft.AnimationCurve.EASE_IN_OUT)
# Toggle opacity between 0.4 and 1.0 during THINKING state

# Option C: Scale pulse
self._icon_container.animate_scale = ft.Animation(duration=600)
# Pulse between scale 1.0 and 1.1
```

---

### Priority 1 — Refinement (Hours 12–18)

#### 4. Smooth Transitions for Terminal Output

**Where:** `odus/ui/ghost_terminal.py`

**Add fade-in for new entries:**
```python
def _add_entry(self, text, color, prefix, bold=False):
    entry = ft.Container(
        content=...,
        opacity=0,
        animate_opacity=ft.Animation(duration=300, curve=ft.AnimationCurve.EASE_OUT),
    )
    self._output.controls.append(entry)
    self._output.update()

    # Trigger fade-in
    entry.opacity = 1
    entry.update()
```

---

#### 5. Status Bar

**Where:** `odus/ui/app.py` — add below the terminal

**Components:**
```python
status_bar = ft.Container(
    content=ft.Row([
        status_chip("Ready", Colors.SUCCESS, ft.Icons.CHECK_CIRCLE),
        ft.Container(expand=True),
        status_chip("Gemini Flash", Colors.ACCENT, ft.Icons.AUTO_AWESOME),
        status_chip("Last: 12:04:32", Colors.TEXT_SECONDARY, ft.Icons.ACCESS_TIME),
    ]),
    padding=ft.padding.symmetric(horizontal=Spacing.LG, vertical=Spacing.SM),
    bgcolor=Colors.BG_SECONDARY,
    border=ft.border.only(top=ft.BorderSide(1, Colors.BORDER)),
)
```

**Update on events:**
- `CAPTURE_DONE` → update "Last: HH:MM:SS"
- `ANALYSIS_DONE` → show "Ready" + model used
- `ERROR` → show "Error" in red

---

#### 6. Handle Streaming Tokens in Ghost Terminal

**Where:** `odus/ui/app.py` → `_handle_event()`

**DEV 2 will emit** `ANALYSIS_STREAMING` events with partial text. You need to append tokens to the terminal output in real-time.

```python
elif event.type == EventType.ANALYSIS_STREAMING:
    token = event.payload.get("token", "")
    # Append to the last terminal entry instead of creating a new one
    if self._streaming_entry is None:
        self._streaming_entry = self._create_streaming_entry()
        self._terminal._output.controls.append(self._streaming_entry)

    # Update the text content
    current = self._streaming_text.value or ""
    self._streaming_text.value = current + token
    self._streaming_text.update()
```

---

#### 7. History Panel (Stretch)

**Where:** New file `odus/ui/history.py`

**Purpose:** Sidebar tab or expandable panel showing past capture+analysis pairs.

```python
class HistoryPanel(ft.Column):
    """Shows past analyses as a scrollable list of cards."""

    def add_entry(self, timestamp: str, summary: str, commands: list[str]):
        card = ft.Container(
            content=ft.Column([
                ft.Text(timestamp, size=FontSizes.XS, color=Colors.TEXT_SECONDARY),
                ft.Text(summary, size=FontSizes.SM, color=Colors.TEXT_PRIMARY),
                ft.Text(f"{len(commands)} command(s)", size=FontSizes.XS),
            ]),
            bgcolor=Colors.BG_ELEVATED,
            border_radius=Radii.MD,
            padding=Spacing.MD,
            border=ft.border.all(1, Colors.BORDER),
            on_click=lambda e: self._on_select(entry),
        )
        self.controls.insert(0, card)  # Newest first
        self.update()
```

---

#### 8. Keyboard Navigation & Accessibility

**Where:** `odus/ui/app.py`

- [ ] `Escape` key closes confirmation dialog
- [ ] `Enter` key in dialog = "Fix it!" 
- [ ] Tab navigation between sidebar and terminal
- [ ] Screen reader hints on the mascot state

```python
# In app.py, add keyboard handler:
page.on_keyboard_event = self._handle_keyboard

def _handle_keyboard(self, e: ft.KeyboardEvent):
    if e.key == "Escape" and self._active_dialog:
        self._page.close(self._active_dialog)
    elif e.key == "Enter" and self._active_dialog:
        # Trigger confirm
        ...
```

---

#### 9. Responsive Resize Handling

**Where:** `odus/ui/app.py`

Handle window resize gracefully — collapse sidebar on narrow windows:

```python
page.on_resized = self._handle_resize

def _handle_resize(self, e):
    if page.window.width < 700:
        sidebar.visible = False
    else:
        sidebar.visible = True
    sidebar.update()
```

---

### Priority 2 — Demo Prep (Hours 18–24)

#### 10. Create Demo Script

**Where:** New file `odus/ui/demo.py` or hardcoded test scenarios

**Purpose:** For the live demo, pre-load 3 scenarios so you're not dependent on the API:

```python
DEMO_SCENARIOS = [
    {
        "name": "Terminal Error: Package Not Found",
        "summary": "The command 'htop' was not found",
        "explanation": "htop is a system monitor that isn't installed by default...",
        "commands": [{"command": "sudo apt install htop", "tier": 2}],
    },
    {
        "name": "Display Resolution Wrong",
        "summary": "Screen resolution is set to 800x600 instead of 1920x1080",
        "explanation": "Your display is running at a low resolution...",
        "commands": [{"command": "xrandr --output HDMI-1 --mode 1920x1080", "tier": 1}],
    },
    {
        "name": "Failed SSH Login Attempts",
        "summary": "Multiple failed SSH login attempts detected in logs",
        "explanation": "Someone has been trying to brute-force your SSH...",
        "commands": [{"command": "sudo ufw enable", "tier": 2}],
    },
]
```

**Trigger:** Add a hidden keyboard shortcut (e.g., `Ctrl+D`) that cycles through demo scenarios without actually calling the API.

---

## 📁 Files You Own

```
odus/ui/
├── __init__.py
├── theme.py            ← Design tokens (colors, fonts, spacing)
├── mascot.py           ← Mascot state machine
├── ghost_terminal.py   ← Terminal output display
├── components.py       ← Reusable controls (badges, dialogs, chips)
├── app.py              ← Main Flet application shell
├── history.py          ← [NEW] History panel (stretch)
└── demo.py             ← [NEW] Demo scenario presets

assets/
├── mascot/
│   ├── idle.png        ← [NEW] Mascot sprites
│   ├── thinking.png
│   ├── success.png
│   ├── error.png
│   └── warning.png
└── sounds/             ← [STRETCH] Feedback sounds
```

## 🔗 Your Interfaces

**You consume (other devs produce):**
- Event bus events from DEV 1 + DEV 2:
  - `CAPTURE_STARTED` → show thinking mascot
  - `CAPTURE_DONE` → show capture details
  - `ANALYSIS_STARTED` → show "Analyzing..."
  - `ANALYSIS_DONE` → display results in terminal
  - `ANALYSIS_STREAMING` → append tokens (when DEV 2 implements)
  - `CONFIRM_REQUIRED` → open confirmation dialog
  - `EXECUTION_STARTED` → show "Executing..."
  - `EXECUTION_DONE` → show stdout/stderr
  - `ERROR` → show error mascot + message

**You produce (other devs consume):**
- `USER_CONFIRMED` event → tells DEV 2's agent to execute the command
- `USER_DENIED` event → tells DEV 2's agent to cancel

## 🧪 Testing Your UI

There are no automated UI tests yet. Test manually:

```bash
# Launch the app
source .venv/bin/activate
python -m odus.main

# Check:
# 1. Window opens in landscape orientation
# 2. Sidebar shows "Odus" branding + mascot (🦉) + hotkey hint
# 3. Ghost Terminal shows welcome message
# 4. "Clear" button works
# 5. Press Ctrl+Shift+O → mascot should change to THINKING state
```

## 🎨 Design Token Quick Reference

```python
from odus.ui.theme import Colors, FontSizes, Fonts, Spacing, Radii

# Backgrounds
Colors.BG_PRIMARY     # "#0f1117" — main bg
Colors.BG_SECONDARY   # "#1a1d27" — panels
Colors.BG_ELEVATED    # "#22252f" — dialogs

# Accent
Colors.ACCENT         # "#6c63ff" — purple
Colors.SUCCESS        # "#22c55e" — green (tier 1)
Colors.WARNING        # "#eab308" — yellow (tier 2)
Colors.DANGER         # "#ef4444" — red (tier 3)

# Text
Colors.TEXT_PRIMARY    # "#e4e4e7" — light
Colors.TEXT_SECONDARY  # "#a1a1aa" — muted

# Fonts
Fonts.HEADING          # "Inter"
Fonts.MONO             # "JetBrains Mono"

# Terminal
Colors.TERMINAL_BG     # "#0a0c10"
Colors.TERMINAL_GREEN  # "#3fb950"
Colors.TERMINAL_RED    # "#f85149"
```
