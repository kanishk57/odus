"""
System Prompts & Tool Schemas for the Gemini Vision API.

DEV 2 owns this module.

Contains:
  - SYSTEM_PROMPT: The Linux mentor persona (now with desktop control powers)
  - TOOL_DECLARATIONS: Function-calling schemas for all tools
  - Safety tier classification instructions embedded in the prompt
"""

from __future__ import annotations

# ── System Prompt ──────────────────────────────────────────────────────

SYSTEM_PROMPT = """\
You are **Odus**, a friendly and patient AI mentor for Linux beginners.

## Your Role
- You analyze screenshots of a user's Linux desktop (terminals, GUIs, logs, \
settings panels) and identify problems, errors, or misconfigurations.
- You explain issues in simple, beginner-friendly language.
- You suggest precise CLI commands to fix the issue.
- You can also **control the user's desktop** by clicking, typing, and \
navigating the GUI to guide them step by step.

## Capabilities
You have TWO kinds of tools:

### 1. CLI Tools
- `run_command` — execute a shell command
- `explain` — teach the user something without running anything
- `suggest_fix` — suggest a command that needs user approval

### 2. Desktop Control Tools (NEW)
- `move_and_click` — move the mouse to a screen coordinate and click
- `type_text` — type text into the currently focused element
- `press_key` — press a keyboard key or shortcut (Enter, Tab, Ctrl+S, etc.)
- `scroll_screen` — scroll the mouse wheel up/down
- `highlight_area` — draw a visual highlight on the screen to show the user \
where to look (non-destructive, always safe)

## Rules
1. **Be specific.** Don't say "check your config" — say exactly which file \
to edit and what to change.
2. **Be safe.** Never suggest destructive commands (rm -rf, dd, mkfs, \
curl|bash). If the fix requires a dangerous operation, explain what it \
would do and suggest a safer alternative.
3. **One step at a time.** When creating a plan with multiple steps, \
list them clearly. Each step should be a single action (one click, one \
command, one keystroke). Wait for verification before continuing.
4. **Explain like a teacher.** The user is learning. After the fix, \
briefly teach them why it works.
5. **Prefer highlighting first.** Before clicking or typing, use \
`highlight_area` to show the user WHERE you intend to act, so they \
can follow along.
6. **Describe targets clearly.** When using desktop control tools, \
always include a clear `target_description` (e.g., "Save button in \
the top-right corner of the Preferences window").

## Safety Tiers
For EVERY action you suggest, classify it into one of these tiers:

### CLI Commands
- **tier_1** (SAFE): Read-only or informational commands. Examples: \
`ls`, `cat`, `systemctl status`, `apt list`, `ping`, `df -h`, `whoami`.
- **tier_2** (CAUTION): Commands that modify system state but are \
recoverable. Examples: `sudo apt install X`, `systemctl restart X`, \
`chmod 755 X`, `pip install X`.
- **tier_3** (DANGER): Destructive or irreversible commands. Examples: \
`rm -rf`, `dd`, `mkfs`, `chmod 777`, `curl|bash`. \
**NEVER suggest tier_3 commands.** Instead, explain the risk and \
suggest a safer alternative.

### Desktop Actions
- **tier_1** (SAFE): `highlight_area`, `scroll_screen` — visual only.
- **tier_2** (CAUTION): `move_and_click`, `type_text`, `press_key` — \
changes desktop state, needs user confirmation.
- **tier_3** (DANGER): Any action targeting password fields, sudo prompts, \
authentication dialogs, security settings. **NEVER act on these.**

## Output Format
Always respond with a JSON object matching this exact schema:
```json
{
  "summary": "One-line description of the problem",
  "explanation_for_user": "Beginner-friendly explanation (2-4 sentences)",
  "plan": [
    {
      "step": 1,
      "action_type": "highlight_area | move_and_click | type_text | press_key | scroll_screen | run_command | explain",
      "params": {},
      "description": "What this step does",
      "safety_tier": 1
    }
  ],
  "confidence": 0.85,
  "follow_up_hint": "Optional — what to check next if this doesn't work"
}
```

If no issue is detected in the screenshot, say so clearly and set \
`plan` to an empty list.

When the plan has multiple steps, number them sequentially. The agent \
will execute them one at a time and re-capture the screen between steps \
to verify success.
"""

# ── Tool Declarations (for Gemini function calling) ────────────────────

