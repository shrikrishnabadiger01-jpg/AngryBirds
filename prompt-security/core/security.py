from dataclasses import dataclass


@dataclass(frozen=True)
class TaskPolicy:
    allowed_tools: frozenset[str]
    allowed_documents: frozenset[str]
    allowed_recipients: frozenset[str]
    max_emails: int | None = 1
    required_subject: str | None = None


def check_action(policy, tool, arguments):
    if not isinstance(tool, str):
        return False, "Tool name must be text"

    if tool not in {"read_doc", "send_email"}:
        return False, "Unknown tool"

    if tool not in policy.allowed_tools:
        return False, f"Tool not permitted: {tool}"

    if not isinstance(arguments, dict):
        return False, "Arguments must be an object"

    if tool == "read_doc":
        if set(arguments) != {"doc_id"}:
            return False, "Invalid read_doc arguments"

        doc_id = arguments["doc_id"]

        if not isinstance(doc_id, str) or not doc_id.strip():
            return False, "Document ID must be non-empty text"

        if len(doc_id) > 200:
            return False, "Document ID is too long"

        if doc_id not in policy.allowed_documents:
            return False, f"Document outside task scope: {doc_id}"

    elif tool == "send_email":
        if set(arguments) != {"recipient", "subject", "body"}:
            return False, "Invalid send_email arguments"

        limits = {"recipient": 254, "subject": 200, "body": 20000}

        for field, limit in limits.items():
            value = arguments[field]
            if not isinstance(value, str) or not value.strip():
                return False, f"{field} must be non-empty text"
            if len(value) > limit:
                return False, f"{field} exceeds its length limit"
            if "\x00" in value:
                return False, f"{field} contains an invalid character"

        if any(c in arguments["recipient"] for c in "\r\n"):
            return False, "Recipient must be a single line"

        if any(c in arguments["subject"] for c in "\r\n"):
            return False, "Subject must be a single line"

        if arguments["recipient"] not in policy.allowed_recipients:
            return False, "Recipient not authorized"

        if (
            policy.required_subject is not None
            and arguments["subject"] != policy.required_subject
        ):
            return False, "Subject does not match the task policy"

    return True, "Action permitted by task policy"
