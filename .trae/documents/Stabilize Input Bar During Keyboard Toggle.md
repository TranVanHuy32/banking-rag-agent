I will make the chat input bar and buttons immune to layout shifts when the keyboard shows/hides.

**Issues Observed:**
- Mixed geometry managers historically caused jitter and disappearing widgets.
- Input bar (entry + mic + send) can be squeezed when keyboard reserves space.

**Planned Fixes (no side effects yet):**
1. Grid Layout Constraints
- File: `frontend/screens/chat.py`
- Actions:
  - Ensure `right_panel` rows are: chat (`row=1`, weight=1), input (`row=2`, weight=0), keyboard slot (`row=3`, weight=0).
  - Set `input_container.grid_propagate(False)` and give it a fixed minimum height (e.g., 70) so it never collapses.
  - In `input_bg`, configure columns with widths:
    - `col 0` (entry): `weight=1`.
    - `col 1` and `col 2` (mic, send): `minsize=48` each to prevent disappearance.

2. Keyboard Slot Discipline
- File: `frontend/screens/chat.py`
- Actions:
  - Use only `grid()` for the keyboard inside `keyboard_slot`.
  - On show: set `keyboard_slot` height to a constant (e.g., 220), `vkbd_frame.grid(row=0, column=0, sticky='ew')`.
  - On hide: `vkbd_frame.grid_remove()` and `keyboard_slot.configure(height=0)`.
  - Call `update_idletasks()` after show/hide to flush geometry updates.

3. Resilience on Resize
- File: `frontend/screens/chat.py`
- Actions:
  - In the existing window resize handler, reassert `input_container` min height and `input_bg` column minsizes.
  - Keep bubble wraplength clamped (already implemented) to avoid chat area squeezing the input bar.

**Outcome:**
- Input entry and mic/send buttons remain visible and sized correctly during keyboard toggle and window resize on Raspberry Pi 5 (1024x600).