# 🛠️ Developer Guides

This folder contains per-developer task guides for continuing the Odus build.

| File | Owner | Scope |
|------|-------|-------|
| [DEV1_SYSTEM.md](DEV1_SYSTEM.md) | System & Automation Dev | Perception + Action layers |
| [DEV2_AI.md](DEV2_AI.md) | AI Logic & Orchestration Dev | Reasoning layer |
| [DEV3_UI.md](DEV3_UI.md) | UI/UX & Mascot Dev | UI layer + assets |

## Quick Architecture Reminder

```
Hotkey → ScreenCapture → [event bus] → VisionAnalyzer → Agent → [event bus] → SafetyGate → Executor → [event bus] → UI
```

**All layers communicate ONLY via the event bus** (`odus/events.py`).  
No developer should import another layer's internal modules.
