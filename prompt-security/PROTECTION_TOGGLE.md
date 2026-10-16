# Protection toggle

Defaults ON. ON uses the permission-enforcing workspace and exact email approvals.
OFF uses the simulated evaluation workspace, bypassing task permissions and human
email approvals. Tool schema validation and duplicate-send checks remain active.
Both modes keep the same model instructions; OFF does not force an injection success.
The sandbox is present in both modes. The toggle changes the security enforcement.

Changing modes cancels pending approvals. Existing results keep their recorded mode
and are marked stale until a new run. Email bodies are visible in the simulated outbox.
No real email capability is added. Heuristic highlights remain visible in both modes.

Verified: 34 unit tests, multi-source summary/approval UI, identical mocked malicious
calls blocked ON and executed OFF, pending approval cancelled on mode switch.
No live Gemini attack success is claimed.
