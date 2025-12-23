I will modify the chat interface to adjust the avatar frame width and implement a toggleable virtual keyboard.

**Planned Changes:**

1.  **Resize Avatar Frame:**
    *   **File:** `frontend/screens/chat.py`
    *   **Action:** In `_build_layout`, change the `width` of `self.ava_frame` from `420` to `340` (approximately 1/3 of the 1024px screen width).

2.  **Implement Toggleable Virtual Keyboard:**
    *   **File:** `frontend/screens/chat.py`
    *   **Action:**
        *   Modify `create_virtual_keyboard` to **not** display the keyboard (`.grid()`) immediately upon creation.
        *   Add a **"Hide" (▼)** button to the keyboard's control row to allow users to close it manually.
        *   Implement a `show_keyboard` method that makes the keyboard visible.
        *   Implement a `hide_keyboard` method that hides it.
        *   Bind the `self.entry` (input box) click event (`<Button-1>`) to trigger `show_keyboard`.

This ensures the avatar takes up less space and the keyboard remains hidden until the user explicitly attempts to type, maximizing screen real estate.