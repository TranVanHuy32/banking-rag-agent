I have analyzed the user's request and the current code in `frontend/screens/chat.py`.

**Problem 1: Stop button not working correctly**
The user mentions that pressing the stop button (next to the chat bubble) doesn't stop the text reading correctly.
*   Currently, `_on_speaker_click` calls `self.audio_client.stop()`.
*   In `src/services/audio_client.py`, `stop()` only stops `pygame.mixer.music`.
*   However, because we implemented a **streaming TTS queue** (`self.tts_queue`), stopping the current playback doesn't clear the queue. The worker thread (`_process_tts_queue`) will immediately pick up the next sentence and start playing it.
*   **Fix:** When the stop button is clicked, we must also clear `self.tts_queue` and set a flag to interrupt the worker loop if it's running.

**Problem 2: Animation Adjustment**
The user wants the character to:
1.  Only move (animate) when it starts reading.
2.  When reading finishes, display images from `speak_024.png` to the end (which presumably is a "closing mouth" or "return to neutral" sequence).

*   **Current Logic:**
    *   `_process_tts_queue` sets `self.set_avatar_state("answering", play_once=False)` at the start.
    *   It sets `self.set_avatar_state("normal")` at the end.
    *   `set_avatar_state` logic in `_animate_loop` loops between frames 8 and 23 (`LOOP_START=7`, `LOOP_END=22`).
*   **Fix:**
    *   We need to keep the "answering" loop while speaking.
    *   When stopping (either naturally or forced), we should play a specific "finish" animation sequence (frame 24 to end) before going back to "normal".
    *   I will modify `set_avatar_state` or add a new state `finishing` or just modify the `normal` transition to play the exit sequence.
    *   Actually, `set_avatar_state("normal")` just shows the static normal image.
    *   I'll add a `stop_speaking_animation()` helper that plays the frames from 24 to end, then sets state to normal.

**Plan:**

1.  **Modify `frontend/screens/chat.py`**:
    *   **Fix Stop Button**:
        *   In `_on_speaker_click`:
            *   Clear `self.tts_queue`.
            *   Set `self.stop_requested = True` (or a specific `self.stop_tts_playback` flag to be safer, but `stop_requested` is already used in `_process_tts_queue`).
            *   Actually, `stop_requested` stops the generation stream too. If the user just wants to stop *reading* an old message, we shouldn't stop generation. But if it's the current message, maybe they want to stop both?
            *   The prompt says "stop button next to the chat bubble", which implies the replay/stop button.
            *   I'll add a `self.cancel_tts_playback()` method that:
                *   Clears `tts_queue`.
                *   Calls `audio_client.stop()`.
                *   Resets avatar.
    *   **Fix Animation**:
        *   Modify `_process_tts_queue`:
            *   Start animation "answering" when loop starts.
            *   When loop ends (queue empty), call a new method `_play_finish_animation()` instead of setting "normal" directly.
        *   Implement `_play_finish_animation()`:
            *   Load frames starting from `speak_024.png` to the end.
            *   Play them once.
            *   Then set state to "normal".
    *   **Refine `_animate_loop`**:
        *   The current loop logic (8->23) is fine for "speaking".
        *   We just need to handle the transition out.

**Detailed Animation Logic:**
The `answering` assets folder has `speak_001.png` to `speak_033.png`.
*   Current Loop: 8 (index 7) -> 23 (index 22).
*   Desired Finish: 24 (index 23) -> End (33/index 32).

**Updated `_process_tts_queue`:**
```python
    def _process_tts_queue(self):
        self.after(0, lambda: self.set_avatar_state("answering", play_once=False))
        
        while not self.stop_requested:
            # ... processing ...
        
        # When done, play finish sequence
        self.after(0, self._play_finish_animation)
```

**Updated `_play_finish_animation`:**
```python
    def _play_finish_animation(self):
        # Manually play frames 24->end
        frames = assets.avatars.get("answering_anim")
        if not frames:
            self.set_avatar_state("normal")
            return
            
        # Slice frames from index 23 (speak_024) to end
        finish_frames = frames[23:] 
        self._animate_oneshot(finish_frames)
```

**Implementation Steps:**
1.  Define `_play_finish_animation` and `_animate_oneshot`.
2.  Update `_process_tts_queue` to use `_play_finish_animation`.
3.  Update `_on_speaker_click` to properly stop the queue.

Let's refine `_on_speaker_click`. Currently, it checks `if self.current_playing_btn == btn`.
If we are streaming, `current_playing_btn` might not be set yet (it's set in `_on_speaker_click` usually).
Wait, the streaming TTS doesn't set `current_playing_btn`. It just plays.
The "Speaker" button is created in `_finalize_response` or `add_chat_bubble`.
If the user clicks "Stop" on a button that *is* playing (streaming or replay), we need to stop.

If streaming is active, there is no "button" associated with it yet (until finalize).
But the prompt implies the user is clicking the button *next to the chat bubble*.
If the user clicks the button on a *finished* message that is being replayed:
*   `_on_speaker_click` is called.
*   `self.audio_client.stop()` is called.
*   If it was a replay (blocking speak in thread), `stop()` works.
*   If it was a streaming response that just finished and added the button?
    *   The streaming queue might still be processing.
    *   We need to clear the queue.

I will add `self.clear_tts_queue()` and call it in `_on_speaker_click` and `on_mic` (to stop reading if user interrupts).