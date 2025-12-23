The user wants to make two visual changes to the UI:

1.  **Send Button**:
    *   Change the default color to **Green** (currently `PRIMARY` which is likely Blue).
    *   When the AI is "running" (generating a response), the button should turn into a **Red Stop Button** (icon change + color change).
    *   Clicking it while running should stop the generation/reading.

2.  **Recording Indicator**:
    *   Improve the "Recording..." display. Currently, it's just a small text label `self.status_label.configure(text="Đang nghe...")`.
    *   The user wants it "more clearly". I will create a dedicated overlay or a more prominent visual indicator (e.g., a large "Listening" badge or changing the Mic button color/icon significantly).

**Plan:**

1.  **Modify `frontend/screens/chat.py`**:
    *   **Send Button Logic**:
        *   Change `self.btn_send` default color to a Green hex code (e.g., `#22c55e` or `#16a34a`).
        *   In `set_loading(True)` (which is called when sending/asking):
            *   Change `btn_send` icon to "Stop" (need to check if we have a stop icon asset, or reuse `assets.icons["stop"]`).
            *   Change `btn_send` color to Red (`DANGER`).
            *   Update command to a new `on_stop` handler.
            *   **Crucially**: `set_loading` currently disables the buttons (`state="disabled"`). I need to keep `btn_send` **enabled** but change its function.
        *   In `set_loading(False)` (when done):
            *   Revert `btn_send` to Green and "Send" icon.
            *   Revert command to `on_send`.
        *   Implement `on_stop()`:
            *   Set `self.stop_requested = True`.
            *   Call `_clear_tts_queue()`.
            *   Call `audio_client.stop()`.

    *   **Recording Display**:
        *   Instead of just text, I'll add a **"Recording Overlay"** or a larger status panel.
        *   Simple but effective approach:
            *   Change the `input_bg` border color to Red.
            *   Change the Mic button to a large Red "Stop Recording" button.
            *   Or show a large "Listening..." label in the chat area (like a temporary bubble).
            *   Let's go with a **"Listening Overlay"** in the center of the chat area or a prominent status bar.
            *   Actually, the user said "instead of just a small line of text".
            *   I will replace the `status_label` text update with a more visible state change:
                *   Change `btn_mic` color to Red and icon to "Stop".
                *   Change `input_bg` border color to Red.
                *   Update `entry` placeholder to "Đang nghe... (Nhấn mic để dừng)".

**Refining Send Button Colors:**
*   Green: `#10B981` (Emerald 500) or `#22C55E` (Green 500).
*   Red: `DANGER` (defined in config).

**Refining Recording UI:**
*   When `on_mic` starts:
    *   `self.btn_mic.configure(fg_color=DANGER, image=assets.icons["stop"])` (assuming we have stop icon).
    *   `self.entry.configure(placeholder_text="🔊 Đang nghe...", state="disabled")`.
*   When `on_mic` stops (or done):
    *   Revert `btn_mic` to `ACCENT` and Mic icon.
    *   Revert `entry`.

**Checking Assets:**
*   `assets.icons["stop"]` exists (used in speaker button).
*   `assets.icons["send"]` exists.

**Step-by-Step Implementation:**

1.  **Update `set_loading`**:
    *   Rename/Refactor to `set_generating_state(is_generating)`.
    *   If `is_generating`:
        *   `btn_send` -> Stop Icon, Red Color, Command = `on_stop`.
        *   `btn_mic` -> Disabled.
        *   `entry` -> Disabled (or read-only).
    *   If `not is_generating`:
        *   `btn_send` -> Send Icon, Green Color, Command = `on_send`.
        *   `btn_mic` -> Normal.
        *   `entry` -> Normal.

2.  **Update `on_mic`**:
    *   Toggle state.
    *   If starting:
        *   `btn_mic` -> Stop Icon, Red.
        *   `status_label` -> Large font "🔴 ĐANG NGHE..."
    *   If stopping:
        *   Revert.

3.  **Implement `on_stop`**:
    *   Trigger stop flags.

**Wait, `set_loading` is currently used for both Mic and Send.**
I need to distinguish "Listening State" vs "Generating State".

*   **Generating (AI Thinking/Speaking)**:
    *   Send Button -> Stop Button.
    *   Mic Button -> Disabled.
*   **Listening (Mic Active)**:
    *   Send Button -> Disabled.
    *   Mic Button -> Stop Recording Button (Red).

I'll refactor the state management in `ChatScreen`.