I examined the current UI structure in frontend/screens/chat.py and found the weak points that cause components to collapse when the window expands/contracts on Raspberry Pi.

**Issues Identified**
- Mixing geometry managers across parents is mostly ok, but grid rows in `right_panel` still reflow when height becomes tight, making row 2 (input) or row 3 (keyboard slot) clip.
- `input_bg` does not explicitly disable grid propagation; only `input_container` does. This allows the row to shrink under pressure.
- Button columns for mic/send rely on content size without guaranteed minimums on every reflow.
- Wraplength for existing bubbles isn’t always reapplied after resize; long lines can push horizontal layout.
- Keyboard width/height not reasserted on resize, so it may overlap or squeeze neighbors.

**Design Principles**
- Only the chat row (`row=1`) should flex; input (`row=2`) and keyboard slot (`row=3`) remain fixed-height.
- Keep a single geometry manager per container and avoid re-defining geometry within the same tick.
- Re-apply minsize constraints after any resize or keyboard toggle.

**Concrete Changes (code-level)**
1. Strengthen grid policies
- In `_build_layout`:
  - `self.right_panel.grid_rowconfigure(1, weight=1)`; `self.right_panel.grid_rowconfigure(2, weight=0)`; `self.right_panel.grid_rowconfigure(3, weight=0)` (ensure already set, otherwise add).
  - Add `self.input_bg.grid_propagate(False)` and `self.input_bg.grid_rowconfigure(0, minsize=36)`.
  - Reassert column constraints: `self.input_bg.grid_columnconfigure(0, weight=1)`; `self.input_bg.grid_columnconfigure(1, minsize=48)`; `self.input_bg.grid_columnconfigure(2, minsize=48)`.
  - Ensure `self.keyboard_slot.grid_columnconfigure(0, weight=1)` (already present) and keep it in grid, not overlay.

2. Debounced resize and safe refresh
- In `__init__`, keep the global binding: `self.controller.bind("<Configure>", self._on_window_resize, add="+")`.
- Implement `_apply_layout_policy()` that:
  - Recomputes `wraplength = min(CHAT_WRAP_MAX, self.chat_card.winfo_width() - 80)` and applies to all `self.message_labels`.
  - Reapplies `self.input_container.configure(height=70)` and `self.input_bg` column minsize settings.
  - If `keyboard_visible`, re-grid keyboard with `sticky="ew"` and keep `self.keyboard_slot.configure(height=220)`.
- In `_on_window_resize`, call this method via a small debounce (`after(120)`) to prevent flicker.

3. Keyboard show/hide hooks
- In `show_keyboard` and `hide_keyboard`, after changing grid, call `self.update_idletasks()` and `self._apply_layout_policy()` (via `after(0)`) so constraints are reasserted immediately and do not affect ongoing threads.

4. Bubble wrap behavior
- Unify wraplength calculation through `_bubble_wrap_length()` and ensure it is used both when creating labels and during refresh.

**Non-invasive Adjustments**
- No changes to TTS, networking, or animation logic.
- No changes to row/column positions beyond constraints; only resilience added.

**Verification Plan**
- On Raspberry Pi at 1024x600:
  - Start maximized; toggle keyboard repeatedly, confirm input bar and mic/send never disappear.
  - Resize window smaller/larger (simulate panel changes) and confirm only chat area flexes while input and keyboard remain fixed.
  - Stream a long AI response; confirm bubble wraps and does not overflow horizontally.

If you approve, I will implement these code-level adjustments in chat.py and verify the behavior end-to-end on the layout.