"""
AI Change Management & Approval - Domain Models
Modelos de governança e aprovação de mudanças de IA
"""
from datetime import datetime
from enum import Enum
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
from uuid import UUID, uuid4


class ChangeRequestStatus(str, Enum):
    """Status de uma solicitação de mudança"""
    DRAFT = "draft"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class ApprovalRole(str, Enum):
    """Papéis no fluxo de aprovação"""
    DEVELOPER = "developer"  # Cria a mudança
    TECH_LEAD = "tech_lead"  # Aprova aspecto técnico
    OPS_LEAD = "ops_lead"  # Aprova aspecto operacional
    BUSINESS_OWNER = "business_owner"  # Aprova aspecto de negócio
    SECURITY = "security"  # Aprova aspecto de segurança
    COMPLIANCE = "compliance"  # Aprova aspecto de compliance


class ApprovalDecision(str, Enum):
    """Decisão de aprovação"""
    APPROVED = "approved"
    REJECTED = "rejected"
    APPROVED_WITH_CONDITIONS = "approved_with_conditions"


class ChangeImpactLevel(str, Enum):
    """Nível de impacto da mudança"""
    LOW = "low"  # Bug fix, ajuste menor
    MEDIUM = "medium"  # Nova feature, mudança de parâmetro
    HIGH = "high"  # Mudança de modelo, alteração de lógica core
    CRITICAL = "critical"  # Mudança que afeta SLA, compliance


class ChangeCategory(str, Enum):
    """Categoria da mudança"""
    BUG_FIX = "bug_fix"
    FEATURE = "feature"
    PERFORMANCE = "performance"
    SECURITY = "security"
    COMPLIANCE = "compliance"
    MODEL_UPGRADE = "model_upgrade"
    ALGORITHM_CHANGE = "algorithm_change"


