I will fix the "hide keyboard" functionality to be universally robust by binding the click event to the main root window rather than specific elements.

**Planned Changes:**

1.  **Universal Click Binding:**
    *   **File:** `frontend/screens/chat.py`
    *   **Action:**
        *   Bind `<Button-1>` (left click/tap) to the **root application window** (`self.winfo_toplevel()`) instead of individual frames like `chat_card` or `chat_frame`.
        *   In the event handler, check which widget was clicked. If the clicked widget is **NOT** part of the virtual keyboard (`self.vkbd_frame`) and **NOT** the input entry (`self.entry`), then hide the keyboard.
        *   This ensures that *any* tap outside the keyboard/input area (including on text bubbles, empty space, headers, etc.) will trigger the hide action, regardless of the application state (reading, searching, idle).

This "global listener" approach is the standard way to implement "click outside to dismiss" behavior in GUI frameworks and will solve the issue reliably.