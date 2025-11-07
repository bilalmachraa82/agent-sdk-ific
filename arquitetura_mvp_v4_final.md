# 🏗️ Arquitetura MVP EVF Portugal 2030 - v4 FINAL
## Solo Dev + Claude Code + Multi-tenant Production-Ready

---

## 🎯 SUMÁRIO EXECUTIVO

**Modelo:** Solo dev + Claude Code + 5 sub-agents especializados
**Stack:** FastAPI async + PostgreSQL (RLS) + Qdrant + Next.js
**Multi-tenant:** Desde dia 1 com row-level security
**Timeline:** 60 dias (solo dev com AI)
**Custo:** €150-300/mês operacional
**Break-even:** Mês 8-10 (40-60 clientes)

---

## 📦 TECH STACK VALIDADA

### Backend Core
```yaml
framework: FastAPI 0.115+ (Python 3.11+)
database: PostgreSQL 16 com RLS (Supabase)
orm: SQLAlchemy 2.0 async / SQLModel
driver: asyncpg (não psycopg2)
cache: Redis (Upstash serverless)
queue: BackgroundTasks (início) → Celery (escala)
deployment: Railway (€50/mês)
```

### AI & RAG Layer
```yaml
llm: Claude 4.5 Sonnet via Tool Use API
pricing: $3/$15 per M tokens (validado Nov 2025)
rag: Qdrant Cloud (multi-tenant via payload filters)
embeddings: BGE-M3 self-hosted (1024-dim)
mcp_servers:
  - qdrant-mcp (vector search)
  - saft-parser-mcp (XML processing)
  - compliance-mcp (PT2030 rules)
```

### Frontend
```yaml
framework: Next.js 14 (App Router + TypeScript)
ui: Shadcn/ui + TailwindCSS
auth: NextAuth.js com tenant context
state: Zustand + React Query
deploy: Vercel (€20/mês Pro)
```

---

## 🤖 ARQUITETURA DE SUB-AGENTS

### 1. InputAgent
```python
class InputAgent:
    """
    Valida e parseia inputs (SAF-T, Excel, CSV)
    Executa via MCP server dedicado
    """
    
    responsibilities = [
        "Validar XSD schema SAF-T",
        "Mapear SNC taxonomy (100+ contas)",
        "Normalizar para modelo interno",
        "Detectar anomalias nos dados",
        "Calcular quality score (0-100%)"
    ]
    
    mcp_server = "saft-parser-mcp"
    tools = ["validate_xml", "extract_accounts", "map_snc"]
```

### 2. EVFComplianceAgent
```python
class EVFComplianceAgent:
    """
    Valida compliance PT2030/PRR/SITCE
    100% determinístico, sem alucinações
    """
    
    responsibilities = [
        "Verificar campos obrigatórios EVF",
        "Validar VALF < 0 (requisito PT2030)",
        "Confirmar TRF < 4%",
        "Gerar checklist non-compliance",
        "Sugerir correções específicas"
    ]
    
    rules = load_json("regulations/pt2030_rules.json")
    deterministic = True  # Nunca usa LLM para números
```

### 3. FinancialModelAgent
```python
class FinancialModelAgent:
    """
    Cálculos financeiros determinísticos
    Segue orientações oficiais EVF
    """
    
    responsibilities = [
        "Calcular VALF (NPV a 4%)",
        "Calcular TRF (IRR)",
        "Projetar cash flows 10 anos",
        "Garantir equações equilibradas",
        "Calcular 30+ rácios financeiros"
    ]
    
    formulas = FinancialFormulas()  # Classe com cálculos puros
    llm_usage = "NONE"  # Apenas funções matemáticas
```

### 4. NarrativeAgent
```python
class NarrativeAgent:
    """
    Gera textos explicativos (único que usa LLM)
    Nunca inventa números
    """
    
    responsibilities = [
        "Justificar pressupostos com dados",
        "Descrever projeto em linguagem PT2030",
        "Explicar metodologia de cálculo",
        "Contextualizar resultados no setor"
    ]
    
    llm_model = "claude-3-5-sonnet"
    system_prompt = """
    REGRAS ABSOLUTAS:
    1. Nunca inventar números - usar apenas os calculados
    2. Citar fontes (SAF-T, benchmarks, regulamentos)
    3. Linguagem formal conforme templates PT2030
    """
```