class RiskLevel(str, Enum):
    """Nível de risco"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class QualityGate(BaseModel):
    """
    Critério de qualidade que deve ser atendido
    """
    name: str
    description: str
    metric: str  # Ex: "success_rate", "confidence_avg", "latency_p95"
    threshold: float
    operator: str = "gte"  # gte, lte, eq
    is_mandatory: bool = True
    
    def evaluate(self, value: float) -> bool:
        """Avalia se o valor passa no gate"""
        if self.operator == "gte":
            return value >= self.threshold
        elif self.operator == "lte":
            return value <= self.threshold
        elif self.operator == "eq":
            return value == self.threshold
        return False


class AIChangeRequest(BaseModel):
    """
    Solicitação formal de mudança de comportamento de IA
    """
    id: UUID = Field(default_factory=uuid4)
    
    # Identificação
    title: str
    description: str
    category: ChangeCategory
    impact_level: ChangeImpactLevel
    
    # Versão alvo
    behavior_version_id: UUID
    version_name: str
    
    # Justificativa
    business_justification: str
    technical_justification: str
    expected_benefits: List[str] = Field(default_factory=list)
    
    # Riscos
    known_risks: List[str] = Field(default_factory=list)
    risk_level: RiskLevel
    mitigation_plan: str
    rollback_plan: str
    
    # Impacto
    affected_tenants: Optional[List[str]] = None  # None = todos
    estimated_affected_users: int = 0
    
    # Testing
    testing_completed: bool = False
    testing_notes: str = ""
    quality_gates_passed: bool = False
    quality_gate_results: Dict[str, bool] = Field(default_factory=dict)
    
    # Status
    status: ChangeRequestStatus = ChangeRequestStatus.DRAFT
    
    # Metadados
    requested_by: str
    requested_at: datetime = Field(default_factory=datetime.utcnow)
    submitted_at: Optional[datetime] = None
    
    # Timeline
    requested_deployment_date: Optional[datetime] = None
    approved_at: Optional[datetime] = None
    rejected_at: Optional[datetime] = None
    
    class Config:
        arbitrary_types_allowed = True


class ApprovalRule(BaseModel):
    """
    Regra de aprovação baseada em impacto
    """
    impact_level: ChangeImpactLevel
    required_roles: List[ApprovalRole]
    min_approvals: int
    require_all_roles: bool = False  # True = todos devem aprovar, False = quorum


class ApprovalRecord(BaseModel):
    """
    Registro de uma aprovação individual
    """
    id: UUID = Field(default_factory=uuid4)
    change_request_id: UUID
    
    # Aprovador
    approver_id: str
    approver_name: str
    approver_role: ApprovalRole
    
    # Decisão
    decision: ApprovalDecision
    comments: str
    conditions: List[str] = Field(default_factory=list)  # Para APPROVED_WITH_CONDITIONS
    
    # Evidências
    review_notes: str = ""
    metrics_reviewed: Dict[str, Any] = Field(default_factory=dict)
    
    # Timestamp
    approved_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        frozen = True


class ApprovalFlow(BaseModel):
    """
    Fluxo de aprovação para uma mudança
    """
    id: UUID = Field(default_factory=uuid4)
    change_request_id: UUID
    
    # Regras aplicáveis
    applicable_rule: ApprovalRule
    
    # Estado
    is_complete: bool = False
    is_approved: bool = False
    
    # Aprovações recebidas
    approvals: List[ApprovalRecord] = Field(default_factory=list)
    
    # Análise
    pending_roles: List[ApprovalRole] = Field(default_factory=list)
    approved_count: int = 0
    rejected_count: int = 0
    
    # Timeline
    created_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    
    def add_approval(self, approval: ApprovalRecord):
        """Adiciona aprovação e recalcula estado"""
        self.approvals.append(approval)
        
        if approval.decision == ApprovalDecision.APPROVED:
            self.approved_count += 1
        elif approval.decision == ApprovalDecision.REJECTED:
            self.rejected_count += 1
        
        # Remover role dos pendentes
        if approval.approver_role in self.pending_roles:
            self.pending_roles.remove(approval.approver_role)
        
        # Verificar se completo
        self._check_completion()
    
    def _check_completion(self):
        """Verifica se o fluxo está completo"""
        rule = self.applicable_rule
        
        # Se qualquer rejeição, fluxo rejeitado
        if self.rejected_count > 0:
            self.is_complete = True
            self.is_approved = False
            self.completed_at = datetime.utcnow()
            return
        
        # Se require_all_roles, precisa de todos
        if rule.require_all_roles:
            roles_approved = {a.approver_role for a in self.approvals if a.decision == ApprovalDecision.APPROVED}
            if roles_approved >= set(rule.required_roles):
                self.is_complete = True
                self.is_approved = True
                self.completed_at = datetime.utcnow()
        
        # Se não, verifica quorum
        else:
            if self.approved_count >= rule.min_approvals:
                self.is_complete = True
                self.is_approved = True
                self.completed_at = datetime.utcnow()


class QualityReport(BaseModel):
    """
    Relatório de qualidade de uma versão
    """
    id: UUID = Field(default_factory=uuid4)
    behavior_version_id: UUID
    change_request_id: Optional[UUID] = None
    
    # Resultados dos gates
    gates_evaluated: List[QualityGate]
    gates_passed: Dict[str, bool]
    gates_values: Dict[str, float]
    
    # Resultado geral
    all_mandatory_gates_passed: bool
    total_gates_passed: int
    total_gates_failed: int
    
    # Métricas coletadas
    test_decisions_count: int
    test_success_rate: float
    test_avg_confidence: float
    test_avg_trust_score: float
    test_avg_latency_ms: float
    
    # Timeline
    evaluated_at: datetime = Field(default_factory=datetime.utcnow)
    evaluation_period_start: datetime
    evaluation_period_end: datetime


class ChangeApprovalPolicy(BaseModel):
    """
    Política de aprovação configurável
    """
    id: UUID = Field(default_factory=uuid4)
    name: str
    description: str
    
    # Regras por impacto
    rules: Dict[ChangeImpactLevel, ApprovalRule]
    
    # Quality gates obrigatórios
    mandatory_quality_gates: List[QualityGate] = Field(default_factory=list)
    
    # Configurações
    require_quality_report: bool = True
    require_rollback_plan: bool = True
    require_testing: bool = True
    
    # Metadados
    created_by: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    is_active: bool = True


# Policy padrão
DEFAULT_APPROVAL_POLICY = ChangeApprovalPolicy(
    name="Standard AI Change Approval Policy",
    description="Política padrão para aprovação de mudanças de IA",
    rules={
        ChangeImpactLevel.LOW: ApprovalRule(
            impact_level=ChangeImpactLevel.LOW,
            required_roles=[ApprovalRole.TECH_LEAD],
            min_approvals=1,
            require_all_roles=True,
        ),
        ChangeImpactLevel.MEDIUM: ApprovalRule(
            impact_level=ChangeImpactLevel.MEDIUM,
            required_roles=[ApprovalRole.TECH_LEAD, ApprovalRole.OPS_LEAD],
            min_approvals=2,
            require_all_roles=True,
        ),
        ChangeImpactLevel.HIGH: ApprovalRule(
            impact_level=ChangeImpactLevel.HIGH,
            required_roles=[
                ApprovalRole.TECH_LEAD,
                ApprovalRole.OPS_LEAD,
                ApprovalRole.BUSINESS_OWNER,
            ],
            min_approvals=3,
            require_all_roles=True,
        ),
        ChangeImpactLevel.CRITICAL: ApprovalRule(
            impact_level=ChangeImpactLevel.CRITICAL,
            required_roles=[
                ApprovalRole.TECH_LEAD,
                ApprovalRole.OPS_LEAD,
                ApprovalRole.BUSINESS_OWNER,
                ApprovalRole.SECURITY,
            ],
            min_approvals=4,
            require_all_roles=True,
        ),
    },
    mandatory_quality_gates=[
        QualityGate(
            name="Minimum Success Rate",
            description="Taxa mínima de sucesso nas decisões",
            metric="success_rate",
            threshold=0.95,
            operator="gte",
            is_mandatory=True,
        ),
        QualityGate(
            name="Minimum Confidence",
            description="Confiança média mínima",
            metric="avg_confidence",
            threshold=0.75,
            operator="gte",
            is_mandatory=True,
        ),
        QualityGate(
            name="Maximum Latency",
            description="Latência máxima aceitável (p95)",
            metric="latency_p95",
            threshold=500.0,
            operator="lte",
            is_mandatory=True,
        ),
    ],
    created_by="system",
    is_active=True,
)
