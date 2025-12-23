I have analyzed the user's request. There are two main issues to address:

1. **TTS "Choppy" Reading**:

   * **Current Behavior**: The `_thread_ask_ai` loop splits text by sentence delimiters (`.`, `?`, `!`, `\n`) and queues each sentence immediately. The TTS worker reads them one by one. If sentences are short or the TTS engine (Google/gTTS) has initialization latency, this creates pauses between sentences.

   * **Goal**: "Read the entire text smoothly."

   * **Solution**: Instead of streaming sentence-by-sentence to the TTS queue, we should accumulate larger chunks or, ideally, wait for the full response if smoothness is priority over latency.

   * *However*, the user previously asked for "simultaneous text display and reading". To keep that *and* be smooth, we need a better buffering strategy.

   * *Alternative Interpretation*: The user might mean that the current splitting logic (`re.split`) is breaking sentences incorrectly (e.g., at "Mr." or "Dr.") or that the playback has gaps.

   * **Revised Strategy**: Since the user explicitly said "it is malfunctioning because it is splitting the text into smaller parts", I will **revert the sentence-level streaming for TTS** and switch to **Reading the Full Text** at the end (or at least larger paragraphs).

   * *Wait*, if I revert to reading at the end, I lose the "simultaneous" feature.

   * *Better Approach*: I will modify the buffer to wait for **Paragraphs** (`\n`) or accumulate a minimum character count (e.g., 50-100 chars) *and* a sentence ending before queuing. This reduces the number of small audio files.

   * *Actually*, the simplest fix for "read entire text smoothly" given the constraints is to **buffer the entire response** for TTS and play it once complete, *or* if the user insists on streaming, only split on newlines.

   * Let's try to find a middle ground: **Accumulate larger chunks**. I'll increase the buffer logic to only flush to TTS when a **newline** is found or the buffer is very large. This makes the speech more continuous for paragraphs.

2. **Character Animation Timing**:

   * **Issue 1: "Responds too early"**: The character starts "answering" animation as soon as the TTS worker picks up the first chunk, which might be before the text is fully visible or just too fast.

   * **Issue 2: "Ending part... inconsistent"**: The `_play_finish_animation` might be triggering at the wrong time or conflicting with the loop.

   * **Fix**:

     * **Sync Animation with Audio**: The `speak_blocking` function is where the audio actually plays. We should trigger `set_avatar_state("answering")` *inside* the `speak_blocking` logic (or right before calling it) and ensure it stays there until the audio finishes.

     * Currently `_process_tts_queue` sets "answering" at the start.

     * If we switch to reading larger chunks (or full text), this syncing becomes easier.

     * **Refined Plan**:

       * Modify `_thread_ask_ai`: Don't queue small sentences. Accumulate `full_text` for TTS.

       * Only queue the **entire text** (or large paragraphs) to `tts_queue` when `_finalize_response` is called or when a strong delimiter (like double newline) is found.

       * This will delay the start of audio slightly (until generation is done or a paragraph is done), but ensures smoothness.

       * Given the user's complaint "splitting into smaller parts", delaying until the full response (or at least full paragraph) is the safest fix for smoothness.

**Plan:**

1. **Modify** **`frontend/screens/chat.py`**:

   * **Disable Sentence-Level Streaming**: In `_thread_ask_ai`, remove the logic that splits by `.` or `?` and pushes to `tts_queue`. Instead, just accumulate `full`.

   * **Queue Full Text**: In `_finalize_response` (or at the end of `_thread_ask_ai`), push the `full` text to `tts_queue`.

   * **Update Animation Trigger**:

     * The `_process_tts_queue` is already set up to wait for the queue.

     * When `_finalize_response` pushes the full text, the worker picks it up.

     * This ensures the character starts "answering" only when we have the text and start playing.

   * **Fix Animation Glitch**:

     * In `_process_tts_queue`, ensure `set_avatar_state("answering")` is called *before* `speak_blocking`.

     * Ensure `_play_finish_animation` is called *after* `speak_blocking` returns.

     * Check if `speak_blocking` actually blocks. Yes, I implemented it to block.

