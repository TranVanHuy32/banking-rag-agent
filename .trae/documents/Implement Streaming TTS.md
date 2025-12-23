The user wants to revise the TTS (Text-to-Speech) part so that text display and text reading happen simultaneously.

**Current Behavior:**
In `frontend/screens/chat.py`, the application waits for the full text response from the AI (`_finalize_response`) before triggering the audio playback (`_on_speaker_click` -> `self.audio_client.speak`). The text streams in chunk by chunk, but the audio only starts after the entire message is received.

**Problem:**
The user perceives a delay because the audio doesn't start until the text generation is completely finished.

**Proposed Solution:**
To achieve simultaneous text display and reading, we need to stream the text to the TTS engine as well. However, doing true streaming TTS with sentence boundary detection is complex. A simpler and robust approach for this context is to:

1.  **Accumulate text chunks** as they arrive.
2.  **Detect sentence endings** (period, question mark, exclamation mark, newline).
3.  **Send completed sentences** to the TTS engine immediately while the rest of the text is still generating.
4.  **Queue audio playback** so sentences are played in order.

**Plan:**

1.  **Modify `frontend/screens/chat.py`**:
    *   Initialize a `sentence_buffer` and an `audio_queue` in `_thread_ask_ai`.
    *   In `_update_stream` (which runs on the main thread for UI updates), we also need to handle buffering for TTS. However, `_update_stream` is called via `self.after`, which might be too "UI-focused". It's better to handle the logic in the background thread `_thread_ask_ai` before dispatching to the UI.
    *   **Refactor `_thread_ask_ai`**:
        *   Create a local buffer for incoming chunks.
        *   Split the buffer by sentence delimiters (`.`, `?`, `!`, `\n`).
        *   If a complete sentence is found, send it to `AudioClient` immediately.
        *   Keep the incomplete part in the buffer.
    *   **Update `AudioClient` (in `src/services/audio_client.py`)**:
        *   The current `speak` method is blocking (it waits for the API and then plays). We need a non-blocking queue system.
        *   Add a `speak_async` or modify `speak` to handle queuing.
        *   Or, simpler: `ChatScreen` manages the threading. `AudioClient.speak` blocks *playback*, so we can chain them? No, `AudioClient.speak` creates a thread.
        *   We need a mechanism to ensure sentence 2 plays *after* sentence 1 finishes. `pygame.mixer.music.get_busy()` can be used to check status.

**Refined Plan for `frontend/screens/chat.py`**:

1.  **`_thread_ask_ai` modification**:
    *   Initialize `self.tts_queue = []` and `self.is_speaking = False`.
    *   As chunks arrive:
        *   Update UI (existing logic).
        *   Append to `tts_buffer`.
        *   Check for sentence endings.
        *   If a sentence is complete:
            *   Extract sentence.
            *   Call a helper `self.queue_tts(sentence)`.
    *   After the loop finishes:
        *   If `tts_buffer` has remaining text, flush it to `self.queue_tts`.

2.  **`queue_tts(text)` helper**:
    *   Add text to a queue.
    *   If not currently speaking, trigger `process_tts_queue`.

3.  **`process_tts_queue` helper**:
    *   Pop text.
    *   Call `self.audio_client.speak(text, ..., blocking=True)` (We need to make sure `AudioClient` can support blocking playback or callback-based chaining).
    *   Wait for it to finish (or use callback).
    *   Process next item.

**Wait, `AudioClient.speak` currently spawns a thread.**
Let's check `src/services/audio_client.py` again.

```python
    def speak(self, text, ...):
        def _run():
            # ... requests.post ...
            # ... pygame.mixer.music.play() ...
            # ... while pygame.mixer.music.get_busy(): time.sleep(0.1) ...
        threading.Thread(target=_run, daemon=True).start()
```

It runs in a thread and blocks *inside that thread* until playback finishes.
This is actually perfect for a "worker thread" approach.

**Revised Plan:**

1.  **In `frontend/screens/chat.py`**:
    *   Create a `TTSManager` class or add methods to `ChatScreen` to handle the queue.
    *   Start a dedicated thread `_tts_worker` when AI generation starts.
    *   The worker reads from a `Queue`.
    *   In `_thread_ask_ai`:
        *   Accumulate text.
        *   On sentence boundary, put sentence into `Queue`.
    *   In `_tts_worker`:
        *   Get sentence from `Queue`.
        *   Call `self.audio_client.speak_blocking(sentence)`. (Need to add `speak_blocking` to `AudioClient` or modify `speak`).

**Let's modify `src/services/audio_client.py` first:**
*   Add `speak_blocking` method: Same logic as `speak` but without wrapping in `threading.Thread`.

**Then modify `frontend/screens/chat.py`:**
*   Add `import queue`.
*   In `_thread_ask_ai`:
    *   Start `tts_thread`.
    *   Accumulate `tts_buffer`.
    *   Split by regex `r'(?<=[.!?])\s+'`.
    *   Push sentences to `self.tts_queue`.
*   Implement `_tts_loop`:
    *   `while` loop reading from `tts_queue`.
    *   Call `self.audio_client.speak_blocking`.

**Wait, `_finalize_response` currently triggers `_on_speaker_click` which triggers `speak`.**
We need to disable the auto-speak in `_finalize_response` if we are streaming audio.
And `_on_speaker_click` (the Replay button) should probably just replay the full text as before.

**Step-by-step Implementation:**

1.  **Modify `src/services/audio_client.py`**:
    *   Refactor `speak` to extract the core logic into a `_speak_logic` method that can be called synchronously.
    *   `speak` becomes a wrapper that runs `_speak_logic` in a thread.
    *   Add `speak_blocking` which calls `_speak_logic` directly.

2.  **Modify `frontend/screens/chat.py`**:
    *   Add `import queue`.
    *   In `__init__`: `self.tts_queue = queue.Queue()`.
    *   In `_thread_ask_ai`:
        *   Clear `tts_queue`.
        *   Start `threading.Thread(target=self._process_tts_queue, daemon=True).start()`.
        *   Implement sentence buffering logic.
        *   Put sentences into `tts_queue`.
    *   Implement `_process_tts_queue`:
        *   Get text, call `audio_client.speak_blocking`.
    *   Update `_finalize_response`:
        *   Don't auto-play.
        *   Just update the speaker button state to "Stop" (since it's likely still playing).
        *   Or better: The `_process_tts_queue` will handle the "Talking" avatar state.

**Handling Avatar State:**
*   `_process_tts_queue` should set `self.set_avatar_state("answering")` when starting and `normal` when the queue is empty and generation is done.

Let's refine the file edits.

**File 1: `src/services/audio_client.py`**
*   Extract the logic inside `speak`'s `_run` into `speak_blocking`.
*   `speak` simply threads `speak_blocking`.

**File 2: `frontend/screens/chat.py`**
*   Import `queue`.
*   Add `self.tts_queue = queue.Queue()` to `__init__`.
*   Add `self.stop_tts = False`.
*   In `_thread_ask_ai`:
    *   Reset `self.stop_tts = False`.
    *   Start TTS worker.
    *   Buffer logic using `re.split(r'(?<=[.!?])\s+', buffer)`.
*   In `_finalize_response`:
    *   Put `None` (sentinel) into queue to signal end of stream? Or just let the worker die naturally?
    *   Actually, `_finalize_response` shouldn't auto-play anymore.
    *   It should bind the "Replay" button to the full text.

**Verification:**
*   Run the client.
*   Ask a long question.
*   Verify audio starts while text is still appearing.

I'll start by modifying `src/services/audio_client.py` to support blocking calls.