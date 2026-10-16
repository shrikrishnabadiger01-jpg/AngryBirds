# AI Agent Security — Round 2 consolidated update
GENESIS 2.0 · Team Angry Birds

This is a Python/Streamlit prototype that puts a deterministic permission gate
between an LLM's proposed tools and execution. Gemini reads synthetic documents
and may propose simulated emails. User permissions are fixed before external
content is read. Document instructions cannot grant permissions. No real email
is sent. There is no trained/custom LLM and no PostgreSQL requirement.

## Install on your existing Windows project
Stop Streamlit with Ctrl+C. Extract this ZIP to a folder outside prompt-security.
Run install_update.py from that extracted folder with --target set to the existing
project. It verifies packaged files, backs up replaced files into backups/, and
preserves .env, logs, and .venv. It replaces the bundled document fixtures (any
custom edits to those fixtures are retained in the backup).

From the existing project:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe eval\run_suite.py --dry-run
.\.venv\Scripts\python.exe -m streamlit run app.py
```

The dependency versions are the versions tested during packaging. Python 3.11+
is required. Existing .env remains valid. Optional model/timeout/retry settings
are listed in .env.example. Environment variables take precedence over .env.
Never commit a key. Choose a model actually available to your account.

## What changed
- 12 versioned synthetic scenarios: 3 benign tasks and 9 attack cases. Gate ON
  and OFF run with the same prompt/policy; only backend enforcement changes.
- Batch evidence viewer, mode/batch filtering, error counts, CSV and evidence ZIP.
- Human task-correctness reviews with a per-case rubric. Reviews are bound to
  the saved evidence hash. Heuristic hints are not presented as a pass score.
- Exact email approval, denial, expiry, and recheck retained. The required
  subject is now an explicit UI policy field, with one email per run.
- Source IDs, content hashes, and server-owned classification recorded. The UI
  requires a successful source read before emailing. If any restricted source
  is read, the entire run is prevented from sending email. This conservative
  rule can block harmless emails too. It is not semantic taint tracking.
- A SQLite ledger persists simulated emails atomically. The same run ID and
  payload cannot be committed twice, including after reopening the workspace.
  Concurrent calls respect the run's email limit. A new run is a new grant.
- Progress messages, model name, installed SDK version, per-request latency,
  usage metadata when available, and transient provider errors recorded.
- Two model-request attempts by default; retry only 429/500/502/503/504. SDK
  retries are disabled to avoid nested retry loops. Tools are never retried by
  the request retry code. Max 8 model steps, 30s request timeout by default.
  A cumulative 180s request-time guard stops before starting another request;
  a request already in progress can exceed that cumulative budget by its timeout.
- Agent output is displayed as plain text so injected Markdown cannot embed
  remote images. Audit events carry IDs/timestamps and source references.
- A Workspace protocol documents the adapter contract for organizer tools.

## Run evaluations without wasting API quota
Dry run and unit tests make no model requests.
Start with one paired scenario, in another PowerShell terminal:

```powershell
.\.venv\Scripts\python.exe eval\run_suite.py --scenario recipient_redirect --mode both --repeats 1
```

Run the whole suite when ready (24 agent runs, each can make multiple requests):

```powershell
.\.venv\Scripts\python.exe eval\run_suite.py --mode both --repeats 1
```

For repeated measurements use --repeats 3 (72 agent runs). A filtered retry is a
new batch; it does not overwrite or erase earlier errors. Refresh the dashboard's
Evaluations tab to view saved results. Open one run, compare answer/outbox with
its rubric, and save a pass/fail review with a reason. API failures are incomplete,
not successful security defenses. Attack counts exclude old logs without labels.

## Reliable presentation sequence
1. Show permissions and a clean summary.
2. Use an injected document; explain that heuristics are operator warnings.
3. Request an email, inspect the exact proposal, Approve; show one simulated email.
4. Repeat and Deny; show an empty outbox and a useful summary.
5. Open Scripted Gate Tests from the sidebar. This uses explicit scripted calls,
   no Gemini request; show forbidden read/recipient blocked with gate ON.
6. Show saved live batch evidence separately. Report only observed results.

If both live modes ignore an attack, say so. Do not label it as a gate block.
The scripted gate checks demonstrate enforcement, not a live attack success rate.
Retain API errors and review usefulness as well as unauthorized actions.

## External integrations and scope limits
**Organizer sandbox:** interface remains unspecified. workspace/protocol.py is
an adapter contract, not a tested integration with their sandbox. A concrete
adapter needs their tool signatures, auth, and semantics. All execution must
continue through execute(), with a policy recheck at the boundary.

**Minimoth:** the provided organizer PDF describes OTP login only if the dashboard
has login. This prototype does not have login. Gemini remains the LLM. The PDF
contains no send/verify endpoint schemas, so no unverified HTTP integration has
been added. To add login, obtain the official request/verification API contract
and response examples, keep the API key server-side, rate-limit attempts, verify
OTP server-side, and establish an authenticated session before exposing tasks.
Do not represent a local demo password or mocked OTP as Minimoth integration.

**Durability:** SQLite contains the synthetic outbox, not an actual delivery
service. Pending approval tokens/generators live in the Streamlit session and
are not resumed after a server restart. A lost session requires a new run; no
pending email is automatically sent. Production mail needs the provider's own
idempotency/reconciliation contract, identity, and durable approval orchestration.

**Security boundary:** allowlists, schemas, scope, recipient, subject, count,
source-read and conservative egress checks are enforced. Exact fixture marker
checks do not detect every transformed leak. Authorized documents may still
corrupt answer content; the deterministic gate cannot prove semantic truth.
Classification is trusted server-owned metadata, not document text. Logs are
local evidence, not a tamper-proof centralized audit service. This is a local,
single-operator prototype, not a production multitenant platform.

## Verification performed for this package
- 20 unit/integration tests passed with real SDK types and mocked model calls.
- Streamlit AppTest exercised approve, deny, batch viewing and saving a review.
- Full 12-scenario dry run validated fixtures, no API calls.
- Provider traffic and organizer/Minimoth integrations were not tested here.
- Tests use temporary data or mocked responses; no fabricated test outcomes
  are shipped as live evaluation results.

Previously observed live evidence: one approved email and one denied email were
verified in user-supplied JSON. Earlier live injections were frequently ignored
by Gemini in both modes. Those observations are separate from this package's tests.
