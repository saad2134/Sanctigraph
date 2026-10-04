import time
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field


class AlertPayload(BaseModel):
    alertname: str = Field(..., description="Name of the Prometheus / Datadog alert")
    severity: Literal["P0", "P1", "P2", "P3"] = Field(default="P0")
    service: str = Field(..., description="Impacted microservice")
    summary: str
    description: str
    startsAt: Optional[str] = None
    labels: Dict[str, str] = Field(default_factory=dict)


class TelemetrySnapshot(BaseModel):
    service: str
    error_rate_percent: float
    p99_latency_ms: float
    active_connections: int
    max_connections: int
    worker_replicas: int
    memory_mb: float
    recent_logs: List[Dict[str, Any]] = Field(default_factory=list)
    git_commits: List[Dict[str, Any]] = Field(default_factory=list)
    k8s_pods: List[Dict[str, Any]] = Field(default_factory=list)


class RootCauseAnalysis(BaseModel):
    incident_id: str
    summary: str
    root_cause: str
    confidence: float = Field(ge=0.0, le=1.0)
    evidence: List[str]
    affected_services: List[str]
    is_fallback: bool = False
    timestamp: float = Field(default_factory=time.time)


class BlastRadius(BaseModel):
    risk_score: int = Field(ge=1, le=100)
    risk_tier: Literal["TIER_1_AUTO_READ", "TIER_2_GUARDED_WRITE", "TIER_3_BLOCKED"]
    human_approval_required: bool
    affected_components: List[str]
    estimated_downtime_reduction_mins: int
    reasoning: str


class DAGStep(BaseModel):
    step_id: str
    title: str
    tool_name: str
    parameters: Dict[str, Any]
    blast_tier: Literal["TIER_1_AUTO_READ", "TIER_2_GUARDED_WRITE", "TIER_3_BLOCKED"]
    status: Literal["PENDING", "RUNNING", "COMPLETED", "FAILED", "SKIPPED"] = "PENDING"
    stdout: Optional[str] = None
    stderr: Optional[str] = None
    idempotency_key: str
    execution_time_ms: Optional[int] = None


class RemediationPlan(BaseModel):
    plan_id: str
    incident_id: str
    steps: List[DAGStep]
    rollback_vectors: List[DAGStep]
    plan_hash: str
    estimated_recovery_time_s: int
    created_at: float = Field(default_factory=time.time)


class HMACApprovalToken(BaseModel):
    incident_id: str
    plan_hash: str
    signature: str
    expires_at: float
    redeemed: bool = False


class CanaryEvaluation(BaseModel):
    phase: Literal["PHASE_1_POD_READINESS", "PHASE_2_TELEMETRY_OBSERVATION"]
    samples_collected: int
    median_error_rate: float
    median_p99_latency: float
    traffic_floor_met: bool
    slo_restored: bool
    auto_rollback_triggered: bool = False
    summary: str


class IncidentRecord(BaseModel):
    incident_id: str
    title: str
    service: str
    severity: Literal["P0", "P1", "P2", "P3"]
    status: Literal[
        "INGESTED",
        "TRIAGING",
        "AWAITING_APPROVAL",
        "EXECUTING",
        "VERIFYING",
        "RESOLVED",
        "ROLLBACK",
        "FAILED",
    ]
    created_at: float = Field(default_factory=time.time)
    resolved_at: Optional[float] = None
    alert: AlertPayload
    telemetry: Optional[TelemetrySnapshot] = None
    rca: Optional[RootCauseAnalysis] = None
    blast_radius: Optional[BlastRadius] = None
    plan: Optional[RemediationPlan] = None
    approval_token: Optional[HMACApprovalToken] = None
    canary: Optional[CanaryEvaluation] = None
    postmortem: Optional[str] = None
    logs: List[str] = Field(default_factory=list)
