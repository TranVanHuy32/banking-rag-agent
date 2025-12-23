I will restore fullscreen mode and add two window control buttons (Minimize, Close) to the top bar.

**Planned Changes:**

1. Fullscreen Behavior (Cross‑platform)
- File: `run_kiosk.py`
- Actions:
  - Set `app.attributes('-fullscreen', True)` on launch.
  - Keep `Escape` to exit fullscreen for debugging.

2. Window Control Methods
- File: `frontend/main_window.py`
- Actions:
  - Add helper methods to the `KioskApp` class:
    - `go_fullscreen()` → `attributes('-fullscreen', True)`.
    - `exit_fullscreen()` → `attributes('-fullscreen', False)`.
    - `minimize_app()` → temporarily exit fullscreen, call `iconify()`, and bind `FocusIn` to re‑enter fullscreen (`go_fullscreen`) when restored.
    - `close_app()` → `destroy()` (clean exit).

3. Header Buttons (Welcome + Chat)
- Files: `frontend/screens/welcome.py`, `frontend/screens/chat.py`
- Actions:
  - In the header area, add two buttons aligned to the right:
    - Minimize button → calls `controller.minimize_app`.
    - Close button → calls `controller.close_app`.
  - Keep the existing "Kết thúc phiên" button.

4. Optional: Platform Edge Cases
- Windows: `iconify()` works normally.
- Raspberry Pi (Linux): if WM blocks iconify while fullscreen, exit_fullscreen first, then iconify; re‑enter fullscreen on focus restore.

**Outcome:**
- App runs in fullscreen.
- UI provides in‑app Minimize and Close controls at the top of the main window, functioning reliably on Raspberry Pi 5 (1024x600).