I will correct the avatar frame sizing issue and implement the "tap to hide keyboard" feature.

**Planned Changes:**

1.  **Fix Avatar Frame Size:**
    *   **File:** `frontend/screens/chat.py`
    *   **Action:**
        *   Change `self.ava_frame.grid_propagate(False)` to `self.ava_frame.pack_propagate(False)` to ensure the frame strictly enforces its 340px width (since the avatar label uses `pack`).
        *   Implement a mechanism to resize avatar images and animations to fit the new smaller frame (300x330px) to prevent cropping or overflow. This involves caching resized images to maintain performance.

2.  **Hide Keyboard on Tap:**
    *   **File:** `frontend/screens/chat.py`
    *   **Action:**
        *   Bind the `<Button-1>` (click) event to the chat display area (`self.chat_card` and `self.chat_frame`) to trigger `self.hide_keyboard()`.
        *   This creates the behavior: Tap Chat Area → Hide Keyboard; Tap Input Bar → Show Keyboard.

This approach resolves the layout bug by using the correct propagation method and adds the requested interaction for managing the keyboard.