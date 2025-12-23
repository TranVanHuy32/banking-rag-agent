I will fix the environment variable loading issue and the Deepgram client initialization.

### 1. Verification

* The user is reporting that `DEEPGRAM_API_KEY` is missing despite being in `.env`.

* The `src/services/stt_deepgram.py` file does `import os` but does not call `load_dotenv()`. It relies on the caller to load it.

* `app.py` calls `load_dotenv()`, but `api/main.py` (which runs via `uvicorn`) does **not** seem to call `load_dotenv()` explicitly at the top level before importing services that might need env vars at module level (though `stt_deepgram` reads it in `__init__`, so it should be fine if loaded before init).

* **Crucial Fix:** I will add `load_dotenv()` to `src/services/stt_deepgram.py` to ensure it self-configures, or ensure `api/main.py` loads it early. Given the error "Thiếu DEEPGRAM\_API\_KEY", it's safer to load it in the service file itself.

### 2. Fix Deepgram Initialization

* The user previously reported a `TypeError` in `app.py` (Flask version) which I haven't touched yet, but I see `app.py` in the file list. Wait, the user's error log showed `src/services/stt_deepgram.py` (which I edited) and `api/endpoints/audio_ws.py`.

* I previously changed `stt_deepgram.py` to use `DeepgramClient(api_key=...)`.

* I will verify if `app.py` also needs similar fixing if the user is running that.

* **However**, the user's error log clearly points to `D:\banking-rag-agent\src\services\stt_deepgram.py`.

* **Action:** I will add `from dotenv import load_dotenv; load_dotenv()` to `src/services/stt_deepgram.py` to guarantee env vars are loaded.

### 3. Verify Env Loading with Script

* I will create a small script `verify_env.py` to print the API key (masked) to prove it's loadable.

### Plan Steps:

1. Modify `src/services/stt_deepgram.py` to import and call `load_dotenv()` at the top.
2. (Optional) Check if `app.py` (the Flask app) is being used or if we are strictly on FastAPI. The user's trace shows `uvicorn`, so it's FastAPI. I will focus on `stt_deepgram.py`.
3. Create `verify_env.py` to confirm `python-dotenv` is working.