**Wait**, if I wait for the full text, the "simultaneous" requirement is gone.
But the user says "malfunctioning because it is splitting... read entire text smoothly". This implies the "smoothness" is now higher priority than "simultaneous starting".
I will implement **Full Text Reading** (start reading only after generation completes or we have a very large chunk).
Actually, a compromise: **Read by Paragraph**. Most AI responses are formatted in paragraphs. Reading paragraph by paragraph is smooth enough and still allows some concurrency.

**Decision**: I will modify the streaming logic to split **ONLY by Newline (`\n`)**.
If the AI sends a long block without newlines, it will wait.
This solves the "choppy sentence" issue.

**Steps:**

1. **Modify** **`_thread_ask_ai`**:

   * Change split regex from `r'(?<=[.!?\n])\s+'` to `r'(?<=\n)\s+'` (or just check for `\n`).

   * Actually, let's just buffer until `__END__` or `\n`.

   * *Correction*: The user said "read the entire text smoothly". The safest interpretation is to **wait for the full response**. I will buffer everything and play once at the end.

2. **Fix Character Timing**:

   * The character currently starts "answering" in `_process_tts_queue`.

   * If we wait for full text, the animation will start exactly when audio starts (which is correct).

   * The "too early" might refer to the "Thinking" state switching to "Answering" before text appears? No, usually "answering" is for speaking.

   * I will ensure `set_avatar_state("answering")` is strictly coupled with the TTS playback.

3. **Fix "Ending part inconsistent"**:

   * Ensure `_play_finish_animation` is robust.

   * Currently it plays 24->end.

   * I'll make sure no other state change interrupts it unless it's a user action.

**Let's proceed with buffering the FULL text for TTS to guarantee smoothness.**

**Revised Plan:**

1. **`frontend/screens/chat.py`**:

   * In `_thread_ask_ai`: Remove the sentence splitting/queuing logic inside the loop. Just accumulate `full`.

   * In `_finalize_response`: Add `self.tts_queue.put(text)`.

   * This effectively reverts the "streaming TTS" but keeps the "Worker Thread" architecture (which is good for non-blocking UI).

   * This ensures the text is read as one continuous block.

2. **Animation**:

   * The `_process_tts_queue` will now receive one large chunk.

   * It sets "answering".

   * Calls `speak_blocking` (plays full audio).

   * Calls `_play_finish_animation`.

   * This aligns perfectly.

3. **"Responds too early"**:

   * Since we now wait for full text, the character won't animate until the text is fully generated and passed to TTS.

   * Wait, the user might want the character to animate *while text is streaming*? No, "only answer when there is a text response appearing".

   * If I wait for full text, the text *has* appeared (streamed).

   * This seems correct.

I will also make sure the "Thinking" state remains while text is streaming (generating).

**One detail**: If the response is long, generating takes time. The user sees text appearing. They might want audio to start *sooner* but *smoothly*.
But "read entire text smoothly" strongly suggests passing the whole text to the TTS engine at once so it can handle intonation across sentences.
I will stick to **Full Text TTS**.

**Wait,** **`AudioClient`** **uses** **`requests`** **to Google TTS (or similar).**
Most TTS engines have a char limit (e.g. 1000-5000 chars).
If the response is huge, `speak_blocking` might fail or cut off.
My `AudioClient.speak_blocking` has `text[:1000]`.
I should bump this limit or split by paragraph if it's too long.
I'll check `src/services/audio_client.py` and increase the limit if needed, or handle splitting *inside* `speak_blocking` if the text is huge.
For now, 1000 chars is \~200 words, usually enough for a chat response. I'll increase it to 2000 just in case.

**Files to change:**

1. `frontend/screens/chat.py` (Main logic).
2. `src/services/audio_client.py` (Increase limit).

**Specifics for** **`frontend/screens/chat.py`:**

* Remove `re.split` in `_thread_ask_ai`.

* Move `self.tts_queue.put(full)` to `_finalize_response`.

* Verify `_process_tts_queue` handles the single large task correctly.

