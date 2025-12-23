The user's issue is: "The avatar's actions still respond before the text appears; I want it to remain in the thinking state until the text appears before taking action."

**Analysis of the current behavior:**
1.  **Thinking State**: `on_send` triggers `set_avatar_state("thinking")`.
2.  **Generating**: `_thread_ask_ai` runs. It streams text from the API. As text arrives, it calls `_update_stream`.
3.  **Avatar Update**: Currently, `_process_tts_queue` sets `set_avatar_state("answering")` immediately when it starts processing an item.
4.  **Buffering**: In the previous step, I moved `self.tts_queue.put(text)` to `_finalize_response` (after all text is generated).
    *   This means the avatar stays in "thinking" state *while* the text is streaming onto the screen (which takes time).
    *   Once the text is fully generated and displayed, `_finalize_response` is called.
    *   `_finalize_response` puts the full text into `tts_queue`.
    *   `_process_tts_queue` picks it up and sets `set_avatar_state("answering")`.

**The Discrepancy**:
The user says "respond before the text appears".
If I interpret "text appears" as "streaming starts", then the current behavior (waiting for full text) is actually *delaying* the animation too much (until text is *fully* appeared).
However, the user says "remain in thinking state until the text appears". This implies:
*   Start Thinking.
*   Text starts appearing (Streaming).
*   Avatar should *still* be Thinking? Or should it start Answering as soon as text appears?
*   "before taking action" -> "Action" likely means "Speaking/Animating".

**Re-reading the user's prompt**: "actions still respond **before** the text appears".
This suggests the avatar might be switching to "answering" *too early*.
But my previous change deferred it to the *end* of generation.
Maybe the user is referring to the *initial* response behavior before my previous fix took effect (if they haven't reloaded), OR there is another path triggering "answering".

Let's look at `_thread_ask_ai`:
```python
    def _thread_ask_ai(self, question):
        # ...
        self.after(0, lambda: setattr(self, "ai_bubble_label", self.add_chat_bubble("ai", "...", True)))
        
        # --- Start TTS Worker ---
        # ...
        threading.Thread(target=self._process_tts_queue, daemon=True).start()
```
The `_process_tts_queue` starts immediately.
```python
    def _process_tts_queue(self):
        self.after(0, lambda: self.set_avatar_state("answering", play_once=False))
        # ... wait for queue ...
```
**FOUND THE BUG!**
In `_process_tts_queue`, the very first line is:
`self.after(0, lambda: self.set_avatar_state("answering", play_once=False))`

This executes **immediately** when the thread starts, which is right at the beginning of `_thread_ask_ai`, long before any text has appeared (or even before the queue has items).
This explains why it responds "too early". It switches to "answering" as soon as the request is sent!

**Fix**:
Move `self.set_avatar_state("answering", ...)` **inside** the loop, specifically *after* we successfully get an item from the queue.

**Correct Logic**:
1.  Worker starts. State is still "Thinking" (set in `on_send`).
2.  Worker waits `self.tts_queue.get()`.
3.  Text generation finishes -> `tts_queue.put(text)`.
4.  Worker gets text.
5.  **NOW** switch to "answering".
6.  Speak.
7.  Switch to finish animation.

**Plan**:
1.  Modify `_process_tts_queue` in `frontend/screens/chat.py`.
2.  Remove the initial `set_avatar_state("answering")` call at the top of the function.
3.  Place `set_avatar_state("answering")` inside the `try` block, immediately after `text = self.tts_queue.get(...)` and checking `if text:`.

This will ensure the avatar remains in "Thinking" state (set by `on_send`) throughout the entire generation process, and only switches to "Answering" when it actually starts speaking the received text.

**Wait**, if the text is long, the user sees text streaming for 10 seconds while the avatar is "Thinking". Then text finishes, and Avatar starts "Answering" and speaking. This seems to match "remain in thinking state until the text appears before taking action".
Actually, if they want it to start answering *as soon as text starts appearing*, that would be different. But "remain in thinking... until text appears" usually implies waiting for the content.
Given the previous instruction was "read entire text smoothly" (which forces waiting for full text), the behavior of waiting until the end to animate/speak is consistent.

I will proceed with moving the state change inside the queue processing loop.