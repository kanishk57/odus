"""
Tiered Safety Gate — classifies commands by danger level.

DEV 1 owns this module. DEV 2 defines the classification rules in prompts.py.

Tiers:
  1 (SAFE):    Read-only / informational — auto-execute
  2 (CAUTION): Modifies system state — needs user confirmation
  3 (DANGER):  Destructive / irreversible — ALWAYS BLOCKED
"""

from __future__ import annotations

import logging
import re
from enum import Enum

logger = logging.getLogger(__name__)


class SafetyVerdict(Enum):
    """Result of the safety classification."""

    SAFE = 1
    NEEDS_CONFIRMATION = 2
    BLOCKED = 3


# ── Classification Rules ───────────────────────────────────────────────

BLOCKED_PATTERNS: list[re.Pattern] = [
    re.compile(p, re.IGNORECASE)
    for p in [
        r"rm\s+(-[a-zA-Z]*r[a-zA-Z]*f|--recursive)",  # rm -rf, rm -fr, etc.
        r"\brm\s+-rf\b",
        r"\bdd\b\s+",                                   # dd — disk destroyer
        r"mkfs\.",                                       # mkfs.ext4, etc.
        r"curl.*\|\s*(ba)?sh",                           # curl | bash
        r"wget.*\|\s*(ba)?sh",                           # wget | bash
        r"chmod\s+777",                                  # world-writable
        r">\s*/dev/sd",                                  # redirect to block device
        r">\s*/dev/nvme",
        r"format\s+/dev",
        r"\bshred\b",                                    # secure delete
        r":\(\)\s*\{",                                   # fork bomb
        r"\bmv\s+/\s",                                   # mv / (root)
        r"\brm\s+/\s",                                   # rm / (root)
    ]
]

CAUTION_PATTERNS: list[re.Pattern] = [
    re.compile(p, re.IGNORECASE)
    for p in [
        r"\bsudo\b",
        r"systemctl\s+(restart|stop|enable|disable|mask)",
        r"chmod\b",
        r"chown\b",
        r"apt\s+(install|remove|purge|upgrade|dist-upgrade)",
        r"dnf\s+(install|remove|erase|upgrade)",
        r"pacman\s+-[SRU]",
        r"pip\s+install",
        r"pip3\s+install",
        r"\bkill\b",
        r"\bkillall\b",
        r"\breboot\b",
        r"\bshutdown\b",
        r"\bpoweroff\b",
        r"iptables\b",
        r"ufw\b",
        r"\bmount\b",
        r"\bumount\b",
    ]
]


class SafetyGate:
    """
    Classifies shell commands into safety tiers using regex patterns.

    Usage:
        gate = SafetyGate()
        verdict = gate.classify("sudo apt install vim")
        # → SafetyVerdict.NEEDS_CONFIRMATION

        verdict = gate.classify("rm -rf /")
        # → SafetyVerdict.BLOCKED
    """

    def classify(self, command: str) -> SafetyVerdict:
        """
        Classify a command's safety tier.

        Priority: BLOCKED > CAUTION > SAFE
        """
        command_stripped = command.strip()

        # Check blocked patterns first (highest priority)
        for pattern in BLOCKED_PATTERNS:
            if pattern.search(command_stripped):
                logger.warning(
                    "🚫 BLOCKED: '%s' matched pattern '%s'",
                    command_stripped,
                    pattern.pattern,
                )
                return SafetyVerdict.BLOCKED

        # Check caution patterns
        for pattern in CAUTION_PATTERNS:
            if pattern.search(command_stripped):
                logger.info(
                    "⚠️  CAUTION: '%s' matched pattern '%s'",
                    command_stripped,
                    pattern.pattern,
                )
                return SafetyVerdict.NEEDS_CONFIRMATION

        # Default: safe
        logger.debug("✅ SAFE: '%s'", command_stripped)
        return SafetyVerdict.SAFE

    def is_safe(self, command: str) -> bool:
        """Quick check: is this command safe to auto-execute?"""
        return self.classify(command) == SafetyVerdict.SAFE

    def is_blocked(self, command: str) -> bool:
        """Quick check: is this command blocked?"""
        return self.classify(command) == SafetyVerdict.BLOCKED

    # ── GUI / Input Action Classification ──────────────────────────────

    # Actions that are always safe (read-only / visual feedback)
    _SAFE_ACTIONS = frozenset({
        "highlight", "highlight_area",
        "scroll", "scroll_screen",
    })

    # Actions that always need user confirmation
    _CAUTION_ACTIONS = frozenset({
        "click", "move_and_click",
        "double_click",
        "right_click",
        "type_text",
        "press_key",
        "hotkey",
        "drag", "drag_element",
    })

    # Keywords in target descriptions that trigger a BLOCKED verdict
    _DANGER_TARGET_PATTERNS: list[re.Pattern] = [
        re.compile(p, re.IGNORECASE)
        for p in [
            r"password",
            r"sudo\s+prompt",
            r"authentication",
            r"polkit",
            r"keyring",
            r"credential",
            r"security\s+settings",
            r"firewall",
            r"root\s+terminal",
            r"disk\s+management",
            r"format\s+partition",
        ]
    ]

    def classify_input_action(
        self,
        action_type: str,
        target_description: str = "",
    ) -> SafetyVerdict:
        """
        Classify a GUI / input action's safety tier.

        Args:
            action_type: The action name (e.g. 'click', 'type_text', 'highlight').
            target_description: Free-text description of the target element
                                (e.g. 'Save button in Firefox').

        Returns:
            SafetyVerdict — SAFE, NEEDS_CONFIRMATION, or BLOCKED.
        """
        action_lower = action_type.lower().strip()

        # 1. Check dangerous targets first (highest priority)
        if target_description:
            for pattern in self._DANGER_TARGET_PATTERNS:
                if pattern.search(target_description):
                    logger.warning(
                        "🚫 BLOCKED input action '%s' — target '%s' "
                        "matched danger pattern '%s'",
                        action_lower, target_description, pattern.pattern,
                    )
                    return SafetyVerdict.BLOCKED

        # 2. Always-safe actions
        if action_lower in self._SAFE_ACTIONS:
            logger.debug("✅ SAFE input action: %s", action_lower)
            return SafetyVerdict.SAFE

        # 3. Caution actions — need user confirmation
        if action_lower in self._CAUTION_ACTIONS:
            logger.info(
                "⚠️  CAUTION input action: %s (target: %s)",
                action_lower, target_description or "unspecified",
            )
            return SafetyVerdict.NEEDS_CONFIRMATION

        # 4. Unknown actions — default to caution
        logger.info("⚠️  Unknown input action '%s' — defaulting to CAUTION", action_lower)
        return SafetyVerdict.NEEDS_CONFIRMATION

