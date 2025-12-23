Here’s why the input box and mic/send buttons disappear, and how we will fix them.

**Root Cause (1024x600 constraints):**
- The right panel has three stacked rows: header (~45px), chat (flex), input bar (~70px), plus the keyboard (~220px) when visible.
- On a 600px-tall screen, header + input + keyboard can exceed the remaining height for the chat row. Grid tries to fit everything and the chat or input rows get squeezed/clipped, which makes the entry and buttons appear to “disappear”.
- Two aggravating factors:
  - We reserve keyboard height inside the same grid, so showing/hiding the keyboard forces a full reflow and temporary 0-size measurements.
  - The input container disables grid propagation, so when total height is insufficient the system clips the bottom rows rather than reflowing the sizes.

**Plan to Fix (safe and stable):**
1. Overlay Keyboard (No Grid Reflow)
- Show the keyboard using `place()` anchored to the bottom of `right_panel` (overlay), not inside its grid.
- Size it to a smaller fixed height (e.g., 180px) and width matching the panel.
- On hide, `place_forget()`; this avoids grid height changes entirely.

2. Pin Input Bar Height
- Keep `input_container` with a fixed min height (70px) and keep it in row 2 with weight 0; it should never collapse.
- Ensure `input_bg` column minsizes for mic/send stay >48px, so buttons don’t shrink away.

3. Optimize Vertical Spacing for Pi
- Reduce header height to ~40px and bubble paddings slightly to gain vertical room.
- Keep chat row flexible (weight 1), so only chat shrinks when keyboard overlays, not the input bar.

4. Debounce & Flush Layout
- After show/hide keyboard, call `update_idletasks()` and avoid multiple geometry manager changes in one tick.

**Outcome:**
- Keyboard no longer forces grid reflow; input/mic/send remain visible and stable at 1024x600 on Raspberry Pi.
- Chat area remains scrollable and adjusts gracefully under the overlay keyboard.

If you approve, I will implement these changes immediately and verify on the Pi layout.