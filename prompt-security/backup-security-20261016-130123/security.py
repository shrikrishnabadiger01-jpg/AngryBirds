from dataclasses import dataclass


@dataclass(frozen=True)
class TaskPolicy:
    allowed_tools: frozenset[str]
    allowed_documents: frozenset[str]
    allowed_recipients: frozenset[str]


def check_action(policy, tool, arguments):
    if tool not in policy.allowed_tools:
        return False, f"Tool not permitted: {tool}"

    if tool == "read_doc":
        if set(arguments) != {"doc_id"}:
            return False, "Invalid read_doc arguments"

        doc_id = arguments["doc_id"]
        if not isinstance(doc_id, str):
            return False, "Document ID must be text"

        if doc_id not in policy.allowed_documents:
            return False, f"Document outside task scope: {doc_id}"

    elif tool == "send_email":
        if set(arguments) != {"recipient", "subject", "body"}:
            return False, "Invalid send_email arguments"

        if not all(isinstance(v, str) for v in arguments.values()):
            return False, "Email arguments must be text"

        if arguments["recipient"] not in policy.allowed_recipients:
            return False, "Recipient not authorized"

    else:
        return False, "Unknown tool"

    return True, "Action permitted by task policy"
