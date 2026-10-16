# Multi-file security workspace

## Start here
Restart Streamlit after installing. The Workspace tab now opens a readable
project report by default. There are three main tabs: Workspace, Run history,
and Evaluations. Inbox Defense and Scripted Gate Tests remain in the sidebar.

1. Upload one or several files, or a ZIP, and click Import selected files.
2. Choose Uploaded files and select which documents the agent may read.
3. Use Open document to inspect each extracted source. Amber highlights show
   suspicious text, with explanations under Why these passages were highlighted.
4. Enter a task, such as "Compare all selected reports and list disagreements,
   delayed work and next actions. Identify the source for each finding."
5. Choose read-only or email mode. In email mode specify the exact recipient and
   subject, and explicitly request the email in the task. Delivery is simulated.
6. Run. Read the answer, proposed actions, block reasons, outbox and evidence.

The source permissions include every selected file, not just the previewed one.
Source IDs depend on filename and file bytes; changing an upload changes its ID.
Runs capture a deep copy of selected uploaded content. Changing selection cannot
silently widen a pending approval. Clearing imports cancels a pending approval.

## Formats and limits
- PDF: text extraction, up to 100 pages; page labels retained. Scans need OCR.
  Blank/image-only pages are marked. Original page layout and images are not shown.
- DOCX: document body and table text. Headers, footers, comments and images are
  not extracted. Macros are not run. Legacy .doc is unsupported: save as .docx.
- TXT, Markdown, CSV, JSON, LOG and EML: readable text. EML is shown as raw email
  text, not decoded MIME attachments. CSV is plain text, not a spreadsheet grid.
- ZIP: supported members read in memory, never unpacked onto disk. No nested ZIPs,
  encrypted entries, unsafe paths or symlinks. Unsupported members are reported.
- 10 MB per file, 30 MB import/archive expansion, 20 documents, 100 ZIP entries,
  100,000 extracted characters per document, 300,000 selected characters per run.
- PDF/DOCX parse in a subprocess with a 20-second timeout. This is bounded local
  parsing, not a hardened OS sandbox for arbitrary hostile files.

## Inspection meaning
Highlights indicate heuristic instruction patterns: claimed system authority,
secrecy, confidential access, recipient changes, fake approvals and hidden HTML.
They can miss attacks and can flag harmless quotations or legitimate routing text.
They are not a vulnerability scanner or a guarantee. The backend gate independently
checks tool calls. Uploaded HTML is escaped; it cannot inject markup into the reader.

## Data and behavior
Raw uploads are held in the current server/browser session and are lost when
that session ends. They are not a persistent document library. Uploaded text is
sent to Gemini when the model invokes a read. Logs persist task, model output,
arguments and source hashes/metadata, and may contain sensitive excerpts. Existing
logs and keys are preserved by the installer. Do not upload material you cannot
send to your chosen model provider. Real email and OTP login are not added here.

## Verify and install
Stop Streamlit. Extract the update outside prompt-security. Run install_update.py
--target against that project. Replaced files are backed up; .env/logs/.venv are
preserved. Install requirements-upload.txt using the project's virtual environment.
Run unittest discovery, then restart Streamlit. No live evaluation rerun is needed
just to install this UI/upload change.

Verified locally: 34 automated tests pass. Streamlit AppTest verifies the default
report reader, two-source task execution and two-source approved email flow, with
model calls mocked. Parser tests cover text, DOCX, PDF, ZIP safety, limits, content
identity, HTML escaping and read-scope enforcement. This does not establish attack
success/block rates against live Gemini.
