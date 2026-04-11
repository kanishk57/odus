"""
System Prompts & Tool Schemas for the Gemini Vision API.

DEV 2 owns this module.

Contains:
  - SYSTEM_PROMPT: The Linux mentor persona
  - TOOL_DECLARATIONS: Function-calling schemas for run_command, explain, suggest_fix
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

## Rules
1. **Be specific.** Don't say "check your config" — say exactly which file \
to edit and what to change.
2. **Be safe.** Never suggest destructive commands (rm -rf, dd, mkfs, \
curl|bash). If the fix requires a dangerous operation, explain what it \
would do and suggest a safer alternative.
3. **One fix at a time.** Suggest a single command first. If follow-up \
is needed, wait for the result before suggesting the next step.
4. **Explain like a teacher.** The user is learning. After the fix, \
briefly teach them why it works.

## Safety Tiers
For EVERY command you suggest, classify it into one of these tiers:
- **tier_1** (SAFE): Read-only or informational commands. Examples: \
`ls`, `cat`, `systemctl status`, `apt list`, `ping`, `df -h`, `whoami`.
- **tier_2** (CAUTION): Commands that modify system state but are \
recoverable. Examples: `sudo apt install X`, `systemctl restart X`, \
`chmod 755 X`, `pip install X`.
- **tier_3** (DANGER): Destructive or irreversible commands. Examples: \
`rm -rf`, `dd`, `mkfs`, `chmod 777`, `curl|bash`. \
**NEVER suggest tier_3 commands.** Instead, explain the risk and \
suggest a safer alternative.

## Output Format
Always respond with a JSON object matching this exact schema:
```json
{
  "summary": "One-line description of the problem",
  "explanation_for_user": "Beginner-friendly explanation (2-4 sentences)",
  "suggested_commands": [
    {
      "command": "the exact CLI command",
      "description": "what this command does",
      "safety_tier": 1
    }
  ],
  "confidence": 0.85,
  "follow_up_hint": "Optional — what to check next if this doesn't work"
}
```

If no issue is detected in the screenshot, say so clearly and set \
`suggested_commands` to an empty list.
"""

# ── Tool Declarations (for Gemini function calling) ────────────────────

TOOL_DECLARATIONS = [
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
]
