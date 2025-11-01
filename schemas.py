"""
FundAI Data Schemas
Pydantic models for request/response validation and data structures
"""

from datetime import datetime
from enum import Enum
from typing import Any, Literal
from pydantic import BaseModel, Field, HttpUrl, field_validator


# ============================================================================
# ENUMS
# ============================================================================

class CompanySize(str, Enum):
    """Company size classification"""
    MICRO = "micro"
    PEQUENA = "pequena"
    MEDIA = "media"


class NUTSII(str, Enum):
    """Portuguese NUTS II regions"""
    PT11 = "PT11"  # Norte
    PT16 = "PT16"  # Centro
    PT17 = "PT17"  # Área Metropolitana de Lisboa
    PT18 = "PT18"  # Alentejo
    PT15 = "PT15"  # Algarve
    PT20 = "PT20"  # Região Autónoma dos Açores
    PT30 = "PT30"  # Região Autónoma da Madeira


class ApplicationStatus(str, Enum):
    """Application processing status"""
    DRAFT = "draft"
    RESEARCH_IN_PROGRESS = "research_in_progress"
    RESEARCH_COMPLETE = "research_complete"
    PROPOSAL_GENERATION = "proposal_generation"
    VALIDATION = "validation"
    READY = "ready"
    SUBMITTED = "submitted"
    APPROVED = "approved"
    REJECTED = "rejected"


class BudgetTier(str, Enum):
    """Budget scenario tiers"""
    ESSENCIAL = "essencial"
    RECOMENDADO = "recomendado"
    COMPLETO = "completo"


# ============================================================================
# COMPANY DATA
# ============================================================================

class CompanyInput(BaseModel):
    """Initial company information from user"""
    nome: str = Field(min_length=2, max_length=200)
    url: HttpUrl | None = None
    nif: str | None = Field(None, pattern=r"^\d{9}$")
    cae: str | None = Field(None, pattern=r"^\d{5}$")
    nuts_ii: NUTSII | None = None
    certificacao_pme: bool = True
    dimensao: CompanySize | None = None


class CompanyData(BaseModel):
    """Complete company data after research"""
    # Basic info
    nome: str
    denominacao_legal: str | None = None
    nif: str
    cae: str
    cae_descricao: str | None = None
    nuts_ii: NUTSII
    morada_completa: str | None = None
    
    # Classification
    certificacao_pme: bool
    dimensao: CompanySize
    headcount: int | None = None
    
    # Financial (latest year)
    capital_social: float | None = None
    volume_negocios: float | None = None
    resultado_liquido: float | None = None
    ano_fiscal: int | None = None
    
    # Tech stack
    tech_stack: list[str] = Field(default_factory=list)
    erp_sistema: str | None = None
    crm_sistema: str | None = None
    cloud_provider: str | None = None
    
    # Compliance
    situacao_fiscal_regular: bool = False
    situacao_ss_regular: bool = False
    situacao_rcbe_regular: bool = False
    
    # Sources & audit
    data_sources: dict[str, str] = Field(default_factory=dict)
    last_updated: datetime = Field(default_factory=datetime.utcnow)


# ============================================================================
# PROJECT & BUDGET
# ============================================================================

class ProjectInput(BaseModel):
    """Project scope and objectives"""
    objetivos: str = Field(min_length=20, max_length=2000)
    processos_alvo: list[str] = Field(min_length=1, max_length=10)
    dados_disponiveis: str | None = None
    inicio_previsto: str = Field(pattern=r"^\d{4}-\d{2}$")  # YYYY-MM
    fim_previsto: str = Field(pattern=r"^\d{4}-\d{2}$")
    departamentos: list[str] = Field(default_factory=list)


class BudgetInput(BaseModel):
    """Budget constraints and preferences"""
    teto_max_investimento: float = Field(gt=5_000, le=500_000)
    cofinanciamento_disponivel: float = Field(ge=0)
    preferencias: list[str] = Field(default_factory=list)
    
    @field_validator("cofinanciamento_disponivel")
    @classmethod
    def validate_cofinancing(cls, v, info):
        teto = info.data.get("teto_max_investimento", 0)
        if v < teto * 0.25:
            raise ValueError(f"Cofinanciamento mínimo: 25% de {teto} = {teto * 0.25:.2f}€")
        return v


class BudgetLine(BaseModel):
    """Single budget line item"""
    categoria: str
    descricao: str
    quantidade: int = 1
    valor_unitario: float
    valor_total: float
    elegivel: bool
    justificacao: str | None = None
    citacao_normativa: str | None = None