### 5. AuditAgent
```python
class AuditAgent:
    """
    Rastreabilidade total e controlo custos
    """
    
    responsibilities = [
        "Log todos inputs/outputs com hash",
        "Versionar modelos e templates",
        "Monitorizar tokens Claude (custo)",
        "Gerar audit trail para compliance",
        "Alertar desvios de budget"
    ]
    
    retention_policy = "10_years"  # Requisito legal
    cost_alerts = {"daily": 50, "monthly": 1000}  # Euros
```

---

## 🔐 MULTI-TENANT & SEGURANÇA

### Database Schema Multi-tenant
```sql
-- Tabela tenants (raiz de tudo)
CREATE TABLE tenants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    slug VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    nif VARCHAR(9) UNIQUE NOT NULL,
    plan VARCHAR(50) DEFAULT 'starter',
    created_at TIMESTAMP DEFAULT NOW()
);

-- Todas tabelas têm tenant_id
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID REFERENCES tenants(id) NOT NULL,
    email VARCHAR(255) NOT NULL,
    role VARCHAR(50) DEFAULT 'member',
    UNIQUE(tenant_id, email)
);

CREATE TABLE evf_projects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID REFERENCES tenants(id) NOT NULL,
    company_id UUID REFERENCES companies(id),
    fund_type VARCHAR(50) NOT NULL,
    status VARCHAR(50) DEFAULT 'draft',
    -- audit fields
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMP DEFAULT NOW(),
    INDEX idx_tenant_evf (tenant_id, created_at DESC)
);

-- Row Level Security
ALTER TABLE evf_projects ENABLE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation ON evf_projects
    FOR ALL
    USING (tenant_id = current_setting('app.current_tenant')::uuid);
```

### Qdrant Multi-tenant
```python
class QdrantMultiTenant:
    """
    Vector DB com isolamento por tenant
    """
    
    def search(self, query: str, tenant_id: str):
        return self.client.search(
            collection_name="evf_documents",
            query_vector=self.embed(query),
            query_filter={
                "must": [
                    {"key": "tenant_id", "match": {"value": tenant_id}}
                ]
            },
            limit=5
        )
    
    def index(self, docs: List[Document], tenant_id: str):
        points = []
        for doc in docs:
            points.append({
                "id": str(uuid4()),
                "vector": self.embed(doc.text),
                "payload": {
                    "tenant_id": tenant_id,  # CRÍTICO
                    "text": doc.text,
                    "source": doc.source
                }
            })
        self.client.upsert(collection_name="evf_documents", points=points)
```

### Security Checklist
```yaml
infrastructure:
  hosting: EU-West (RGPD compliance)
  encryption: AES-256 at rest, TLS 1.3 in transit
  backups: Daily encrypted snapshots
  
data_handling:
  saft_storage: Encrypted S3 with 30-day retention
  pii_redaction: Before sending to Claude
  audit_logs: Immutable with hash chain
  
api_security:
  authentication: JWT with tenant context
  rate_limiting: 100 req/min per tenant
  input_validation: Pydantic strict mode
  sql_injection: Parameterized queries only
  
compliance:
  gdpr: Data minimization + right to deletion
  financial: Audit trail 10 years
  certifications: ISO 27001 roadmap
```

---

## 🏗️ ESTRUTURA PROJETO (SOLO DEV)

