from core.security import TaskPolicy, check_action
from workspace.simulated import SimWorkspace

class GateDisabledWorkspace(SimWorkspace):
    """Evaluation only: permissions disabled; tool validation retained."""

    def execute(self, policy, tool, arguments):
        permitted, reason, _ = self.preview(policy, tool, arguments)

        evaluation_policy = TaskPolicy(
            max_emails=None,
            block_restricted_egress=False,
            allowed_tools=frozenset({"read_doc", "read_email", "send_email"}),
            allowed_documents=frozenset(self._documents),
            allowed_recipients=frozenset(
                [arguments["recipient"]]
                if isinstance(arguments, dict) and isinstance(arguments.get("recipient"), str)
                else []
            ),
        )

        result = super().execute(evaluation_policy, tool, arguments)
        event = self.audit[-1]
        event["gate_enabled"] = False
        event["original_policy_allowed"] = permitted
        event["original_policy_reason"] = reason

        if event["decision"] == "ALLOW":
            event["decision"] = "BYPASS"
            event["reason"] = "Permission enforcement disabled for evaluation"

        return result

