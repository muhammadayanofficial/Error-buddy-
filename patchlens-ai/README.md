# PatchLens AI - Code Review & Debugging Studio

Paste code, optionally add an error or traceback, and get a structured review from Gemini: findings with severity,
a debugging analysis, an improved version next to your original, suggested tests, saved history (SQLite) and Markdown export.
Submitted code is never executed. Generated tests are never claimed to have passed.

## Setup on Windows with VS Code
1. Install Python 3.10+ from python.org (tick "Add python.exe to PATH") and VS Code with the Python extension.
2. Open this folder in VS Code (File > Open Folder) and open a terminal (Ctrl+`).
3. Create and activate a virtual environment:
   ```
   python -m venv .venv
   .venv\Scripts\activate
   ```
   If PowerShell blocks activation, run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` once.
4. Install dependencies: `pip install -r requirements.txt`
5. Copy `.env.example` to `.env` (`copy .env.example .env`) and set `GEMINI_API_KEY`. Get a key at https://aistudio.google.com/apikey
6. Start the app: `python app.py`, then open http://127.0.0.1:5000
7. Run the tests: `python -m unittest discover tests`

Without an API key the app still starts; the top bar shows "API key missing" and AI reviews are refused with a clear message.
"Check syntax locally" is a non-AI Python syntax check only.

## Structure
- `app.py` routes and validation, `config.py` settings, `database.py` SQLite, `ai_service.py` Gemini call and output validation, `export.py` Markdown
- `templates/index.html`, `static/css/style.css`, `static/js/app.js`, `tests/test_app.py`

Keyboard: Ctrl+Enter in the editor runs a review; Tab inserts four spaces.
