I will improve the TTS text cleaning to aggressively remove special characters throughout the text, not just at the start/end.

**Planned Changes:**

1.  **Enhance `_clean_for_tts`:**
    *   **File:** `frontend/screens/chat.py`
    *   **Action:**
        *   Modify `_clean_for_tts` to use regex (`re.sub`) to remove specific special characters (`*`, `#`, `_`, `` ` ``, `~`, etc.) from the **entire string**, while preserving necessary punctuation for pauses (`,`, `.`, `?`, `!`, `;`, `:`).
        *   This ensures that inline markdown like `**Important**` becomes just `Important` for the TTS engine.

This change guarantees the TTS reads only the meaningful words and proper punctuation, avoiding awkward character pronunciations.