class BudgetScenario(BaseModel):
    """Complete budget for one tier"""
    tier: BudgetTier
    linhas: list[BudgetLine]
    total_investimento: float
    total_elegivel: float
    incentivo_estimado: float
    cofinanciamento_necessario: float
    distribuicao_percentual: dict[str, float]


# ============================================================================
# MERIT SCORING
# ============================================================================

class ImpactMetrics(BaseModel):
    """Impact metrics for scoring"""
    postos_trabalho_liquidos: int = Field(ge=0, le=10)
    crescimento_vab_percent: float = Field(ge=0, le=100)
    exportacoes_aumento_percent: float = Field(ge=0, le=100, default=0)
    inovacao_score: float = Field(ge=0, le=5, default=3.0)


class MeritScore(BaseModel):
    """Merit scoring breakdown"""
    criterio_a_qualidade: float = Field(ge=0, le=5)
    criterio_b1_competitividade: float = Field(ge=0, le=5)
    criterio_b2_mercado: float = Field(ge=0, le=5)
    merit_point_final: float = Field(ge=0, le=5)
    ranking: Literal["baixo", "medio", "alto", "muito_alto"]
    elegivel: bool
    competitivo: bool
    
    @field_validator("merit_point_final")
    @classmethod
    def calculate_mp(cls, v, info):
        a = info.data.get("criterio_a_qualidade", 0)
        b1 = info.data.get("criterio_b1_competitividade", 0)
        b2 = info.data.get("criterio_b2_mercado", 0)
        calculated = 0.5 * a + 0.5 * min(b1, b2)
        return round(calculated, 2)


class ScoringScenario(BaseModel):
    """What-if scoring scenario"""
    empregos: int
    crescimento_vab: float
    score: MeritScore


# ============================================================================
# USE CASES & DELIVERABLES
# ============================================================================

class UseCase(BaseModel):
    """AI use case specification"""
    id: str
    titulo: str
    descricao: str
    departamento: str
    tecnologias: list[str]
    dados_necessarios: list[str]
    kpis: dict[str, str]
    roi_estimado_percent: float = Field(ge=0, le=100)
    payback_meses: int = Field(ge=1, le=60)
    prioridade: Literal["alta", "media", "baixa"] = "media"


class TrainingModule(BaseModel):
    """Training module specification"""
    modulo: str
    perfis_alvo: list[str]
    duracao_horas: int
    conteudos: list[str]
    custo_estimado: float


# ============================================================================
# VALIDATION & COMPLIANCE
# ============================================================================

class ValidationResult(BaseModel):
    """Validation check result"""
    check: str
    passed: bool
    message: str
    severity: Literal["error", "warning", "info"]
    citacao: str | None = None


class ComplianceReport(BaseModel):
    """Complete compliance validation"""
    rgpd_compliant: bool
    dnsh_compliant: bool
    duplo_financiamento_ok: bool
    elegibilidade_ok: bool
    validations: list[ValidationResult]
    overall_status: Literal["pass", "conditional", "fail"]


# ============================================================================
# ARTIFACTS & OUTPUT
# ============================================================================

class ProposalArtifact(BaseModel):
    """Generated proposal artifact"""
    artifact_type: Literal["html", "csv", "json", "pdf"]
    filename: str
    content: str | bytes
    size_bytes: int
    mime_type: str
    generated_at: datetime = Field(default_factory=datetime.utcnow)


class AuditTrail(BaseModel):
    """Audit trail for proposal generation"""
    session_id: str
    user_id: str | None = None
    company_nif: str
    timestamps: dict[str, datetime]
    data_sources: dict[str, list[str]]
    agent_calls: list[dict[str, Any]]
    validations: list[ValidationResult]
    final_status: ApplicationStatus


# ============================================================================
# COMPLETE APPLICATION
# ============================================================================

class FundingApplication(BaseModel):
    """Complete funding application"""
    application_id: str
    status: ApplicationStatus
    
    # Core data
    company: CompanyData
    project: ProjectInput
    budget: BudgetInput
    impact: ImpactMetrics
    
    # Analysis results
    budget_scenarios: list[BudgetScenario]
    use_cases: list[UseCase]
    training_plan: list[TrainingModule]
    merit_scoring: MeritScore
    scoring_scenarios: list[ScoringScenario]
    compliance: ComplianceReport
    
    # Artifacts
    artifacts: list[ProposalArtifact]
    audit_trail: AuditTrail
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    submitted_at: datetime | None = None
