# DEV 1 — System & Automation Developer

> **You own:** `odus/perception/` and `odus/action/`

---

## ✅ What's Already Implemented

### Perception Layer — `odus/perception/`

| File | Feature | Status | Notes |
|------|---------|--------|-------|
| `capture.py` | `ScreenCapture` class | ✅ Done | Fully functional |
| `capture.py` | X11 backend via `mss` | ✅ Done | Primary backend, auto-selected on X11 sessions |
| `capture.py` | Wayland backend via `grim` | ✅ Done | Auto-detected via `shutil.which("grim")` |
| `capture.py` | Wayland backend via `gnome-screenshot` | ✅ Done | Fallback for GNOME Wayland |
| `capture.py` | Session type auto-detection | ✅ Done | Reads `$XDG_SESSION_TYPE` env var |
| `capture.py` | `compress()` static method | ✅ Done | Resizes to ≤1280px wide, JPEG quality 75 |
| `capture.py` | `grab_region()` method | ✅ Done | Full capture + PIL crop |
| `hotkey.py` | `HotkeyListener` class | ✅ Done | Uses `pynput.keyboard.GlobalHotKeys` |
| `hotkey.py` | Configurable hotkey via `$ODUS_HOTKEY` | ✅ Done | Parses `ctrl+shift+o` format |
| `hotkey.py` | Event bus integration | ✅ Done | Emits `CAPTURE_STARTED` on press |

### Action Layer — `odus/action/`

| File | Feature | Status | Notes |
|------|---------|--------|-------|
| `safety.py` | `SafetyGate` classifier | ✅ Done | 14 blocked patterns, 18 caution patterns |
| `safety.py` | Tier 1/2/3 classification | ✅ Done | BLOCKED > CAUTION > SAFE priority |
| `executor.py` | `CommandExecutor.run()` | ✅ Done | subprocess with timeout + output capture |
| `executor.py` | Safety gate enforcement | ✅ Done | Raises `PermissionError` on Tier 3 |
| `executor.py` | Audit logging | ✅ Done | Writes to `~/.odus/audit.log` |
| `executor.py` | Output truncation | ✅ Done | Caps stdout at 10K chars, stderr at 5K |

### Tests

| File | Tests | Status |
|------|-------|--------|
| `tests/test_capture.py` | 6 tests (backend selection + compression) | ✅ All passing |
| `tests/test_executor.py` | 6 tests (run, fail, timeout, block, stderr, truncation) | ✅ All passing |
| `tests/test_safety.py` | 37 tests (12 safe, 12 caution, 10 blocked, 3 edge cases) | ✅ All passing |

---

## 🔲 What's Left To Build

### Priority 0 — Must Have for MVP (by Hour 12)

#### 1. Fix Wayland Hotkey (`pynput` may not work)

**Problem:** The app logs show `session=wayland`, meaning `pynput`'s `GlobalHotKeys` listener may silently fail to detect keypresses since it relies on X11 under the hood.

**Where:** `odus/perception/hotkey.py`

**What to do:**
```python
# Option A: Try pynput first, catch failure, fallback to evdev
# Option B: Use evdev directly (reads /dev/input, needs 'input' group)

# evdev approach:
import evdev
devices = [evdev.InputDevice(path) for path in evdev.list_devices()]
# Find keyboard device, listen for key combos
```

**Test:** Run the app on Wayland, press `Ctrl+Shift+O`, check if `CAPTURE_STARTED` event fires.

**Risk:** User may need to be added to the `input` group: `sudo usermod -aG input $USER`

---

#### 2. Verify Live Screen Capture on Wayland

**Problem:** The log shows `Wayland detected but no compatible tool found. Falling back to mss (may fail).` — this means `grim` is not installed on the dev machine.

**Where:** `odus/perception/capture.py`

**What to do:**
1. Install `grim`: `sudo apt install grim` (or distro equivalent)
2. Test: `grim -t png - > /tmp/test.png && file /tmp/test.png`
3. If `grim` isn't available for your compositor, add another fallback:
   ```python
   # For KDE Plasma Wayland:
   elif shutil.which("spectacle"):
       return self._capture_spectacle
   ```

