"""Contract for an organizer adapter; external writes must remain behind the gate.

preview must be side-effect free. execute must recheck policy atomically with
execution. Never give the model a raw transport/client that bypasses execute.
"""
from typing import Protocol
from core.security import TaskPolicy

class Workspace(Protocol):
    audit: list
    outbox: list
    requests: list
    sources: dict
    metadata: dict
    def preview(self, policy: TaskPolicy, tool: str, arguments: dict) -> tuple: ...
    def execute(self, policy: TaskPolicy, tool: str, arguments: dict) -> dict: ...
    def notify(self, message: str) -> None: ...