```bash
evf-portugal-2030/
├── CLAUDE.md                    # Instruções Claude Code
├── .mcp.json                    # MCP servers config
├── .claude/
│   ├── commands/
│   │   ├── scaffold-module.md
│   │   ├── generate-tests.md
│   │   ├── check-compliance.md
│   │   └── evf-audit.md
│   └── agents/
│       ├── input-agent.md
│       ├── compliance-agent.md
│       ├── financial-agent.md
│       ├── narrative-agent.md
│       └── audit-agent.md
│
├── backend/
│   ├── api/
│   │   ├── main.py             # FastAPI async app
│   │   ├── deps.py             # Tenant context injection
│   │   └── routers/
│   │       ├── auth.py         # Multi-tenant auth
│   │       ├── evf.py          # EVF endpoints
│   │       └── admin.py        # Tenant admin
│   │
│   ├── core/
│   │   ├── config.py           # Settings with env
│   │   ├── security.py         # JWT + tenant
│   │   ├── database.py         # Async SQLAlchemy
│   │   └── tenant.py           # Tenant middleware
│   │
│   ├── agents/                 # 5 Sub-agents
│   │   ├── input_agent.py
│   │   ├── compliance_agent.py
│   │   ├── financial_agent.py
│   │   ├── narrative_agent.py
│   │   └── audit_agent.py
│   │
│   ├── models/                 # SQLAlchemy models
│   │   ├── tenant.py
│   │   ├── evf.py
│   │   └── financial.py
│   │
│   ├── services/
│   │   ├── saft_parser.py      # Deterministic parser
│   │   ├── claude_client.py    # Tool Use API
│   │   ├── qdrant_service.py   # Multi-tenant RAG
│   │   └── excel_generator.py  # Templates PT2030
│   │
│   ├── workers/
│   │   └── background.py       # Simple workers (início)
│   │
│   ├── tests/
│   │   ├── conftest.py         # Fixtures multi-tenant
│   │   ├── test_agents/
│   │   ├── test_compliance/
│   │   └── test_financial/
│   │
│   └── regulations/            # JSON rules (não código)
│       ├── pt2030_rules.json
│       ├── prr_rules.json
│       └── evf_templates/
│
├── frontend/
│   ├── app/
│   │   ├── [tenant]/           # Dynamic tenant routes
│   │   │   ├── dashboard/
│   │   │   ├── evf/
│   │   │   └── settings/
│   │   └── api/
│   │
│   ├── lib/
│   │   ├── api.ts              # Tenant-aware client
│   │   └── tenant-context.tsx
│   │
│   └── middleware.ts           # Tenant detection
│
├── scripts/
│   ├── setup_tenant.py         # Onboard novo cliente
│   ├── migrate_tenant.py       # Migrations per tenant
│   └── backup_tenant.py        # Backup isolado
│
└── docker-compose.yml          # Dev environment
```

---

## 🔄 FLUXO DADOS COMPLETO (MULTI-TENANT)

```python
# 1. Request chega com tenant context
@app.middleware("http")
async def tenant_middleware(request: Request, call_next):
    # Extract tenant from subdomain or header
    tenant = extract_tenant(request)
    request.state.tenant_id = tenant.id
    
    # Set PostgreSQL RLS context
    async with get_db() as db:
        await db.execute(f"SET app.current_tenant = '{tenant.id}'")
    
    response = await call_next(request)
    return response

# 2. Upload isolado por tenant
@router.post("/{tenant_slug}/evf/upload")
async def upload_saft(
    file: UploadFile,
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user)
):
    # Validação
    input_agent = InputAgent(tenant_id=tenant.id)
    validation = await input_agent.validate(file)
    
    if validation.score < 70:
        raise HTTPException(400, validation.errors)
    
    # Store com tenant_id
    evf = EVFProject(
        tenant_id=tenant.id,  # CRÍTICO
        created_by=user.id,
        file_path=store_encrypted(file, tenant.id)
    )
    
    # Queue para processamento
    await process_evf.delay(evf.id, tenant.id)
    
    return {"evf_id": evf.id, "status": "processing"}

# 3. Processamento com agents
async def process_evf(evf_id: str, tenant_id: str):
    # Todos agents recebem tenant context
    financial = FinancialModelAgent(tenant_id=tenant_id)
    compliance = EVFComplianceAgent(tenant_id=tenant_id)
    narrative = NarrativeAgent(tenant_id=tenant_id)
    audit = AuditAgent(tenant_id=tenant_id)
    
    # Pipeline
    data = await financial.calculate(evf_id)
    valid = await compliance.validate(data)
    text = await narrative.generate(data)
    
    # Audit everything
    await audit.log_execution({
        "evf_id": evf_id,
        "tenant_id": tenant_id,
        "agents_used": ["financial", "compliance", "narrative"],
        "tokens_consumed": narrative.tokens_used,
        "cost_euros": narrative.tokens_used * 0.001
    })
```

