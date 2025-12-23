I will revert the chat bubble sizing to a stable, fixed width optimized for Raspberry Pi 1024x600 and prevent overflow.

**Planned Changes:**

1. Fixed Wrap Width
- File: `frontend/screens/chat.py`
- Actions:
  - Replace dynamic wraplength with a fixed constant tuned for 1024x600 (e.g., `CHAT_WRAP_MAX = 460`).
  - Update `_bubble_wrap_length()` to return `min(CHAT_WRAP_MAX, chat_card width - margins)` but clamp to `<= CHAT_WRAP_MAX` to avoid over-expansion.
  - Use this for both AI and user bubble labels at creation time.

2. Reflow on Resize
- File: `frontend/screens/chat.py`
- Actions:
  - In `_reflow_layout()`, update all `message_labels` to the clamped wraplength so existing bubbles resize safely without exceeding the maximum.

3. Margins and Stability
- File: `frontend/screens/chat.py`
- Actions:
  - Ensure bubble containers keep `fill="x"` only on the container, not the label; labels rely on wraplength so bubbles don’t stretch horizontally.
  - Maintain side padding so bubbles don’t hug the right border.

Outcome: Chat bubbles return to original-width behavior suitable for 1024x600, stop overflowing, and remain stable during resize/keyboard toggling.