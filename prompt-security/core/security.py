from dataclasses import dataclass


@dataclass(frozen=True)
class TaskPolicy:
    allowed_tools: frozenset[str]
    allowed_documents: frozenset[str]
    allowed_recipients: frozenset[str]
    max_emails: int | None = 1
    required_subject: str | None = None
    require_source_read: bool = False
    block_restricted_egress: bool = True

    def __post_init__(self):
        for field in ('allowed_tools', 'allowed_documents', 'allowed_recipients'):
            value = getattr(self, field)
            if isinstance(value, (str, bytes)) or not all(isinstance(item, str) and item for item in value):
                raise ValueError(field + ' must contain nonempty strings')
            object.__setattr__(self, field, frozenset(value))
        if self.max_emails is not None and (type(self.max_emails) is not int or self.max_emails < 0):
            raise ValueError('max_emails must be a nonnegative integer or None')
        if self.required_subject is not None and (not isinstance(self.required_subject, str) or not self.required_subject.strip() or len(self.required_subject) > 200 or any(c in self.required_subject for c in '\r\n\x00')):
            raise ValueError('required_subject must be valid single-line text')


def check_action(policy, tool, arguments):
    if not isinstance(tool, str):
        return False, "Tool name must be text"

    if tool not in {"read_doc", "read_email", "send_email"}:
        return False, "Unknown tool"

    if tool not in policy.allowed_tools:
        return False, f"Tool not permitted: {tool}"

    if not isinstance(arguments, dict):
        return False, "Arguments must be an object"

    if tool in {"read_doc", "read_email"}:
        field = "email_id" if tool == "read_email" else "doc_id"
        if set(arguments) != {field}:
            return False, "Invalid source-read arguments"

        doc_id = arguments[field]

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
