I will revise the window initialization to use maximized mode (not fullscreen) and ensure the UI stays sized for 1024x600.

**Planned Changes:**

1. Window Behavior
- File: `run_kiosk.py`
- Actions:
  - Remove `app.attributes('-fullscreen', True)`.
  - Set maximized state by platform:
    - Windows: `app.state('zoomed')`.
    - Linux/Raspberry Pi: try `app.attributes('-zoomed', True)` in a `try/except`; if unsupported, set geometry to the actual screen size: `app.geometry(f"{app.winfo_screenwidth()}x{app.winfo_screenheight()}+0+0")` and keep `fullscreen=False`.
  - Keep `Escape` binding to restore normal window for debugging.

2. Root Window Sizing
- File: `frontend/main_window.py`
- Actions:
  - Ensure `self.geometry(WINDOW_SIZE)` remains `"1024x600"`.
  - Add `self.minsize(1024, 600)` and `self.resizable(True, True)` so the window can maximize but never shrink below 1024x600.

3. Verification
- Launch app on Windows: confirm maximized with title bar visible.
- Launch on Raspberry Pi: window fills screen but not fullscreen (taskbar visible). If `zoomed` unsupported, geometry fallback uses detected screen size.
- Confirm layout still fits: avatar column at 340px, chat fills remaining space, keyboard toggles correctly.

If approved, I will implement these changes and test across platforms.