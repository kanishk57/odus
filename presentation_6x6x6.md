# Odus — AI Linux Mentor (Technical Overview)

---

## Slide 1: Odus Core Architecture Context
**Goal:** Automate Linux desktop issue remediation using vision models and sandboxed execution, minimizing cognitive friction for end-users.
- **Trigger Phase:** Global shortcut driven screenshot capture.
- **Analysis Phase:** Multimodal processing pipeline via Google Gemini LLMs.
- **Remediation Phase:** Automated Bash execution with explicit sandbox restrictions.

---

## Slide 2: UI & Frontend Infrastructure (DEV 3 Layer)
**Framework:** Flet (Flutter-powered Python desktop UI framework) bound directly to native OS views.
**Key Components & Tools:**
- **Ghost Terminal:** Async scrollable terminal using `JetBrains Mono`. Color-codes events and command outputs (`add_success`, `add_warning`, `add_command`).
- **Dynamic Mascot Agent:** A state-machine interface reacting to application states (IDLE, THINKING, SUCCESS, ERROR, WARNING) using responsive graphical sprites.
- **Streaming Pipeline:** Captures `ANALYSIS_STREAMING` event bus payloads to display raw AI tokens in real-time.
- **Design Token System:** Hardcoded palette managed through `Colors`, `Fonts` (hotloaded via Google Fonts CDN).
- **Offline Demo Engine:** Scripted local fallback generator decoupling the frontend from the API loop for testing.

---

## Slide 3: Perception & Capture System (DEV 1 Layer)
**Responsibility:** Fetching visual server telemetry and registering OS-level keyboard hooks across display servers.
**Key Components & Tools:**
- **X11 Capture:** Uses the `mss` library for high-speed screenshot frames interacting with X server APIs.
- **Wayland Pipeline:** Utilizes `grim` as the primary standard or `gnome-screenshot` as fallback. Dynamically scopes environments reading `$XDG_SESSION_TYPE`.
- **Global Event Listeners:** Keybindings tracked via `pynput.keyboard.GlobalHotKeys`, enhanced by a deep `evdev` (/dev/input) fallback system for permission-restricted Wayland environments.
- **Processing Engine:** Uses `PIL/Pillow` to instantly downsample display matrices to ≤1280px wide and aggressively compress (JPEG Q75) before multimodal API transmission.

---

## Slide 4: Action & Sandboxing Engine (DEV 1 Layer)
**Responsibility:** Secure, isolated execution of AI-generated shell remediation scripts.
**Key Components & Tools:**
- **Subprocess Engine:** Routes commands via wrapped subprocess implementations using strict CPU/Execution timeouts.
- **Aggressive Truncation:** Caps trailing `stdout` at 10,000 chars and `stderr` at 5,000 to prevent GUI freezes during log analysis outputs.
- **GUI Input Simulation:** Extensibility layer utilizing `PyAutoGUI` for legacy X11 and raw `ydotool` (/dev/uinput) targeting modern Wayland compositors.
- **The Safety Gate Regex Appraiser:**
  - Analyzes raw script text against deterministic pattern layers BEFORE system execution.
  - Flags **14 distinct Tier 3 Threat** parameters that force immediate blockade (`rm -rf`, `curl \| bash`).
  - Flags **18 distinct Tier 2 Caution** parameters that halt workflows for explicit user confirmation via dialog (`sudo`, `chmod`).

---

## Slide 5: AI Logic & Agentic Orchestration (DEV 2 Layer)
**Responsibility:** Core logic loop driving the `google-genai` Google AI Studio SDK.
**Key Components & Tools:**
- **Dual-Model Escalation Pipeline:** Triggers base analysis via the lightning-fast `gemini-2.5-flash`; automatically escalates the frame buffer to the heavier `gemini-2.5-pro` model if the confidence probability score drops below `< 0.6`.
- **Native Function Tooling:** Deprecates regex JSON parsing for Gemini's native `types.FunctionDeclaration` (Tool Calling) framework, explicitly routing payloads logically to `run_command`, `explain`, and `suggest_fix` schemas.
- **Resiliency Module:** Maps Python's `tenacity` decorator library to build automatic exponential backoff systems mitigating network disconnects and HTTP 429 Rate Limits.
- **Sliding Memory Context:** Implements a localized multi-turn history structure allowing conversational state-referencing up to a depth of $N=3$.

---

## Slide 6: Event Backend & Development Environment
**Key Components & Tools:**
- **Internal Choreography:** Runs all 4 core layers asynchronously utilizing a completely decoupled `Event Bus` (transmitting `USER_CONFIRMED`, `ANALYSIS_STREAMING`, etc).
- **Environment Targeting:** Fully statically designed around Python 3.11+ asynchronous runtime and typing engines.
- **Assertion and Coverage Engine:** Powered by `pytest` running localized mock tests spanning SDK timeout faults, vision classification confidence drops, and explicit regex safety-gate bypass attempts.
- **Audit Logging Protocol:** Generates localized `JSON` structured action sequences inside `~/.odus/audit.log` tying execution histories securely.
