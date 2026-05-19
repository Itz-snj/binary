"""
SlothOps Engine — Pydantic Models & Enums
Defines the internal data contract used by every module in the pipeline.
"""

from __future__ import annotations

import enum
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# ── Enums ────────────────────────────────────────────────────────────────

class Classification(str, enum.Enum):
    CODE = "code"
    INFRA = "infra"
    DEPENDENCY = "dependency"
    UNKNOWN = "unknown"


class Confidence(str, enum.Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class IssueStatus(str, enum.Enum):
    RECEIVED = "received"
    TRIAGING = "triaging"
    CLASSIFIED = "classified"
    FIXING = "fixing"
    PR_CREATED = "pr_created"
    PR_MERGED = "pr_merged"
    FIX_INEFFECTIVE = "fix_ineffective"
    IGNORED = "ignored"
    RECOMMENDATION_ONLY = "recommendation_only"
    FIXING_FAILED = "fixing_failed"
    PR_CREATION_FAILED = "pr_creation_failed"


class DedupeAction(str, enum.Enum):
    CREATE = "CREATE"
    SKIP = "SKIP"
    RETRIGGER = "RETRIGGER"

class RollbackStatus(str, enum.Enum):
    PENDING = "pending"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    REVERTING = "reverting"
    REVERTED = "reverted"
    ROLLBACK_PR_OPENED = "rollback_pr_opened"
    COMPLETED = "completed"
    FAILED = "failed"
    ABORTED = "aborted"

class RollbackMode(str, enum.Enum):
    DISABLED = "disabled"
    SUGGEST_ONLY = "suggest_only"
    APPROVAL_REQUIRED = "approval_required"
    AUTO_REVERT = "auto_revert"

class RollbackStrategy(str, enum.Enum):
    ROLLBACK_PR = "rollback_pr"
    DIRECT_REVERT = "direct_revert"

class AgentImportance(str, enum.Enum):
    REQUIRED = "required"
    ADVISORY = "advisory"

class AuditAction(str, enum.Enum):
    WEBHOOK_RECEIVED = "webhook_received"
    QA_STARTED = "qa_started"
    QA_COMPLETED = "qa_completed"
    QA_BYPASSED = "qa_bypassed"
    QA_RESOLUTION_REQUESTED = "qa_resolution_requested"
    ROLLBACK_PLANNED = "rollback_planned"
    ROLLBACK_APPROVED = "rollback_approved"
    ROLLBACK_EXECUTED = "rollback_executed"
    ROLLBACK_FAILED = "rollback_failed"
    ROLLBACK_ABORTED = "rollback_aborted"
    RESOLUTION_STARTED = "resolution_started"
    RESOLUTION_COMPLETED = "resolution_completed"
    ISSUE_RECEIVED = "issue_received"
    ISSUE_DUPLICATE_SKIPPED = "issue_duplicate_skipped"
    FIX_GENERATED = "fix_generated"
    PR_CREATED = "pr_created"
    RECOMMENDATION_ONLY = "recommendation_only"

class ResolutionStatus(str, enum.Enum):
    PENDING = "pending"
    FIX_PUSHED = "fix_pushed"
    PR_OPENED = "pr_opened"
    BUILD_PASSED = "build_passed"
    BUILD_FAILED = "build_failed"
    ABANDONED = "abandoned"




# ── Call Chain Models ───────────────────────────────────────────────────

class CallFrame(BaseModel):
    """One frame in the call stack, extracted from the Sentry stack trace."""
    file_path: str
    function_name: str
    line_number: int
    context_line: str = ""

# ── Core Issue Record ────────────────────────────────────────────────────

class IssueRecord(BaseModel):
    """The single data object that flows through the entire pipeline."""

    id: str
    workspace_id: str = "default_workspace"
    repo_name: Optional[str] = None
    fingerprint: str = ""
    error_type: Optional[str] = None
    error_message: Optional[str] = None
    file_path: Optional[str] = None
    function_name: Optional[str] = None
    line_number: Optional[int] = None
    stack_trace: Optional[str] = None
    raw_payload: Optional[str] = None
    occurrence_count: int = 1
    classification: str = Classification.UNKNOWN.value
    confidence: Optional[str] = None
    status: str = IssueStatus.RECEIVED.value
    fix_pr_url: Optional[str] = None
    fix_pr_branch: Optional[str] = None
    root_cause: Optional[str] = None
    recommendation: Optional[str] = None
    previous_fix_id: Optional[str] = None
    call_chain: list[CallFrame] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class RollbackRecord(BaseModel):
    """Record of a production rollback."""
    id: str
    workspace_id: str
    repo_name: str
    failed_commit_sha: str
    rolled_back_to_sha: Optional[str] = None
    backup_branch: Optional[str] = None
    pr_number: Optional[int] = None
    pr_url: Optional[str] = None
    environment: Optional[str] = None
    deployment_ref: Optional[str] = None
    deployment_url: Optional[str] = None
    rollback_mode: str = RollbackMode.APPROVAL_REQUIRED.value
    rollback_strategy: str = RollbackStrategy.ROLLBACK_PR.value
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    approval_reason: Optional[str] = None
    failure_reason: str = ""
    status: str = RollbackStatus.PENDING.value
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class ResolutionRecord(BaseModel):
    """Record of an auto-resolution attempt following a rollback."""
    id: str
    rollback_id: str
    workspace_id: str
    repo_name: str
    backup_branch: str
    resolution_pr_url: Optional[str] = None
    resolution_pr_number: Optional[int] = None
    attempt_number: int = 1
    build_error_log: str = ""
    status: str = ResolutionStatus.PENDING.value
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)




