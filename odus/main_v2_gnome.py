import asyncio
import signal
import io
import logging
import re
from dbus_next.aio import MessageBus
from dbus_next.service import ServiceInterface, method
from PIL import Image
from dbus_client import OdusDBusClient
from odus.reasoning.vision import VisionAnalyzer, AnalysisResult

# Configure logging for real-time visibility in journalctl
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [OdusBrain] - %(levelname)s - %(message)s'
)

def on_hotkey_triggered(event):
    """Callback for the HotkeyTriggered D-Bus signal."""
    logging.info("HotkeyTriggered signal received from GNOME extension.")
    if event and hasattr(event, 'set'):
        event.set()


class OdusControl(ServiceInterface):
    def __init__(self, trigger_event: asyncio.Event):
        super().__init__('org.gnome.Odus.Control')
        self._trigger_event = trigger_event

    @method()
    def TriggerCapture(self):
        logging.info('Manual capture requested from GNOME extension button.')
        self._trigger_event.set()

    @method()
    def SubmitQuery(self, query: 's') -> 'b':
        query = query.strip()
        if not query:
            return False

        logging.info('Follow-up query received from modal: %s', query)
        self._pending_query = query
        self._trigger_event.set()
        return True

    def consume_query(self) -> str:
        query = getattr(self, '_pending_query', '')
        self._pending_query = ''
        return query

async def process_image_bytes(image_bytes: bytes) -> bytes:
    """
    Converts raw image bytes from D-Bus/memfd into a Vision-compatible JPEG buffer.
    Ensures zero-copy until PIL processing.
    """
    # Use BytesIO to avoid disk I/O
    with io.BytesIO(image_bytes) as input_buffer:
        with Image.open(input_buffer) as img:
            # Convert to RGB if necessary (e.g., from RGBA PNG)
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")
            
            # Save to JPEG in memory
            output_buffer = io.BytesIO()
            img.save(output_buffer, format="JPEG", quality=85)
            return output_buffer.getvalue()

def extract_retry_delay_seconds(error_message: str) -> float | None:
    match = re.search(r'retry in ([0-9.]+)s', error_message, re.IGNORECASE)
    if not match:
        return None

    try:
        return float(match.group(1))
    except ValueError:
        return None

async def run_vision_model(analyzer: VisionAnalyzer, image_bytes: bytes, user_query: str = '') -> tuple[str, float | None, AnalysisResult | None]:
    """Actual AI model inference using Gemini Vision via VisionAnalyzer."""
    try:
        if not image_bytes:
            return "", None, None

        # 1. Prepare image (PNG from GNOME -> JPEG for API)
        jpeg_bytes = await process_image_bytes(image_bytes)
        
        # 2. Analyze with RAG/Vision pipeline
        logging.info("Sending screenshot to Gemini Vision for analysis...")
        user_context = "The user is stuck and needs help with a terminal error or system state shown in the screenshot."
        if user_query:
            user_context += f"\n\n## User Follow-up\n{user_query}"

        result = await analyzer.analyze(jpeg_bytes, user_context=user_context)

        retry_after = extract_retry_delay_seconds(result.raw_response)
        if retry_after:
            return "", retry_after, result

        if result.summary:
            logging.info("Gemini summary: %s", result.summary)
        if result.explanation_for_user:
            logging.info("Gemini explanation: %s", result.explanation_for_user)
        if result.follow_up_hint:
            logging.info("Gemini follow-up: %s", result.follow_up_hint)
        
        # 3. Extract the best command from the plan or suggested_commands
        command = ""
        if result.plan:
            # Prefer the first step of a multi-step plan
            step = result.plan[0]
            if step.get("action_type") == "cli":
                command = step.get("params", {}).get("command", "")
        
        if not command and result.suggested_commands:
            command = result.suggested_commands[0].command
             
        if command:
            logging.info(f"Gemini Vision generated command: {command}")
        else:
            logging.info("Gemini returned guidance without a CLI command.")
        return command, None, result
    except Exception as e:
        logging.error(f"Vision inference failed: {e}")
        return "", extract_retry_delay_seconds(str(e)), None