TOOL_DECLARATIONS = [
    # ── CLI Tools ──────────────────────────────────────────────────────
    {
        "name": "run_command",
        "description": (
            "Execute a CLI command on the user's Linux system. "
            "The command runs in a sandboxed subprocess with a timeout. "
            "Returns stdout, stderr, and exit code."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "The exact shell command to execute.",
                },
                "safety_tier": {
                    "type": "integer",
                    "description": "Safety classification: 1=safe, 2=caution, 3=danger.",
                    "enum": [1, 2, 3],
                },
                "explanation": {
                    "type": "string",
                    "description": "Beginner-friendly explanation of what this command does.",
                },
            },
            "required": ["command", "safety_tier", "explanation"],
        },
    },
    {
        "name": "explain",
        "description": (
            "Provide an educational explanation without running any command. "
            "Use this when the screenshot shows something interesting "
            "but no action is needed."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "topic": {
                    "type": "string",
                    "description": "The topic being explained.",
                },
                "explanation": {
                    "type": "string",
                    "description": "Clear, beginner-friendly explanation.",
                },
            },
            "required": ["topic", "explanation"],
        },
    },
    {
        "name": "suggest_fix",
        "description": (
            "Suggest a fix to the user without auto-executing it. "
            "Use this for tier_2 commands that need user confirmation."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "The suggested command.",
                },
                "safety_tier": {
                    "type": "integer",
                    "description": "Safety classification (should be 2 for caution).",
                },
                "explanation": {
                    "type": "string",
                    "description": "Why this fix is needed and what it does.",
                },
                "risk_warning": {
                    "type": "string",
                    "description": "What could go wrong if this command fails.",
                },
            },
            "required": ["command", "safety_tier", "explanation"],
        },
    },

    # ── Desktop Control Tools ──────────────────────────────────────────
    {
        "name": "move_and_click",
        "description": (
            "Move the mouse cursor to the specified screen coordinates "
            "and click. Use this to interact with GUI elements like buttons, "
            "menus, text fields, tabs, etc."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "x": {
                    "type": "integer",
                    "description": "X coordinate (pixels from left edge of screen).",
                },
                "y": {
                    "type": "integer",
                    "description": "Y coordinate (pixels from top edge of screen).",
                },
                "button": {
                    "type": "string",
                    "description": "Mouse button: 'left', 'right', or 'middle'.",
                    "enum": ["left", "right", "middle"],
                },
                "click_type": {
                    "type": "string",
                    "description": "Click type: 'single' or 'double'.",
                    "enum": ["single", "double"],
                },
                "target_description": {
                    "type": "string",
                    "description": (
                        "Human-readable description of what is at those coordinates. "
                        "E.g., 'Save button in Firefox toolbar'."
                    ),
                },
                "safety_tier": {
                    "type": "integer",
                    "description": "Safety classification: 1=safe, 2=caution.",
                    "enum": [1, 2],
                },
                "explanation": {
                    "type": "string",
                    "description": "Why this click is needed.",
                },
            },
            "required": ["x", "y", "target_description", "safety_tier", "explanation"],
        },
    },
    {
        "name": "type_text",
        "description": (
            "Type a string of text into the currently focused GUI element. "
            "Make sure the correct element is focused (via a prior click) "
            "before calling this."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "The text to type.",
                },
                "target_description": {
                    "type": "string",
                    "description": (
                        "Description of the focused element. "
                        "E.g., 'search bar in GNOME Settings'."
                    ),
                },
                "safety_tier": {
                    "type": "integer",
                    "description": "Safety classification: 1=safe, 2=caution.",
                    "enum": [1, 2],
                },
                "explanation": {
                    "type": "string",
                    "description": "Why this typing action is needed.",
                },
            },
            "required": ["text", "target_description", "safety_tier", "explanation"],
        },
    },
    {
        "name": "press_key",
        "description": (
            "Press a keyboard key or key combination. "
            "Use for shortcuts (Ctrl+S, Ctrl+C), navigation (Tab, Enter, Escape), "
            "or special keys (F5, Delete, Home)."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "keys": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": (
                        "List of keys to press simultaneously. "
                        "E.g., ['ctrl', 's'] for Ctrl+S, or ['enter'] for Enter."
                    ),
                },
                "target_description": {
                    "type": "string",
                    "description": "What this keystroke is targeting.",
                },
                "safety_tier": {
                    "type": "integer",
                    "description": "Safety classification: 1=safe, 2=caution.",
                    "enum": [1, 2],
                },
                "explanation": {
                    "type": "string",
                    "description": "Why this key press is needed.",
                },
            },
            "required": ["keys", "target_description", "safety_tier", "explanation"],
        },
    },
    {
        "name": "scroll_screen",
        "description": (
            "Scroll the mouse wheel to navigate content. "
            "Always safe — doesn't modify anything."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "direction": {
                    "type": "string",
                    "description": "Scroll direction.",
                    "enum": ["up", "down", "left", "right"],
                },
                "amount": {
                    "type": "integer",
                    "description": "Number of scroll increments (default: 3).",
                },
                "explanation": {
                    "type": "string",
                    "description": "Why scrolling is needed.",
                },
            },
            "required": ["direction", "explanation"],
        },
    },
    {
        "name": "highlight_area",
        "description": (
            "Draw a temporary visual highlight (glowing rectangle) on the screen "
            "to show the user where to look. This is purely visual and does NOT "
            "interact with the desktop. Always safe."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "x": {
                    "type": "integer",
                    "description": "X coordinate of the highlight rectangle's top-left corner.",
                },
                "y": {
                    "type": "integer",
                    "description": "Y coordinate of the highlight rectangle's top-left corner.",
                },
                "width": {
                    "type": "integer",
                    "description": "Width of the highlight rectangle in pixels.",
                },
                "height": {
                    "type": "integer",
                    "description": "Height of the highlight rectangle in pixels.",
                },
                "explanation": {
                    "type": "string",
                    "description": "What this area shows and why the user should look here.",
                },
            },
            "required": ["x", "y", "width", "height", "explanation"],
        },
    },
]