# ── SaaS Multi-Tenant Models ──────────────────────────────────────────────────

class User(BaseModel):
    id: str
    email: str
    hashed_password: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

class Workspace(BaseModel):
    id: str
    name: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

class WorkspaceUser(BaseModel):
    workspace_id: str
    user_id: str
    role: str = "admin"

class Integration(BaseModel):
    workspace_id: str
    github_installation_id: Optional[str] = None
    sentry_webhook_secret: Optional[str] = None

class RepoConfig(BaseModel):
    workspace_id: str
    repo_name: str
    config_json: dict = Field(default_factory=dict)
    sentry_project_slug: Optional[str] = None
    active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class AuditEvent(BaseModel):
    id: str
    workspace_id: str
    repo_name: Optional[str] = None
    actor: str = "slothops"
    action: str
    target_type: Optional[str] = None
    target_id: Optional[str] = None
    metadata_json: dict = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)


# ── LLM Response Models ─────────────────────────────────────────────────

class FileChange(BaseModel):
    """One file changed by the LLM fix."""

    path: str
    original_content: str
    fixed_content: str
    explanation: str

class BuildFileChange(BaseModel):
    path: str
    fixed_content: str
    explanation: str

class BuildFixResponse(BaseModel):
    root_cause: str
    confidence: str
    files_changed: list[BuildFileChange] = Field(default_factory=list)
    generated_tests: list[BuildFileChange] = Field(default_factory=list)
    pr_title: str
    pr_body: str


class LLMFixResponse(BaseModel):
    """Parsed JSON response from Gemini 2.5 Pro."""

    root_cause: str
    confidence: str  # high | medium | low
    files_changed: list[FileChange]
    generated_tests: list[FileChange]
    pr_title: str
    pr_body: str
    deep_scan_needed: bool
    deep_scan_files: list[str]


# ── QA Agent Models ─────────────────────────────────────────────────────

class QAStatus(str, enum.Enum):
    PASSED = "passed"
    WARNING = "warning"
    FAILED = "failed"
    RUNNING = "running"
    BYPASSED = "bypassed"
    RESOLVING = "resolving"
    RESOLVED = "resolved"

class QATriageResult(BaseModel):
    risk_level: str
    categories: list[str] = Field(default_factory=list)
    required_agents: list[str] = Field(default_factory=list)
    advisory_agents: list[str] = Field(default_factory=list)
    reason: str = ""

class QAAgentResult(BaseModel):
    status: str
    summary: str
    issues: list[dict] = Field(default_factory=list)
    logs: str = ""
    artifacts: list[dict] = Field(default_factory=list)

class QAReport(BaseModel):
    id: str
    workspace_id: str
    pr_number: int
    pr_url: str = ""
    commit_sha: str = ""
    repo_name: str = ""
    static_analysis: Optional[dict] = None
    functionality: Optional[dict] = None
    stress_test: Optional[dict] = None
    vapt: Optional[dict] = None
    regression: Optional[dict] = None
    performance: Optional[dict] = None
    triage: Optional[dict] = None
    required_agents: list[str] = Field(default_factory=list)
    advisory_agents: list[str] = Field(default_factory=list)
    artifacts: list[dict] = Field(default_factory=list)
    overall_status: str = QAStatus.RUNNING.value
    summary: str = ""
    email_sent_to: Optional[str] = None
    email_sent_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
