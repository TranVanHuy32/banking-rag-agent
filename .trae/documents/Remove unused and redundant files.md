I have identified several files that are unused, redundant, or leftovers from previous implementations. I plan to remove them to clean up the project structure.

**Files to be removed:**

1.  **`app.py`**: This is the legacy Flask backend that was used for the WebSocket streaming implementation. The project has moved to using `api/main.py` (FastAPI) as the backend entry point.
2.  **`kiosk_ui with keyboard.txt`**: This is a text file backup of an older frontend implementation. The active frontend code is now structured in the `frontend/` directory.
3.  **`test_slm.py`**: This is a standalone test script for the LLM. Removing it will declutter the root directory.
4.  **Root PNG Icons** (`mic_icon.png`, `send_icon.png`, `speaker_icon.png`, `stop_icon.png`): These are duplicate image files located in the root directory. The application correctly loads these assets from the `assets/` directory (referenced by `frontend/assets.py`), making these copies unnecessary.

**Verification:**
- I have verified that `run.py` and `run_kiosk.py` are the correct entry points for the backend and frontend, respectively.
- I have confirmed that `frontend/assets.py` loads images from the `assets/` folder, not the root.
- I have confirmed that `api/main.py` is the active backend application.

I will proceed with deleting these files.