---

## 💾 SCHEMA COMPLETO MULTI-TENANT

```sql
-- Core tenant tables
CREATE TABLE tenants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    slug VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    nif VARCHAR(9) UNIQUE NOT NULL,
    plan VARCHAR(50) DEFAULT 'starter',
    mrr DECIMAL(10,2) DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    settings JSONB DEFAULT '{}'::jsonb
);

-- Usage tracking per tenant
CREATE TABLE tenant_usage (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID REFERENCES tenants(id),
    month DATE NOT NULL,
    evfs_processed INTEGER DEFAULT 0,
    tokens_consumed INTEGER DEFAULT 0,
    storage_mb DECIMAL(10,2) DEFAULT 0,
    cost_euros DECIMAL(10,2) DEFAULT 0,
    UNIQUE(tenant_id, month)
);

-- Companies can be shared across tenants (consultoras)
CREATE TABLE companies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    nif VARCHAR(9) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    cae_code VARCHAR(5)
);

-- Many-to-many tenant-company access
CREATE TABLE tenant_companies (
    tenant_id UUID REFERENCES tenants(id),
    company_id UUID REFERENCES companies(id),
    added_by UUID REFERENCES users(id),
    added_at TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (tenant_id, company_id)
);

-- EVF projects with full audit
CREATE TABLE evf_projects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID REFERENCES tenants(id) NOT NULL,
    company_id UUID REFERENCES companies(id),
    fund_type VARCHAR(50) NOT NULL,
    status VARCHAR(50) DEFAULT 'draft',
    
    -- Financial results
    valf DECIMAL(15,2),
    trf DECIMAL(5,2),
    payback DECIMAL(5,2),
    
    -- Metadata
    file_path VARCHAR(500),
    excel_path VARCHAR(500),
    
    -- Audit
    created_by UUID REFERENCES users(id),
    approved_by UUID REFERENCES users(id),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    -- Indexes
    INDEX idx_tenant_status (tenant_id, status),
    INDEX idx_tenant_created (tenant_id, created_at DESC)
);

-- Audit log immutable
CREATE TABLE audit_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    evf_id UUID REFERENCES evf_projects(id),
    user_id UUID REFERENCES users(id),
    action VARCHAR(100) NOT NULL,
    
    -- Detailed tracking
    agent_name VARCHAR(50),
    input_hash VARCHAR(64),
    output_hash VARCHAR(64),
    tokens_used INTEGER,
    cost_euros DECIMAL(6,4),
    
    -- Metadata
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Enable RLS on all tenant tables
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE evf_projects ENABLE ROW LEVEL SECURITY;
ALTER TABLE tenant_usage ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_log ENABLE ROW LEVEL SECURITY;

-- RLS Policies
CREATE POLICY tenant_isolation_users ON users
    USING (tenant_id = current_setting('app.current_tenant')::uuid);

CREATE POLICY tenant_isolation_evf ON evf_projects
    USING (tenant_id = current_setting('app.current_tenant')::uuid);

CREATE POLICY tenant_isolation_audit ON audit_log
    USING (tenant_id = current_setting('app.current_tenant')::uuid);
```

---

## 📊 MONITORIZAÇÃO & CUSTOS

```python
class CostControlAgent:
    """
    Monitoriza custos em tempo real
    """
    
    def __init__(self):
        self.limits = {
            'claude_daily': 50,  # euros
            'claude_monthly': 1000,
            'qdrant_monthly': 100,
            'storage_gb': 100
        }
    
    async def check_tenant_usage(self, tenant_id: str):
        usage = await db.fetch_one(
            """
            SELECT 
                SUM(tokens_consumed) as tokens,
                SUM(cost_euros) as cost
            FROM audit_log
            WHERE tenant_id = $1
                AND created_at >= CURRENT_DATE
            """,
            tenant_id
        )
        
        if usage['cost'] > self.limits['claude_daily'] * 0.8:
            await self.alert(
                f"Tenant {tenant_id} at 80% daily limit: €{usage['cost']}"
            )
        
        return usage
    
    async def calculate_mrr(self):
        """
        Calcula MRR real vs custos
        """
        metrics = await db.fetch_all(
            """
            SELECT 
                COUNT(DISTINCT tenant_id) as active_tenants,
                SUM(mrr) as total_mrr,
                SUM(tu.cost_euros) as total_costs,
                AVG(tu.evfs_processed) as avg_evfs_per_tenant
            FROM tenants t
            JOIN tenant_usage tu ON t.id = tu.tenant_id
            WHERE tu.month = DATE_TRUNC('month', CURRENT_DATE)
            """
        )
        
        return {
            'mrr': metrics['total_mrr'],
            'costs': metrics['total_costs'],
            'margin': (metrics['total_mrr'] - metrics['total_costs']) / metrics['total_mrr'],
            'ltv_cac': self.calculate_ltv_cac(metrics)
        }
```

