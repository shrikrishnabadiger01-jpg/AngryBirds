# Judge dashboard update

## Install
Stop Streamlit with Ctrl+C. Extract this package outside the existing project.
Run install_update.py --target PATH_TO_PROMPT_SECURITY using the project's Python.
Install requirements-upload.txt with that same Python, then restart app.py.
The installer backs up replaced files and preserves .env, logs and .venv.

## What changed
- Source and live action trace side by side, compact visual process map.
- Clean white/slate/teal interface, amber source highlights, explicit decision badges.
- Full extracted document reader; multiple file selection and accumulated uploads.
- Upload PDF, DOCX, ZIP, TXT, Markdown, CSV, JSON, LOG and EML.
- Exact email approval card and readable answer panel.
- Run history, evidence and evaluations moved out of the main demo surface.
- Inbox and scripted-test screens share the visual theme.

## Present the prototype honestly
1. Open the injected report. Explain the highlighted instructions are untrusted content.
2. Set the legitimate task and source scope, then run the protected task.
3. Show actual tool calls, decisions and response. If the model ignores the attack,
   say so: zero blocked calls does not demonstrate a gate intervention.
4. Open scripted gate tests to demonstrate deterministic permission checks.
5. For email: choose the email action AND request email in the task. Approve or deny
   the exact draft. Delivery goes to a simulated outbox, not a real mailbox.

## Limits
Gemini key remains in your existing .env. No model/API calls were made during this
build's local verification. 34 automated unit tests and mocked UI summary/approval
flows passed. Browser screenshot verification was unavailable in the build environment.
Scanned PDFs require OCR elsewhere; the reader shows extracted text, not original
page layout. Highlighting is heuristic, not a complete attack detector. Uploaded
files stay in session; logs can retain task/output/tool argument text.
