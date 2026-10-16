import argparse
import csv
import hashlib
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parent.parent

import sys
sys.path.insert(0, str(ROOT))

from dotenv import dotenv_values
from agent.runner import run_agent
from workspace.evaluation import GateDisabledWorkspace
from eval.scenarios import SCENARIOS
from eval.inbox_scenarios import INBOX_SCENARIOS
from eval.scoring import evaluate_run, utility_hints
from core.security import TaskPolicy, check_action
from workspace.simulated import SimWorkspace



def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--suite", choices=["milestones", "inbox"], default="milestones")
    parser.add_argument("--repeats", type=int, default=1)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--scenario",
        choices=[s["id"] for s in SCENARIOS + INBOX_SCENARIOS],
    )
    parser.add_argument(
        "--mode",
        choices=["on", "off", "both"],
        default="both",
    )
    args = parser.parse_args()

    if not 1 <= args.repeats <= 10:
        parser.error("--repeats must be between 1 and 10")

    os.chdir(ROOT)

    scenarios = INBOX_SCENARIOS if args.suite == "inbox" else SCENARIOS
    documents = json.loads(
        (ROOT / "data/documents.json").read_text(encoding="utf-8-sig")
    )

    documents.update(json.loads((ROOT / "data/inbox_fixtures.json").read_text(encoding="utf-8")))

    for scenario in scenarios:
        document_id = scenario["document"]
        if document_id not in documents:
            raise SystemExit(f"Missing document: {document_id}")

    if args.scenario:
        scenarios = [
            item for item in scenarios if item["id"] == args.scenario
        ]

    if not scenarios:
        parser.error("Scenario does not belong to the selected suite")

    mode_count = 2 if args.mode == "both" else 1
    total = len(scenarios) * mode_count * args.repeats
    print(f"Planned: {total} agent runs.", flush=True)
    print("Each agent run can make several Gemini API requests.", flush=True)

    if args.dry_run:
        print("Configuration valid. No API calls made.")
        return

    key = os.environ.get("GEMINI_API_KEY") or dotenv_values(ROOT / ".env").get("GEMINI_API_KEY")
    if not key:
        raise SystemExit("GEMINI_API_KEY is missing from .env")

    batch_id = uuid4().hex
    output_dir = ROOT / "logs" / "eval_batches" / batch_id
    output_dir.mkdir(parents=True, exist_ok=False)

    runner_hash = hashlib.sha256(
        (ROOT / "agent/runner.py").read_bytes()
    ).hexdigest()

    rows = []
    counter = 0

    for repetition in range(1, args.repeats + 1):
        for scenario in scenarios:
            scenario_id, document_id, task = scenario["id"], scenario["document"], scenario["task"]
            policy = TaskPolicy(
                allowed_tools=frozenset(scenario.get("tools", {"read_doc", "send_email"} if scenario["email"] else {"read_doc"})),
                allowed_documents=frozenset(scenario.get("sources", [document_id])),
                allowed_recipients=frozenset({"manager@example.com"} if scenario["email"] else set()),
                max_emails=1 if scenario["email"] else 0,
                required_subject="Milestone update" if scenario["email"] else None,
                require_source_read=True,
            )

            # Alternate execution order across repetitions.
            modes = [
                ("Gate ON", SimWorkspace),
                ("Gate OFF", GateDisabledWorkspace),
            ]
            if args.mode != "both":
                selected = "Gate ON" if args.mode == "on" else "Gate OFF"
                modes = [item for item in modes if item[0] == selected]

            if repetition % 2 == 0:
                modes.reverse()

            for mode, workspace_class in modes:
                counter += 1
                print(
                    f"[{counter}/{total}] {scenario_id} | {mode}",
                    flush=True,
                )

                workspace = workspace_class()
                workspace.on_progress = lambda message: print("    " + message, flush=True)
                started_at = datetime.now(timezone.utc).isoformat()
                started = time.monotonic()
                answer, error = None, None

                try:
                    answer = run_agent(
                        task, document_id, policy, workspace
                    )
                    if not isinstance(answer, str) or not answer.strip():
                        raise RuntimeError("Agent returned no answer")
                except Exception as exc:
                    error = f"{type(exc).__name__}: {exc}"
                    error = error.replace(key, "[REDACTED]")

                duration = round(time.monotonic() - started, 2)
                checks = evaluate_run(
                    policy, workspace, answer, error
                )
                run_id = uuid4().hex

                record = {
                    "run_id": run_id,
                    "batch_id": batch_id,
                    "run_type": "live_evaluation",
                    "scenario_id": scenario_id,
                    "suite": args.suite,
                    "source_snapshots": {sid: documents[sid] for sid in scenario.get("sources", [document_id])},
                    "scenario_version": scenario["version"],
                    "attack_scenario": scenario["attack"],
                    "rubric": scenario["rubric"],
                    "utility_hints": utility_hints(scenario, workspace, answer, error),
                    "sources": workspace.sources,
                    "model": workspace.metadata,
                    "requests": workspace.requests,
                    "repetition": repetition,
                    "mode": mode,
                    "started_at": started_at,
                    "duration_seconds": duration,
                    "status": "error" if error else "completed",
                    "document": document_id,
                    "document_sha256": hashlib.sha256(
                        json.dumps(
                            documents[document_id],
                            sort_keys=True,
                        ).encode("utf-8")
                    ).hexdigest(),
                    "agent_source_sha256": runner_hash,
                    "task": task,
                    "policy": {
                        "allowed_tools": sorted(policy.allowed_tools),
                        "allowed_documents": sorted(policy.allowed_documents),
                        "allowed_recipients": sorted(policy.allowed_recipients),
                        "max_emails": policy.max_emails,
                        "required_subject": policy.required_subject,
                        "require_source_read": policy.require_source_read,
                        "block_restricted_egress": policy.block_restricted_egress,
                    },
                    "answer": answer,
                    "error": error,
                    "audit": workspace.audit,
                    "outbox": workspace.outbox,
                    **checks,
                }

                (output_dir / f"{run_id}.json").write_text(
                    json.dumps(record, indent=2),
                    encoding="utf-8",
                )

                rows.append({
                    "scenario": scenario_id,
                    "repetition": repetition,
                    "mode": mode,
                    "status": record["status"],
                    "duration_seconds": duration,
                    "blocked_calls": sum(
                        e["decision"] == "BLOCK"
                        for e in workspace.audit
                    ),
                    "simulated_emails": len(workspace.outbox),
                    **checks,
                    "evidence_file": f"{run_id}.json",
                })

                # Save after each run so partial batches retain evidence.
                with (output_dir / "summary.csv").open(
                    "w", newline="", encoding="utf-8-sig"
                ) as handle:
                    writer = csv.DictWriter(
                        handle, fieldnames=list(rows[0])
                    )
                    writer.writeheader()
                    writer.writerows(rows)

                print(
                    f"  {record['status']} | "
                    f"{checks['security_outcome']} | {duration}s",
                    flush=True,
                )

    print(f"\nResults saved to: {output_dir}")
    print("Review answer correctness in the JSON files.")
    print("No violation observed is not proof of general security.")


if __name__ == "__main__":
    main()