**Test:** Call `ScreenCapture().grab_full_screen()` and verify you get valid PNG bytes.

---

#### 3. Wire Hotkey → Capture → Event (end-to-end)

**Problem:** The hotkey listener and capture engine are connected in `main.py` via the agent, but the agent listens for `CAPTURE_STARTED` and then calls capture internally. Verify this full chain works.

**Where:** `odus/reasoning/agent.py` line ~67 (`_handle_capture`)

**What to test:**
1. Press `Ctrl+Shift+O` → see `📸 Capturing screen...` in the Ghost Terminal
2. Verify compressed JPEG is under 300 KB
3. Check event bus emits `CAPTURE_DONE`

---

### Priority 1 — Refinement (Hours 12–18)

#### 4. Add `evdev` Hotkey Fallback for Wayland

**Where:** `odus/perception/hotkey.py`

```python
class EvdevHotkeyListener:
    """Fallback hotkey listener using evdev (works on Wayland)."""

    def __init__(self, on_trigger):
        self._on_trigger = on_trigger
        # Find keyboard device
        self._device = self._find_keyboard()

    def _find_keyboard(self):
        import evdev
        for path in evdev.list_devices():
            dev = evdev.InputDevice(path)
            caps = dev.capabilities(verbose=True)
            if ('EV_KEY', 1) in caps:
                return dev
        raise RuntimeError("No keyboard found")

    async def listen(self):
        import evdev
        async for event in self._device.async_read_loop():
            # Detect Ctrl+Shift+O combo
            ...
```

**Note:** `evdev` is already installed as a dependency of `pynput`.

---

#### 5. Audit Log Improvements

**Where:** `odus/action/executor.py`

- [ ] Add JSON format instead of plain text (easier to parse)
- [ ] Add rotation (max 1MB, keep last 3 files)
- [ ] Add session ID to correlate commands within a capture cycle

---

#### 6. Input Simulation Wrapper (Stretch Goal)

**Where:** `odus/action/input_sim.py` (new file)

**Purpose:** For fixes that require GUI interaction (clicking buttons, typing into dialogs) rather than CLI commands.

```python
class InputSimulator:
    """Wraps PyAutoGUI (X11) or ydotool (Wayland)."""

    def click(self, x: int, y: int): ...
    def type_text(self, text: str): ...
    def hotkey(self, *keys): ...
```

**⚠️ Warning:** PyAutoGUI does NOT work on Wayland. Use `ydotool` instead:
```bash
# Install: sudo apt install ydotool
# Requires /dev/uinput access
ydotool click 0xC0    # left click
ydotool type "hello"  # type text
```

---

## 📁 Files You Own

```
odus/perception/
├── __init__.py
├── capture.py      ← Screen capture engine
├── hotkey.py       ← Global hotkey listener
└── daemon.py       ← [NEW] Background monitor (stretch)

odus/action/
├── __init__.py
├── executor.py     ← Sandboxed subprocess runner
├── safety.py       ← Tiered permission gate
└── input_sim.py    ← [NEW] PyAutoGUI/ydotool wrapper (stretch)
```

## 🔗 Your Interfaces

**You produce (other devs consume):**
- `CaptureResult` — PNG bytes + dimensions → consumed by DEV 2's `VisionAnalyzer`
- `ExecutionResult` — stdout/stderr/return_code → consumed by DEV 3's Ghost Terminal
- `SafetyVerdict` — SAFE/NEEDS_CONFIRMATION/BLOCKED → consumed by DEV 2's Agent

**You consume (other devs produce):**
- Event bus events: `USER_CONFIRMED` from DEV 3's UI

## 🧪 Running Your Tests

```bash
# All your tests
.venv/bin/pytest tests/test_capture.py tests/test_executor.py tests/test_safety.py -v

# Quick smoke test for capture
python -c "from odus.perception.capture import ScreenCapture; s = ScreenCapture(); print(f'Backend: {s._backend.__name__}')"
```
