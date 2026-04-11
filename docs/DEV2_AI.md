# DEV 2 — AI Logic & Orchestration Developer

> **You own:** `odus/reasoning/`

---

## ✅ What's Already Implemented

### Reasoning Layer — `odus/reasoning/`

| File | Feature | Status | Notes |
|------|---------|--------|-------|
| `prompts.py` | `SYSTEM_PROMPT` — Linux mentor persona | ✅ Done | Includes safety tier instructions, JSON output schema |
| `prompts.py` | `TOOL_DECLARATIONS` — function calling schemas | ✅ Done | `run_command`, `explain`, `suggest_fix` defined |
| `vision.py` | `VisionAnalyzer` class | ✅ Done | Wraps `google-genai` SDK |
| `vision.py` | `analyze()` method | ✅ Done | Sends JPEG via `Part.from_bytes()`, returns `AnalysisResult` |
| `vision.py` | JSON response parsing | ✅ Done | Handles clean JSON, markdown-fenced JSON, and raw text fallback |
| `vision.py` | `AnalysisResult` dataclass | ✅ Done | summary, explanation, commands list, confidence, follow_up |
| `vision.py` | `SuggestedCommand` dataclass | ✅ Done | command string, description, safety_tier |
| `vision.py` | Dual model support | ✅ Done | `ODUS_MODEL_FAST` and `ODUS_MODEL_DEEP` env vars |
| `tools.py` | `tool_run_command()` | ✅ Done | Routes through safety gate, returns execution results |
| `tools.py` | `tool_explain()` | ✅ Done | Returns explanation dict |
| `tools.py` | `tool_suggest_fix()` | ✅ Done | Returns confirmation-needed dict |
| `agent.py` | `Agent` class | ✅ Done | Full agentic loop with event bus integration |
| `agent.py` | `_handle_capture()` | ✅ Done | Capture → compress → analyze → route pipeline |
| `agent.py` | `_process_analysis()` | ✅ Done | Tier routing: auto/confirm/block |
| `agent.py` | `_handle_user_confirmed()` | ✅ Done | Executes confirmed Tier 2 commands |

### Tests

| File | Tests | Status |
|------|-------|--------|
| `tests/test_vision.py` | 4 tests (JSON parsing, markdown fences, fallback, empty) | ✅ All passing |

---

## 🔲 What's Left To Build

### Priority 0 — Must Have for MVP (by Hour 12)

#### 1. Test with Real Screenshots (5 scenarios)

**This is your most important task.** The scaffolding works, but the prompts haven't been validated against real Linux screenshots.

**What to do:**
1. Capture 5 real screenshots manually:
   - **Terminal error:** `command not found` or `package not installed`
   - **Broken GUI:** display resolution wrong, theme broken
   - **Log file:** `journalctl` output with errors
   - **Package manager:** `apt upgrade` with held packages
   - **System settings:** wrong timezone, locale issues

2. Test each one:
   ```python
   import asyncio
   from dotenv import load_dotenv
   load_dotenv()

   from odus.reasoning.vision import VisionAnalyzer

   async def test():
       analyzer = VisionAnalyzer()
       with open("screenshot.jpg", "rb") as f:
           result = await analyzer.analyze(f.read(), "I see an error")
       print(f"Summary: {result.summary}")
       print(f"Confidence: {result.confidence}")
       for cmd in result.suggested_commands:
           print(f"  [{cmd.safety_tier}] {cmd.command} — {cmd.description}")

   asyncio.run(test())
   ```

3. **Tune the prompt** in `prompts.py` based on failure modes:
   - Does the model return valid JSON consistently?
   - Are safety tiers assigned correctly?
   - Is the explanation actually beginner-friendly?
   - Does it suggest reasonable commands?

---

#### 2. Improve JSON Output Reliability

**Problem:** Gemini sometimes returns extra text before/after JSON, or uses slightly different key names.

**Where:** `odus/reasoning/vision.py` → `_parse_response()`

