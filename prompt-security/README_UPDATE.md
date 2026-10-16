# Genesis dashboard update

## Install on your existing project
1. Stop Streamlit with Ctrl+C.
2. Back up the files being replaced. Keep your existing .env, .venv and logs.
3. Extract this ZIP into the prompt-security project folder, replacing matching files.
4. Run: .\.venv\Scripts\python.exe -m streamlit run app.py

No additional packages are needed beyond your working installation.

## Changes
- Three tabs: Run agent, Security audit, Evaluation.
- Saved live-comparison table with mode filter and CSV download; no API usage for viewing logs.
- Input-change warnings now include permissions in the live comparison panel.
- Existing scripted tests remain a separate sidebar page.
- Core security, fixtures and Gemini agent behavior preserved.

## Demo sequence
1. Choose an injected report and show the fixed permissions.
2. Run a legitimate summary (or authorized simulated email).
3. Open Security audit: explain that suspicious text is data, and only permitted calls execute.
4. Open Evaluation: show saved results, including gate OFF. The observed live model resisted these attacks in both modes.
5. Open Scripted Gate Tests: submit the same authorized/prohibited calls with enforcement on and off. Explicitly identify this as scripted, not model-generated.

## Evidence and limitations
The previously reviewed six paired comparisons contained 12 completed runs and zero unauthorized actions in either mode. They do not demonstrate an improvement from enforcement. The scripted tests check the enforcement mechanism independently.
The saved table reads your own logs; no results are fabricated or bundled. Completion is not an automatic utility score. Marker detection is limited to the test fixture's marker.
This prototype supports document reads and simulated emails only. It has no organizer sandbox adapter, approval flow, production authentication or broad security guarantee.

## Verification
Run local smoke tests without API calls:
.\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_dashboard_update.py"

The Gemini SDK and model setting are unchanged. Remote validation does not exercise your API key or a live Gemini response.