async def main_loop(client: OdusDBusClient, analyzer: VisionAnalyzer, trigger_event: asyncio.Event, control_service: OdusControl):
    """The core execution loop for the Odus Agent."""
    logging.info("Starting Odus execution loop with VisionAnalyzer...")
    
    while True:
        try:
            manual_capture = False
            # Wait for either the timer or the hotkey event
            try:
                await asyncio.wait_for(trigger_event.wait(), timeout=15)
                manual_capture = True
                logging.info("Capture triggered by hotkey")
                trigger_event.clear()
            except asyncio.TimeoutError:
                logging.debug("Periodic capture trigger")

            # 1. Perception: Capture the screen
            logging.info("Initiating screen capture via D-Bus...")
            image_bytes = await client.capture_screen()
            
            if not image_bytes:
                logging.warning("Capture failed. Retrying in 5s...")
                await asyncio.sleep(5)
                continue

            logging.info(f"Successfully mapped {len(image_bytes)} bytes from memfd screenshot.")

            # 2. Reasoning: Run the real vision model
            user_query = control_service.consume_query()
            command, retry_after, analysis = await run_vision_model(analyzer, image_bytes, user_query=user_query)

            if retry_after:
                logging.warning(f"Vision API rate-limited. Backing off for {retry_after:.1f}s...")

                if manual_capture:
                    fallback = analysis or AnalysisResult(
                        summary="Gemini rate limit reached",
                        explanation_for_user=f"Gemini asked to retry in {retry_after:.1f}s.",
                        follow_up_hint="Try again after the retry window or update the Gemini API key.",
                        confidence=0.0,
                        raw_response="",
                    )

                    await client.set_mascot_state("warning")
                    await client.request_approval(
                        fallback.summary,
                        fallback.explanation_for_user,
                        fallback.follow_up_hint,
                        "",
                        kind="rate_limit",
                        retry_after=retry_after,
                    )

                await asyncio.sleep(retry_after)
                continue
            
            if manual_capture and analysis:
                # 3. Safety: Ask for user approval
                await client.set_mascot_state("warning")
                logging.info("Requesting user advice/approval from modal")
                modal_kind = "error" if analysis.summary == "Analysis failed" else ("info" if not command else "advice")
                approved = await client.request_approval(
                    analysis.summary,
                    analysis.explanation_for_user,
                    analysis.follow_up_hint,
                    command,
                    kind=modal_kind,
                )
                
                if command and approved:
                    logging.info("User interaction result: ALLOWED")
                    await client.set_mascot_state("thinking")
                    
                    # 4. Action: Inject characters one by one
                    logging.info(f"Injecting keystrokes for command: {command}")
                    for char in command:
                        keysym = char
                        # Basic keysym mapping
                        if char == " ": keysym = "space"
                        elif char == "'": keysym = "apostrophe"
                        elif char == '"': keysym = "quotedbl"
                        elif char == "!": keysym = "exclam"
                        elif char == "&": keysym = "ampersand"
                        elif char == "/": keysym = "slash"
                        elif char == "\\": keysym = "backslash"
                        elif char == "-": keysym = "minus"
                        elif char == "_": keysym = "underscore"
                        elif char == ".": keysym = "period"
                        
                        await client.inject_keystroke(keysym)
                        await asyncio.sleep(0.01)
                    
                    await client.inject_keystroke("Return")
                    await client.set_mascot_state("success")
                elif command:
                    logging.info("User interaction result: DENIED")
                    await client.set_mascot_state("idle")
                else:
                    await client.set_mascot_state("idle")

            # Wait before next iteration (longer for real API usage)

        except asyncio.CancelledError:
            break
        except Exception as e:
            logging.error(f"Loop error: {e}")
            await asyncio.sleep(5)

async def shutdown(loop, client, sig=None):
    """Cleanup and close connections."""
    if sig:
        logging.info(f"Received exit signal {sig.name}...")
    
    logging.info("Closing D-Bus connection...")
    if client.bus:
        client.bus.disconnect()
        
    tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
    [task.cancel() for task in tasks]
    
    logging.info(f"Cancelling {len(tasks)} outstanding tasks")
    await asyncio.gather(*tasks, return_exceptions=True)
    loop.stop()

async def main():
    client = OdusDBusClient()
    try:
        analyzer = VisionAnalyzer()
    except ValueError as e:
        logging.critical(f"Critical Error: {e}")
        return

    loop = asyncio.get_running_loop()

    signals = (signal.SIGHUP, signal.SIGTERM, signal.SIGINT)
    for s in signals:
        loop.add_signal_handler(
            s, lambda s=s: asyncio.create_task(shutdown(loop, client, sig=s))
        )

    try:
        await client.connect()
        
        if client.authenticated:
            logging.info("D-Bus connection successfully established and authenticated.")
            
            # Set up reactive hotkey trigger
            trigger_event = asyncio.Event()
            control_service = OdusControl(trigger_event)
            client.bus.export('/org/gnome/Odus/Control', control_service)
            await client.bus.request_name('org.gnome.Odus.Control')
            logging.info('Control D-Bus service exported: org.gnome.Odus.Control')
            try:
                client.on_hotkey_triggered(lambda: on_hotkey_triggered(trigger_event))
                logging.info("HotkeyTriggered signal listener registered")
            except Exception as e:
                logging.warning(f"HotkeyTriggered signal registration failed: {e}")

            await main_loop(client, analyzer, trigger_event, control_service)
        else:

            logging.error("Could not authenticate with GNOME extension. Exiting.")
    except Exception as e:
        logging.error(f"Startup failed: {e}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