**What to improve:**
```python
def _parse_response(self, raw_text: str) -> AnalysisResult:
    # Current: strips ``` fences
    # Needed: also handle:
    #   - "Here's my analysis:\n```json\n{...}\n```"
    #   - JSON with trailing commas
    #   - Response starting with explanation then JSON

    # Strategy: find first { and last }, extract that substring
    start = raw_text.find("{")
    end = raw_text.rfind("}") + 1
    if start != -1 and end > start:
        json_str = raw_text[start:end]
        data = json.loads(json_str)
        ...
```

**Test:** Run the 5 screenshots above 3 times each. Count JSON parse failures.

---

#### 3. Validate Safety Tier Assignments

**Problem:** The AI model assigns safety tiers in its JSON response, but DEV 1's `SafetyGate` also classifies independently via regex. These could disagree.

**Where:** `odus/reasoning/tools.py` → `tool_run_command()`

**Current behavior:** The safety gate's regex classification overrides the AI's tier. This is correct (defense in depth), but you should verify the AI isn't consistently mis-classifying — which would mean your prompt needs tuning.

**What to check:**
```python
# In tool_run_command(), after safety classification:
if verdict.value != safety_tier:
    logger.warning(
        "Safety disagreement: AI said tier %d, regex said %s for: %s",
        safety_tier, verdict.name, command
    )
```

---

### Priority 1 — Refinement (Hours 12–18)

#### 4. Add Streaming Response Support

**Where:** `odus/reasoning/vision.py`

**Purpose:** Show analysis text in the Ghost Terminal as it arrives, instead of waiting for the full response.

```python
async def analyze_streaming(
    self,
    image_bytes: bytes,
    user_context: str = "",
) -> AsyncGenerator[str, None]:
    """Stream partial tokens from Gemini."""
    response = self._client.models.generate_content_stream(
        model=self._model_fast,
        contents=[
            types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg"),
            prompt_text,
        ],
    )
    for chunk in response:
        if chunk.text:
            yield chunk.text
```

**Event bus integration:**
```python
# In agent.py, emit partial tokens:
await self._bus.emit(OdusEvent(
    EventType.ANALYSIS_STREAMING,
    {"token": partial_text}
))
```

**DEV 3 will need to handle** `ANALYSIS_STREAMING` events in the Ghost Terminal.

---

#### 5. Multi-Turn Conversation History

**Where:** `odus/reasoning/agent.py`

**Purpose:** Let the AI remember the last 3 interactions so it can say "I see you tried my first suggestion but it didn't work — let's try this instead."

```python
class Agent:
    def __init__(self):
        ...
        self._history: list[dict] = []  # Last N interactions
        self._max_history = 3

    async def _handle_capture(self):
        ...
        # Include history in the analysis context
        history_context = self._format_history()
        analysis = await self._vision.analyze(
            compressed,
            user_context=history_context,
        )
        # Store the result
        self._history.append({
            "screenshot_summary": analysis.summary,
            "commands": [c.command for c in analysis.suggested_commands],
            "result": "pending",
        })
        if len(self._history) > self._max_history:
            self._history.pop(0)
```

---

#### 6. Dual-Model Strategy (Flash → Pro Escalation)

**Where:** `odus/reasoning/agent.py` + `vision.py`

**Purpose:** Use `gemini-2.5-flash` for fast initial triage. If confidence is low (< 0.6), automatically re-analyze with `gemini-2.5-pro`.

```python
async def _handle_capture(self):
    ...
    # First pass: fast model
    analysis = await self._vision.analyze(compressed, use_deep_model=False)

    if analysis.confidence < 0.6 and analysis.suggested_commands:
        logger.info("Low confidence (%.2f) — escalating to Pro model", analysis.confidence)
        analysis = await self._vision.analyze(compressed, use_deep_model=True)
    ...
