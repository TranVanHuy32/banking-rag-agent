I will fix the voice communication by implementing a full-duplex WebSocket solution using `websockets` and `pyaudio`.

### 1. Backend: Refactor Deepgram Service
**File:** `src/services/stt_deepgram.py`
- Remove `socketio` dependency.
- Modify `DeepgramService` to accept an `async_callback` in its constructor.
- When Deepgram returns a transcript, await this callback instead of emitting to socketio.
- Ensure the service can be instantiated per WebSocket connection.

### 2. Backend: Implement WebSocket Endpoint
**File:** `api/endpoints/audio_ws.py`
- Update `audio_websocket` to:
  - Initialize `DeepgramService` for the current connection.
  - Define a callback `send_to_client` that sends JSON to the WebSocket.
  - Start the Deepgram service.
  - In the receive loop, pass incoming audio bytes to the Deepgram service.
  - Handle `WebSocketDisconnect` to stop the service.

### 3. Frontend: Rewrite Stream Client
**File:** `src/services/stream_client.py`
- Switch from `socketio` to `websockets` (AsyncIO) + `pyaudio`.
- Implement `start_recording` to launch a background thread running an AsyncIO loop.
- **Async Logic:**
  - Connect to `ws://localhost:8000/api/v1/ws/audio`.
  - **Sender Task:** continuously read from PyAudio (using `run_in_executor` to avoid blocking) and send bytes to WebSocket.
  - **Receiver Task:** continuously listen for messages from WebSocket and trigger `on_transcript_callback` or `on_response_callback`.

### 4. Verification
- Since I cannot run the UI, I will verify the code structure and ensure all dependencies (`websockets`, `pyaudio`, `deepgram-sdk`) are correctly used.
- I will verify the endpoint path matches the router configuration.
