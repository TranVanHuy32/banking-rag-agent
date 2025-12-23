I will optimize the interface layout to fit perfectly within a 1024x600 resolution and ensure full-screen mode is enabled.

**Planned Changes:**

1.  **Enable Full Screen (Global):**
    *   **File:** `run_kiosk.py`
    *   **Action:** Modify the initialization to set `app.attributes('-fullscreen', True)` for all platforms (not just Linux), ensuring the app launches in full screen mode immediately. I will verify the Escape key binding remains for exiting full screen.

2.  **Optimize Layout for 600px Height:**
    *   **File:** `frontend/screens/chat.py`
    *   **Action:** Reduce vertical padding and element sizes to maximize space for the chat area on a short screen (600px).
        *   **Avatar:** Reduce vertical padding (`pady`) from 40 to 10.
        *   **Header:** Reduce bottom padding from 10 to 5.
        *   **Input Box:** Reduce height from 50 to 45.
        *   **Virtual Keyboard:** Reduce key height from 50 to 42 to make the keyboard more compact (~32px saved).
        *   **Chat Area:** This will gain approximately ~50px of additional vertical space, improving usability.

This ensures the interface runs full screen and the layout elements (keyboard, input, avatar) are proportioned correctly for the 1024x600 resolution without requiring scrolling for basic interactions.