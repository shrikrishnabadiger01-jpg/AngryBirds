from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class PolicyConfig(BaseModel):
    allow_read_doc: bool = True
    allow_send_email: bool = False
    allowed_documents: List[str] = Field(default_factory=list)
    allowed_recipients: List[str] = Field(default_factory=lambda: ["manager@example.com"])
    max_emails: Optional[int] = 1
    required_subject: Optional[str] = None


class RunTaskRequest(BaseModel):
    task: str
    document_id: str
    allow_email: bool = False
    recipient: Optional[str] = "manager@example.com"


class ApprovalDecisionRequest(BaseModel):
    token: str
    approved: bool


class ComparisonRequest(BaseModel):
    task: str
    document_id: str
    allow_email: bool = False


class ScriptedTestRunRequest(BaseModel):
    policy_doc: Optional[str] = "project_report"
    allowed_recipient: Optional[str] = "manager@example.com"
