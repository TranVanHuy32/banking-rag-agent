I have researched the current codebase and designed a plan to upgrade the voice communication to a **Streaming WebSocket + PyAudio** solution as requested.

### **Current Status**
-   **Client (`src/services/audio_client.py`)**: Uses `speech_recognition` (blocking) for listening and `requests` (HTTP) for TTS.
-   **Server (`api/endpoints/audio_ws.py`)**: Has a placeholder WebSocket endpoint (`/ws/audio`) that is mounted but empty.
-   **Dependencies**: `PyAudio` is present. `websockets` needs to be added for the client.

### **Plan to Implement Streaming Voice**

I will implement a bidirectional streaming architecture:

1.  **Backend (`api/endpoints/audio_ws.py`)**:
    *   Implement the WebSocket logic to receive raw audio bytes (PCM 16kHz).
    *   **VAD & Buffering**: Since Google Free STT doesn't support true streaming, I will implement a "Silence Detection" buffer on the server. When silence is detected (or a max buffer size is reached), the server will convert the buffered bytes to a format `speech_recognition` accepts and transcribe it.
    *   **Response**: Send the transcription back to the client immediately via WebSocket JSON events (`{"event": "transcription", "text": "..."}`).

2.  **Client (`src/services/audio_client.py`)**:
    *   **Rewrite `listen()`**: Instead of using `sr.Microphone()`, it will use `pyaudio` to open a raw stream.
    *   **Streaming Loop**: It will read chunks from PyAudio and send them over the WebSocket connection in real-time.
    *   **Receive Loop**: It will listen for JSON messages from the server to get the transcription text.

3.  **UI Integration (`frontend/screens/chat.py`)**:
    *   Update `on_mic` to use the new `audio_client.listen_stream()` method.
    *   This will allow the UI to show "Listening..." and update in real-time (if we achieve partial results) or at least be faster than the blocking HTTP approach.

### **Why this approach?**
This fulfills the "Streaming WebSocket + PyAudio" requirement. Even though the underlying STT engine (Google Free) isn't fully streaming, moving the audio transport to WebSocket reduces the latency of connection establishment and allows for smoother "VAD-on-Server" logic in the future.

**Do you want me to proceed with these changes?**