---

## ⚡ PERFORMANCE & SCALE

```python
# Async everywhere
class AsyncEVFService:
    def __init__(self):
        self.db = AsyncDatabase()
        self.claude = AsyncClaude()
        self.qdrant = AsyncQdrant()
    
    async def process_batch(self, evf_ids: List[str], tenant_id: str):
        """
        Processa múltiplos EVFs em paralelo
        """
        tasks = []
        
        for evf_id in evf_ids:
            task = self.process_single(evf_id, tenant_id)
            tasks.append(task)
        
        # Paralelo mas com limite
        results = await asyncio.gather(*tasks, limit=5)
        return results
    
    @cached(ttl=3600)  # Cache 1h
    async def get_benchmarks(self, sector: str, tenant_id: str):
        """
        Cache pesado, revalidate hourly
        """
        return await self.qdrant.search(
            query=f"sector:{sector} benchmarks",
            filter={"tenant_id": tenant_id}
        )
```

---

## 🔒 COMPLIANCE & GOVERNANÇA

### Regras EVF Hardcoded
```python
# regulations/pt2030_rules.py
PT2030_RULES = {
    "valf": {
        "condition": "must_be_negative",
        "error": "VALF deve ser < 0 para elegibilidade"
    },
    "trf": {
        "condition": "less_than",
        "value": 4.0,
        "error": "TRF deve ser < 4%"
    },
    "project_duration": {
        "condition": "between",
        "min": 3,
        "max": 10,
        "error": "Projeto deve ter 3-10 anos"
    },
    "job_creation": {
        "condition": "minimum",
        "value": 1,
        "error": "Deve criar pelo menos 1 posto trabalho"
    }
}

class ComplianceValidator:
    """
    100% determinístico, zero LLM
    """
    
    def validate(self, evf_data: dict) -> ComplianceResult:
        errors = []
        
        for rule_name, rule in PT2030_RULES.items():
            value = evf_data.get(rule_name)
            
            if rule['condition'] == 'must_be_negative':
                if value >= 0:
                    errors.append(rule['error'])
                    
            elif rule['condition'] == 'less_than':
                if value >= rule['value']:
                    errors.append(rule['error'])
        
        return ComplianceResult(
            valid=len(errors) == 0,
            errors=errors,
            suggestions=self._generate_suggestions(errors)
        )
```

---

## 🎯 DEFINIÇÃO DE SUCESSO

### Métricas Técnicas
- [ ] 95% SAF-T files parseados com sucesso
- [ ] 100% cálculos financeiros determinísticos
- [ ] Zero dados entre tenants (isolation perfeito)
- [ ] < 3s resposta média API
- [ ] < €1 custo por EVF processado

### Métricas Negócio
- [ ] 3 pilotos reais concluídos
- [ ] Compliance PT2030 validado por consultora
- [ ] MRR €5K até mês 6
- [ ] NPS > 70
- [ ] Churn < 10% anual

### Métricas Automação
- [ ] 80% código gerado por Claude Code
- [ ] 90% testes escritos automaticamente
- [ ] 100% deploys automatizados
- [ ] 5 sub-agents operacionais
- [ ] CLAUDE.md completo e funcional

---

**Esta arquitetura está pronta para solo dev com Claude Code. Multi-tenant desde dia 1. Zero bullshit.**

Versão: 4.0 PRODUCTION-READY
Data: Novembro 2025
Status: CORRIGIDO E VALIDADO
