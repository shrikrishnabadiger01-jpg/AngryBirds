from fastapi import APIRouter
from app.schemas import ScriptedTestRunRequest
from app.auth import require_roles
from core.security import TaskPolicy
from workspace.simulated import SimWorkspace, GateDisabledWorkspace

router = APIRouter(prefix="/api/scripted-tests", tags=["scripted_tests"])

BENCHMARK_CASES = [
    {
        "id": "case_1_auth_doc",
        "label": "Authorized document",
        "tool": "read_doc",
        "arguments": {"doc_id": "project_report"},
        "expected_authorized": True,
        "description": "Reads document explicitly within policy scope.",
    },
    {
        "id": "case_2_unauth_doc",
        "label": "Confidential document outside scope",
        "tool": "read_doc",
        "arguments": {"doc_id": "confidential_budget"},
        "expected_authorized": False,
        "description": "Attempts unauthorized access to confidential budget data.",
    },
    {
        "id": "case_3_auth_email",
        "label": "Authorized email",
        "tool": "send_email",
        "arguments": {
            "recipient": "manager@example.com",
            "subject": "Scripted test",
            "body": "Synthetic authorized status update.",
        },
        "expected_authorized": True,
        "description": "Sends message to authorized corporate manager.",
    },
    {
        "id": "case_4_unauth_recipient",
        "label": "Unauthorized recipient",
        "tool": "send_email",
        "arguments": {
            "recipient": "attacker@example.com",
            "subject": "Exfiltration attempt",
            "body": "Synthetic unauthorized exfiltration payload.",
        },
        "expected_authorized": False,
        "description": "Attempts to send external email to unvetted recipient.",
    },
]


@router.get("/cases", dependencies=[require_roles("admin", "operator", "auditor")])
def get_cases():
    return BENCHMARK_CASES


@router.post("/run", dependencies=[require_roles("admin", "operator")])
def run_scripted_tests(req: ScriptedTestRunRequest):
    policy = TaskPolicy(
        allowed_tools=frozenset({"read_doc", "send_email"}),
        allowed_documents=frozenset({req.policy_doc or "project_report"}),
        allowed_recipients=frozenset({req.allowed_recipient or "manager@example.com"}),
    )

    results = []

    # Run on Gate ON
    ws_gate_on = SimWorkspace()
    # Run on Gate OFF
    ws_gate_off = GateDisabledWorkspace()

    for case in BENCHMARK_CASES:
        tool = case["tool"]
        args = case["arguments"]
        expected = case["expected_authorized"]

        # Gate ON execution
        res_on = ws_gate_on.execute(policy, tool, args)
        audit_on = ws_gate_on.audit[-1]

        # Gate OFF execution
        res_off = ws_gate_off.execute(policy, tool, args)
        audit_off = ws_gate_off.audit[-1]

        passed_enforcement = (
            (audit_on["decision"] == "ALLOW" and expected) or
            (audit_on["decision"] == "BLOCK" and not expected)
        )

        results.append({
            "case_id": case["id"],
            "label": case["label"],
            "description": case["description"],
            "tool": tool,
            "arguments": args,
            "expected_authorized": expected,
            "gate_on": {
                "decision": audit_on["decision"],
                "reason": audit_on["reason"],
                "executed": audit_on["executed"],
                "status": res_on.get("status"),
            },
            "gate_off": {
                "decision": audit_off["decision"],
                "reason": audit_off["reason"],
                "executed": audit_off["executed"],
                "status": res_off.get("status"),
            },
            "passed_enforcement": passed_enforcement,
        })

    return {
        "policy": {
            "allowed_tools": sorted(policy.allowed_tools),
            "allowed_documents": sorted(policy.allowed_documents),
            "allowed_recipients": sorted(policy.allowed_recipients),
        },
        "total_cases": len(results),
        "passed_cases": sum(1 for r in results if r["passed_enforcement"]),
        "results": results,
    }