```

---

#### 7. Error Recovery & Retry Logic

**Where:** `odus/reasoning/vision.py` → `analyze()`

**What to handle:**
- API key invalid → clear error message
- Rate limit (429) → exponential backoff with max 3 retries
- Network timeout → retry once
- Malformed response → fallback parsing (already partially done)

```python
import tenacity  # Already installed as a dependency

@tenacity.retry(
    stop=tenacity.stop_after_attempt(3),
    wait=tenacity.wait_exponential(multiplier=1, min=1, max=10),
    retry=tenacity.retry_if_exception_type((httpx.TimeoutException, httpx.HTTPStatusError)),
)
async def _call_api(self, ...):
    ...
```

---

### Priority 2 — Stretch Goals

#### 8. Function Calling Mode (Native Gemini Tool Use)

Instead of instructing the model to return JSON and parsing it yourself, use Gemini's **native function calling** feature:

```python
from google.genai import types

tools = types.Tool(function_declarations=[
    types.FunctionDeclaration(
        name="run_command",
        description="Execute a CLI command",
        parameters=types.Schema(
            type="OBJECT",
            properties={
                "command": types.Schema(type="STRING"),
                "safety_tier": types.Schema(type="INTEGER"),
                "explanation": types.Schema(type="STRING"),
            },
            required=["command", "safety_tier", "explanation"],
        ),
    ),
])

response = client.models.generate_content(
    model="gemini-2.5-flash",
    contents=[image_part, prompt],
    config=types.GenerateContentConfig(tools=[tools]),
)

# Response will contain function_call objects instead of raw text
for part in response.candidates[0].content.parts:
    if part.function_call:
        name = part.function_call.name
        args = part.function_call.args
```

This eliminates JSON parsing entirely and is more reliable.

---

## 📁 Files You Own

```
odus/reasoning/
├── __init__.py
├── prompts.py      ← System prompt + tool schemas
├── vision.py       ← Gemini Vision API client
├── tools.py        ← Runtime tool implementations
└── agent.py        ← Agentic loop (observe → think → act)
```

## 🔗 Your Interfaces

**You consume (other devs produce):**
- `CaptureResult` from DEV 1's `capture.py` → PNG bytes for compression
- `SafetyVerdict` from DEV 1's `safety.py` → double-checks your tier classification
- `ExecutionResult` from DEV 1's `executor.py` → command output for multi-turn

**You produce (other devs consume):**
- `AnalysisResult` → consumed by DEV 3's UI to display explanation + commands
- Event bus events: `ANALYSIS_STARTED`, `ANALYSIS_DONE`, `ANALYSIS_STREAMING`, `CONFIRM_REQUIRED`

## 🧪 Running Your Tests

```bash
# Unit tests (no API key needed — uses mocks)
.venv/bin/pytest tests/test_vision.py -v

# Live API test (needs GEMINI_API_KEY in .env)
python -c "
import asyncio
from dotenv import load_dotenv
load_dotenv()
from odus.reasoning.vision import VisionAnalyzer

async def test():
    a = VisionAnalyzer()
    # Create a simple test image
    from PIL import Image
    import io
    img = Image.new('RGB', (800, 600), color=(0, 0, 0))
    buf = io.BytesIO()
    img.save(buf, format='JPEG')
    result = await a.analyze(buf.getvalue(), 'This is a test')
    print(f'Summary: {result.summary}')
    print(f'Confidence: {result.confidence}')

asyncio.run(test())
"
```

## ⚡ Key Gemini API Reference

```python
from google import genai
from google.genai import types

client = genai.Client(api_key="...")

# Basic vision call
response = client.models.generate_content(
    model="gemini-2.5-flash",
    contents=[
        types.Part.from_bytes(data=jpeg_bytes, mime_type="image/jpeg"),
        "Analyze this screenshot",
    ],
)
print(response.text)

# Streaming
for chunk in client.models.generate_content_stream(model=..., contents=...):
    print(chunk.text, end="")

# Limits: 7 MB per inline image, 20 MB total request, 3000 images max
```
