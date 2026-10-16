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
    task: str = Field(min_length=1, max_length=8000)
    document_id: str = Field(min_length=1, max_length=200)
    allow_email: bool = False
    recipient: Optional[str] = Field(default="manager@example.com", max_length=254)
    allowed_documents: Optional[List[str]] = Field(default=None, max_length=100)
    allowed_recipients: Optional[List[str]] = Field(default=None, max_length=50)
    max_emails: int = Field(default=1, ge=0, le=10)
    required_subject: Optional[str] = Field(default=None, max_length=200)
    email_ids: Optional[List[str]] = Field(default=None, max_length=20)


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
