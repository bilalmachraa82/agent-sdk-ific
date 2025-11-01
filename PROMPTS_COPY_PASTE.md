# 🎯 PROMPTS COPY-PASTE — Claude Code Implementation

**Como usar**: Copia cada prompt sequencialmente para o Claude Code. Aguarda confirmação após cada fase antes de avançar.

---

## 🏗️ PROMPT INICIAL (Setup)

```
Olá Claude Code!

Vou construir o FundAI — um SaaS para automatizar candidaturas ao fundo IFIC (Aviso 03/C05-i14.01/2025 — "IA nas PME").

Tenho a especificação técnica completa em IFIC_SAAS_CLAUDE_CONFIG.md (58 KB, 1000+ linhas).

**Contexto Crítico**:
- Este sistema NUNCA pode sugerir ferramentas redundantes
- Exemplo: Se empresa usa PHC (ERP português), NÃO pode sugerir Monday.com, HubSpot CRM ou Salesforce
- Exemplo: Se empresa tem Microsoft 365, NÃO pode sugerir Slack, Notion ou Trello
- Esta inteligência de stack é o DIFERENCIADOR competitivo

**Abordagem**:
- Python 3.11+ com type hints completos
- Claude API (Sonnet 4) para agentes IA
- FastAPI para backend
- PostgreSQL para database
- React + TypeScript para frontend
- Testes unitários obrigatórios para cada componente

**FASE 1 — FOUNDATION** (Começar agora):

1. Cria estrutura de pastas completa conforme IFIC_SAAS_CLAUDE_CONFIG.md (linhas 30-92)
2. Setup environment:
   - requirements.txt com: anthropic, fastapi, sqlalchemy, jinja2, pandas, pytest, httpx
   - pyproject.toml com metadata do projeto
   - .env.example com CLAUDE_API_KEY, DATABASE_URL
   - .gitignore adequado
3. docker-compose.yml com services: api, db (postgres), web
4. Cria agents/__init__.py e base class BaseAgent com logging comum
5. Skeleton de agents/orchestrator.py com IFICOrchestrator class

**Output esperado**:
- Todos os ficheiros criados
- Estrutura de pastas verificável com `tree fundai/`
- README.md básico com instruções de setup

Mostra-me os ficheiros criados e aguarda minha confirmação antes de FASE 2.

IMPORTANTE: Lê IFIC_SAAS_CLAUDE_CONFIG.md completo antes de começar!
```

---

## 📊 FASE 1 — FOUNDATION

**Prompt após revisão**:
```
FASE 1 aprovada! Estrutura criada com sucesso.

Agora FASE 2 — COMPANY RESEARCH AGENT:

Objetivo: Criar agente que recolhe dados de empresas de fontes públicas (eInforma, Racius, website).

**Tarefas**:

1. Cria agents/researcher.py com classe CompanyResearchAgent
   - __init__(self, claude_client)
   - async fetch(nome: str, nif: str = None, sources: List[str]) -> Dict
   - async _detect_stack_from_website(url: str) -> List[str]
   - _infer_nuts_ii(address: str) -> str
   - _classify_sme_size(headcount: int, revenue: float) -> str

2. Por agora usa MOCK para eInforma:
   - Cria tests/fixtures/mock_einforma.json com exemplo de empresa:
     ```json
     {
       "legal_name": "InnovaSolutions Lda",
       "nif": "123456789",
       "cae_principal": "62010",
       "address": "Rua Exemplo 123, Lisboa",
       "balance_sheet": {
         "volume_negocios_2024": 850000,
         "ebitda_2024": 125000,
         ...
       }
     }
     ```

3. _detect_stack_from_website deve:
   - Usar Claude API com web_fetch (MCP tool)
   - Procurar menções de: PHC, SAP, Microsoft 365, Salesforce, etc.
   - Prompt exemplo no código

4. _infer_nuts_ii com mapping:
   - Lisboa/Setúbal → PT17
   - Porto/Braga → PT11
   - Coimbra → PT16
   - Fuzzy match para cidades

5. Testes unitários em tests/unit/test_researcher.py:
   - test_fetch_with_mock_einforma()
   - test_nuts_ii_inference()
   - test_sme_classification()

**Referência**: IFIC_SAAS_CLAUDE_CONFIG.md linhas 160-270

Mostra código completo de agents/researcher.py e testes. Aguardo revisão.
```

---

## 🧠 FASE 2 — COMPANY RESEARCH AGENT

**Prompt após revisão**:
```
FASE 2 ✓ — CompanyResearchAgent implementado!

Agora FASE 3 — STACK INTELLIGENCE AGENT:

Objetivo: Detetar redundâncias tecnológicas e sugerir apenas ferramentas complementares.

**Tarefas**:

1. Cria mcp_servers/stack_detector_mcp/rules.yaml:
   ```yaml
   PHC:
     category: "ERP"
     coverage: ["CRM", "Finance", "Inventory", "Sales"]
     blocks: ["Monday.com", "HubSpot CRM", "Salesforce", "Pipedrive"]
     suggests: ["Power BI Embedded", "Azure ML", "PHC Analytics Module"]
   
   Microsoft_365:
     category: "Productivity Suite"
     coverage: ["Email", "Collaboration", "Document Management"]
     blocks: ["Slack", "Notion", "Trello", "Asana", "ClickUp"]
     suggests: ["Microsoft Copilot", "Power Automate", "Power Apps"]
   
   SAP:
     category: "ERP Enterprise"
     blocks: ["NetSuite", "Odoo", "Sage"]
     suggests: ["SAP Analytics Cloud", "SAP AI Business Services"]
   
   # Adiciona mais 5-10 sistemas comuns
   ```

2. Implementa agents/stack_intelligence.py:
   - class StackIntelligenceAgent
   - _load_redundancy_rules() → lê YAML
   - async analyze(existing_stack, industry_cae, employee_count) -> Dict
   - Lógica: para cada sistema existente, BLOQUEAR todos os tools em "blocks"
   - Usa Claude API para sugerir 3-5 ferramentas que:
     * NÃO estão em blocked_tools
     * Complementam stack existente
     * São elegíveis IFIC
     * Têm suporte pt-PT

3. Output do analyze() deve incluir:
   ```python
   {
     "existing_systems": [...],
     "blocked_tools": [...],  # Lista consolidada de proibidos
     "recommended_additions": [...],
     "integration_strategy": str,  # Narrativa de como integrar
     "redundancies_detected": []   # Deve estar vazio se bem feito
   }
   ```

4. Testes CRÍTICOS em tests/unit/test_stack_intelligence.py:
   - test_phc_blocks_monday_com()
   - test_m365_blocks_slack()
   - test_no_redundancies_in_recommendations()
   - test_integration_with_existing_stack()

**Referência**: IFIC_SAAS_CLAUDE_CONFIG.md linhas 275-400

IMPORTANTE: Este agente é o CORE DO DIFERENCIADOR. Testa exaustivamente!

Mostra código + testes. Aguardo revisão antes de FASE 4.
```

---

## 💰 FASE 3 — STACK INTELLIGENCE

**Prompt após revisão**:
```
FASE 3 ✓ — Stack Intelligence funcional com zero redundâncias!

Agora FASE 4 — FINANCIAL ANALYST AGENT:

Objetivo: Parsear IES (Informação Empresarial Simplificada), calcular rácios, projetar ROI realista.

**Tarefas**:

1. Cria agents/financial_analyst.py:
   - class FinancialAnalysisAgent
   - async analyze(ies_docs: List[str], years: List[int], cae: str) -> Dict
   - async _parse_ies_pdf(pdf_path: str) -> Dict
     * Usa Claude API com documento PDF (base64)
     * Extrai: volume_negocios, EBITDA, resultado_liquido, ativo_corrente, passivo_corrente, capital_proprio, fornecimentos_externos
   - _calculate_cagr(values: List[float], periods: int) -> float
   - _project_roi(current_revenue, investment_planned, industry_avg_margin) -> Dict

2. Cálculos chave:
   ```python
   # VAB (Valor Acrescentado Bruto) — crítico para scoring B2
   vab = revenue - external_costs
   
   # Current Ratio
   current_ratio = current_assets / current_liabilities
   
   # ROI projeção (3 cenários)
   conservative: 25-35% (cap at 35%)
   moderate: 35-45% (cap at 45%)
   ambitious: 45-60% (cap at 60%)
   
   # NUNCA >100% ROI — destrói credibilidade
   ```

3. Output structure:
   ```python
   {
     "historical_financials": {
       "2024": {...},
       "2023": {...},
       "2022": {...}
     },
     "growth_trends": {
       "revenue_cagr": float,
       "vab_growth_2y": float
     },
     "ratios": {...},
     "roi_projection": {
       "conservative": float,
       "moderate": float,
       "ambitious": float
     },
     "vab_impact_estimate": {
       "baseline_vab": float,
       "post_ia_vab": float,
       "growth_percent": float
     }
   }
   ```

4. Cria tests/fixtures/ies_2024_mock.pdf (pode ser PDF simples de teste)

5. Testes em tests/unit/test_financial_analyst.py:
   - test_parse_ies_pdf()
   - test_calculate_cagr()
   - test_roi_projection_caps() # Verificar que nunca >60%
   - test_vab_calculation()

**Referência**: IFIC_SAAS_CLAUDE_CONFIG.md linhas 405-530

Mostra código + testes. Aguardo.
```

---

## 🎯 FASE 4 — FINANCIAL ANALYST

**Prompt após revisão**:
```
FASE 4 ✓ — Financial analysis com ROI realista!

Agora FASE 5 — MERIT SCORER AGENT:

Objetivo: Calcular Merit Score (MP) segundo fórmula IFIC e simular cenários.

**Tarefas**:

1. Cria data/regulatory/merit_criteria.json:
   ```json
   {
     "A_quality": {
       "max_score": 5.0,
       "weight": 0.50
     },
     "B1_jobs": {
       "weight": 0.50,
       "sub_weight_in_B": 0.25,
       "thresholds": {
         "0_jobs": 3.0,
         "1_job": 3.8,
         "2_jobs": 4.2,
         "3+_jobs": 5.0
       }
     },
     "B2_market": {
       "weight": 0.50,
       "sub_weight_in_B": 0.25,
       "vab_growth_ranges": {
         "0-5%": 3.2,
         "5-10%": 3.7,
         "10-15%": 4.3,
         "15%+": 4.8
       }
     }
   }
   ```

2. Implementa agents/merit_scorer.py:
   - class MeritScoringAgent
   - _load_merit_criteria() → lê JSON
   - async simulate(base_quality_score, job_creation_range, vab_growth_range, industry_benchmark) -> Dict
   - _calculate_b1(jobs_created: int) -> float
   - _calculate_b2(vab_growth_percent: float) -> float
   - _classify_ranking(mp: float) -> str
     * <3.0: "Inelegível"
     * 3.0-3.5: "Baixo"
     * 3.5-4.0: "Médio"
     * ≥4.0: "Alto" (TARGET)

3. Fórmula EXATA:
   ```python
   MP = 0.50 × A + 0.50 × min(B1, B2)
   
   # Exemplo:
   A = 4.0
   B1 = 4.2 (2 jobs criados)
   B2 = 3.7 (8% VAB growth)
   B = min(4.2, 3.7) = 3.7
   MP = 0.50 × 4.0 + 0.50 × 3.7 = 3.85 (Médio, quase Alto)
   ```

4. simulate() gera matriz de cenários:
   - job_creation_range = [0, 1, 2]
   - vab_growth_range = [0, 5, 8, 12, 15]
   - Calcula MP para todas combinações (15 cenários)
   - Ordena por MP descendente
   - Identifica "recommended" = primeiro com MP ≥ 4.0

5. Usa Claude para gerar _generate_scoring_analysis():
   - Explica por que recommended scenario é ideal
   - Estratégia para atingir job targets
   - Drivers de VAB growth necessários

6. Testes em tests/unit/test_merit_scorer.py:
   - test_mp_formula()
   - test_job_creation_scoring() # B1 = 25% do merit!
   - test_scenario_matrix_generation()
   - test_recommended_has_mp_gte_4()

**Referência**: IFIC_SAAS_CLAUDE_CONFIG.md linhas 535-660

CRÍTICO: Job creation = 25% total merit. Proposta deve SEMPRE incluir plano de criação de empregos!

Mostra código + testes.
```

---

## 📄 FASE 5 — MERIT SCORER

**Prompt após revisão**:
```
FASE 5 ✓ — Merit scoring com cenários otimizados!

Agora FASE 6 — PROPOSAL WRITER AGENT:

Objetivo: Gerar proposta HTML premium (McKinsey-grade) com 6 módulos interativos.

**Tarefas**:

1. Cria templates/proposal_premium.html:
   - Estrutura de 6 módulos:
     1. Dashboard Executivo (badges: Elegível/MP/Incentivo)
     2. Stack Intelligence & Use Cases (3-5 use cases)
     3. Orçamento 3-Tier Interativo (Essencial/Recomendado/Completo)
     4. Merit Score Simulator (input jobs/VAB → output MP)
     5. Cronograma Gantt (fases, marcos)
     6. Checklist SIGA-BF + Copy Map
   
   - CSS embutido:
     * Glassmorphism: `backdrop-filter: blur(10px)`
     * Tipografia: Inter (sans-serif), IBM Plex Serif (headings)
     * Paleta: --primary: #0066CC, --secondary: #00A86B
   
   - JavaScript interativo:
     * showTier(n) → alterna budget tiers
     * recalculateMP() → merit score calculator em tempo real

2. Implementa agents/proposal_writer.py:
   - class ProposalWriterAgent
   - __init__ com Jinja2 setup
   - async generate(template, company, stack, financial, budget_tiers, scoring, regulatory_citations) -> Dict
   - async _generate_use_cases(cae: str, stack: Dict) -> List[Dict]
     * Usa Claude API
     * Prompt: "Gera 3-5 use cases IA para CAE {cae} com stack {stack}"
     * Por cada use case: title, problem, solution, data_requirements, KPIs, ROI_impact
   - _generate_training_plan(dimensao: str) -> Dict
     * Micro: 5 pessoas, 40h
     * Pequena: 15 pessoas, 60h
     * Média: 30 pessoas, 80h
     * Alocação: 4-10% budget (NÃO 47%!)
   - _generate_timeline() -> List[Dict]
     * 4 fases: Preparação (M1-M2), Implementação 1 (M3-M9), Implementação 2 (M10-M18), Consolidação (M19-M24)
   - _export_budget_csv(tiers) -> str
   - _export_timeline_csv(timeline) -> str
   - _export_copy_map_csv(context) -> str

3. Budget Tiers (distribuição realista):
   ```python
   {
     "tier1_essencial": {
       "rh_dedicados": 60000,  # 60-70% total
       "saas_software": 15000,  # 15-20%
       "consultoria": 8000,     # 8-12%
       "formacao": 5000,        # 5-8%
       "equipamentos": 0,
       "roc_cc": 2000,
       "total": 90000
     },
     "tier2_recomendado": {
       "rh_dedicados": 90000,   # 2 FTEs
       "saas_software": 30000,
       "consultoria": 15000,
       "formacao": 10000,
       "equipamentos": 5000,
       "roc_cc": 2500,
       "total": 152500
     }
   }
   ```

4. Testes em tests/unit/test_proposal_writer.py:
   - test_html_generation()
   - test_interactive_tier_selector()
   - test_use_case_generation()
   - test_csv_exports()
   - test_realistic_budget_distribution()

**Referência**: IFIC_SAAS_CLAUDE_CONFIG.md linhas 665-850

Template HTML deve ser VISUALMENTE IMPRESSIONANTE mas funcionalmente sólido.

Mostra template HTML (completo!) + agents/proposal_writer.py.
```

---

## ✅ FASE 6 — PROPOSAL WRITER

**Prompt após revisão**:
```
FASE 6 ✓ — Proposal writer com HTML premium!

Agora FASE 7 — COMPLIANCE VALIDATOR AGENT:

Objetivo: Validar proposta contra frameworks RGPD, DNSH, Duplo Financiamento, Elegibilidade IFIC.

**Tarefas**:

1. Cria data/regulatory/compliance_checklists/rgpd.yaml:
   ```yaml
   name: "RGPD Compliance"
   checks:
     - id: "rgpd_1"
       criterion: "Data handling procedures documented"
       requirement: "Proposal must mention data governance approach"
       severity: "critical"
     
     - id: "rgpd_2"
       criterion: "DPO designated (if >10 employees processing personal data)"
       requirement: "If applicable, must name DPO or plan to designate"
       severity: "high"
     
     - id: "rgpd_3"
       criterion: "User consent mechanisms"
       requirement: "For AI systems processing personal data, consent flows defined"
       severity: "critical"
     
     # Adiciona 5-7 checks total
   ```

2. Similarmente para dnsh.yaml (DNSH = Do No Significant Harm):
   ```yaml
   name: "DNSH Compliance"
   checks:
     - id: "dnsh_1"
       criterion: "Climate change mitigation"
       requirement: "Project must not significantly harm climate goals"
       severity: "critical"
     
     - id: "dnsh_2"
       criterion: "Circular economy"
       requirement: "Equipment disposal/recycling plan if hardware included"
       severity: "medium"
     
     # 6 objectives DNSH total
   ```

3. Implementa agents/compliance_validator.py:
   - class ComplianceValidator
   - _load_checklists() → carrega YAMLs
   - async check(proposal_html: str, company_data: Dict, frameworks: List[str]) -> Dict
   - Para cada framework:
     * Passa proposal_html para Claude API
     * Prompt: "Valida este proposal contra checklist {framework}. Para cada check, retorna: id, status (PASS/WARN/FAIL), evidence (quote relevante), recommendation"
   - Agrega results por framework

4. Output structure:
   ```python
   {
     "overall_status": "PASS",  # ou WARN/FAIL
     "frameworks": {
       "RGPD": {
         "status": "PASS",
         "checks": [
           {
             "id": "rgpd_1",
             "status": "PASS",
             "evidence": "Secção 4.2 menciona governança de dados...",
             "recommendation": null
           },
           ...
         ]
       },
       "DNSH": {...},
       "DuploFinanciamento": {...},
       "IFIC_Eligibility": {...}
     }
   }
   ```

5. Testes em tests/unit/test_compliance_validator.py:
   - test_rgpd_validation_pass()
   - test_rgpd_validation_fail()
   - test_dnsh_compliance()
   - test_aggregated_validation()

**Referência**: IFIC_SAAS_CLAUDE_CONFIG.md linhas 855-950

Este validator é CRÍTICO para evitar rejeições por não-conformidade.

Mostra YAMLs + agents/compliance_validator.py + testes.
```

---

## 🎭 FASE 7 — COMPLIANCE VALIDATOR

**Prompt após revisão**:
```
FASE 7 ✓ — Compliance validator robusto!

Agora FASE 8 — ORCHESTRATOR COMPLETO (INTEGRAÇÃO FINAL):

Objetivo: Juntar todos os 6 agentes num pipeline coerente end-to-end.

**Tarefas**:

1. Completa agents/orchestrator.py:
   - Método process_application() deve:
     * Phase 1: CompanyResearchAgent.fetch()
     * Phase 2: StackIntelligenceAgent.analyze()
     * Phase 3: _validate_budget_gate() (BLOQUEANTE se falhar)
     * Phase 4: _calculate_tiers() (3 tiers)
     * Phase 5: FinancialAnalysisAgent.analyze()
     * Phase 6: MeritScoringAgent.simulate()
     * Phase 7: ProposalWriterAgent.generate()
     * Phase 8: ComplianceValidator.check()
   
   - Cada fase passa output para a próxima
   - Logging detalhado em cada fase
   - Timing de cada fase (métricas)

2. Implementa _validate_budget_gate():
   ```python
   def _validate_budget_gate(self, teto_max, cofinanciamento, elegiveis_target):
       errors = []
       
       if elegiveis_target < 5000:
           errors.append("Investimento elegível mínimo: €5.000 [Aviso art.6]")
       
       if elegiveis_target > teto_max:
           errors.append(f"Elegíveis €{elegiveis_target} > Teto €{teto_max}")
       
       min_cofin = elegiveis_target * 0.25
       if cofinanciamento < min_cofin:
           errors.append(f"Cofinanciamento mínimo: €{min_cofin:.2f}")
       
       if errors:
           return {"valid": False, "message": "\n".join(errors)}
       
       return {"valid": True}
   ```

3. Implementa _calculate_tiers():
   ```python
   def _calculate_tiers(self, teto, distribution_prefs):
       # Tier 1: Essencial (60-80% do teto)
       tier1 = self._build_tier(teto * 0.70, distribution_prefs)
       
       # Tier 2: Recomendado (85-95% do teto)
       tier2 = self._build_tier(teto * 0.90, distribution_prefs)
       
       # Tier 3: Completo (95-100% do teto)
       tier3 = self._build_tier(teto * 0.98, distribution_prefs)
       
       return {"tier1": tier1, "tier2": tier2, "tier3": tier3}
   
   def _build_tier(self, total, prefs):
       # Default distribution (ajustável por prefs)
       return {
           "rh_dedicados": total * 0.65,
           "saas_software": total * 0.20,
           "consultoria": total * 0.10,
           "formacao": total * 0.05,
           "equipamentos": 0,
           "roc_cc": min(2500, total * 0.02),
           "total": total
       }
   ```

4. Audit Trail:
   ```python
   def _generate_audit_trail(self):
       return {
           "session_id": str(uuid.uuid4()),
           "timestamp": datetime.now().isoformat(),
           "sources": [
               # Agregado de todos os agents
           ],
           "processing_time": self.processing_time,
           "agent_versions": {
               "researcher": "1.0",
               "stack_intel": "1.0",
               ...
           }
       }
   ```

5. TESTE CRÍTICO: tests/integration/test_full_pipeline.py:
   ```python
   @pytest.mark.asyncio
   async def test_end_to_end_micro_company():
       orchestrator = IFICOrchestrator(api_key=os.getenv("CLAUDE_API_KEY"))
       
       mock_input = {
           "nome": "InnovaSolutions Lda",
           "nif": "123456789",
           "cae": "62010",
           "teto_max": 80000,
           "cofinanciamento": 20000,
           "ies_files": ["tests/fixtures/ies_2024_mock.pdf"]
       }
       
       result = await orchestrator.process_application(
           company_input=mock_input,
           regulatory_docs=["data/regulatory/portaria_286_2025.json"]
       )
       
       # Assertions críticas
       assert result["validation"]["status"] == "PASS"
       assert result["metrics"]["merit_score"] >= 3.0
       assert result["metrics"]["merit_score"] <= 5.0
       assert result["metrics"]["roi_estimated"] < 100  # Realista!
       assert len(result["artifacts"]["html"]) > 10000
       assert "<h1>" in result["artifacts"]["html"]  # Valid HTML
       assert len(result["stack_analysis"]["redundancies_detected"]) == 0
       assert "€" in result["artifacts"]["budget_csv"]
       assert result["metrics"]["processing_time_seconds"] < 180  # <3 min
   ```

6. Testes adicionais:
   - test_budget_gate_blocks_invalid()
   - test_tier_calculation()
   - test_audit_trail_generation()

**Referência**: IFIC_SAAS_CLAUDE_CONFIG.md linhas 95-160

Este é o CORE DO SISTEMA. Testa exaustivamente antes de avançar para API/Frontend.

Mostra orchestrator.py completo + teste de integração. Aguardo revisão detalhada.
```

---

## 🌐 FASE 8 — ORCHESTRATOR COMPLETO

**Prompt após revisão e testes passing**:
```
FASES 1-8 COMPLETAS! 🎉

Core agents funcionais:
✅ Orchestrator com pipeline completo
✅ Company Research com eInforma mock
✅ Stack Intelligence (zero redundâncias)
✅ Financial Analysis (ROI realista)
✅ Merit Scorer (MP ≥4.0 target)
✅ Proposal Writer (HTML premium)
✅ Compliance Validator (RGPD/DNSH)

Agora CAMADA WEB — FASES 9-12 (Backend API + Frontend + Database + Deployment):

**FASE 9 — FastAPI Backend**:

1. Cria api/main.py:
   ```python
   from fastapi import FastAPI, UploadFile, File, HTTPException
   from typing import List
   
   app = FastAPI(title="FundAI API", version="1.0")
   
   @app.post("/applications")
   async def create_application(
       company_name: str,
       nif: str = None,
       teto_max: float,
       cofinanciamento: float,
       ies_files: List[UploadFile] = File(None)
   ):
       """
       Create new IFIC application.
       Triggers full orchestrator pipeline.
       Returns application_id + proposal URLs.
       """
       # Implementação
   
   @app.get("/applications/{application_id}/proposal.html")
   async def get_proposal_html(application_id: str):
       """Retrieve generated proposal HTML"""
       # Fetch from DB
   
   @app.get("/applications/{application_id}/budget.csv")
   async def get_budget_csv(application_id: str):
       """Download budget CSV"""
       # Fetch from DB
   
   @app.post("/research/company")
   async def research_company(nif: str = None, nome: str = None):
       """Standalone company research (pre-sales tool)"""
       # Just run CompanyResearchAgent
   ```

2. Cria api/models/:
   - company.py (Pydantic models para request/response)
   - proposal.py
   - validation.py

3. Integra com Orchestrator:
   ```python
   orchestrator = IFICOrchestrator(api_key=os.getenv("CLAUDE_API_KEY"))
   result = await orchestrator.process_application(...)
   application_id = save_to_database(result)
   return {"application_id": application_id, "status": "completed", ...}
   ```

4. Testes API em tests/api/test_endpoints.py:
   - test_create_application_success()
   - test_create_application_invalid_budget()
   - test_get_proposal_html()

**Referência**: IFIC_SAAS_CLAUDE_CONFIG.md linhas 980-1050

Mostra api/main.py + models + testes.
```

---

## 🗄️ FASE 9 — FASTAPI BACKEND

**Prompt após revisão**:
```
FASE 9 ✓ — API funcional!

Agora FASE 10 — DATABASE:

**Tarefas**:

1. Cria database/models.py (SQLAlchemy ORM):
   ```python
   from sqlalchemy import Column, String, Float, JSON, DateTime, ForeignKey
   from sqlalchemy.dialects.postgresql import UUID
   import uuid
   
   class Company(Base):
       __tablename__ = "companies"
       
       id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
       nome_legal = Column(String(255), nullable=False)
       nif = Column(String(9), unique=True, nullable=False)
       cae = Column(String(5))
       nuts_ii = Column(String(4))
       dimensao = Column(String(20))
       tech_stack = Column(JSON)
       created_at = Column(DateTime, default=func.now())
   
   class Application(Base):
       __tablename__ = "applications"
       
       id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
       company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id"))
       status = Column(String(50))  # draft/processing/completed/submitted
       teto_max = Column(Float)
       cofinanciamento = Column(Float)
       merit_score = Column(Float)
       proposal_html = Column(Text)
       budget_csv = Column(Text)
       timeline_csv = Column(Text)
       audit_trail = Column(JSON)
       created_at = Column(DateTime, default=func.now())
       updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
   
   # Mais tabelas: use_cases, validations
   ```

2. Setup Alembic para migrations:
   ```bash
   alembic init database/migrations
   alembic revision --autogenerate -m "Initial schema"
   alembic upgrade head
   ```

3. Cria database/seeds/test_companies.sql:
   ```sql
   INSERT INTO companies (nome_legal, nif, cae, nuts_ii, dimensao, tech_stack)
   VALUES 
     ('InnovaSolutions Lda', '123456789', '62010', 'PT17', 'pequena', 
      '["Microsoft 365", "PHC"]'::jsonb),
     ('TechStartup SA', '987654321', '62020', 'PT11', 'micro', 
      '["Notion", "Stripe"]'::jsonb);
   ```

4. Integra DB em api/main.py:
   ```python
   from database.models import Company, Application
   from sqlalchemy.orm import Session
   
   def save_to_database(result: Dict, session: Session) -> str:
       company = Company(...)
       session.add(company)
       
       application = Application(
           company_id=company.id,
           proposal_html=result["artifacts"]["html"],
           ...
       )
       session.add(application)
       session.commit()
       
       return str(application.id)
   ```

5. Testes em tests/database/test_models.py:
   - test_company_creation()
   - test_application_creation()
   - test_relationships()

**Referência**: IFIC_SAAS_CLAUDE_CONFIG.md linhas 1055-1090

Mostra models.py + migrations + integração com API.
```

---

## 🎨 FASE 10 — DATABASE

**Prompt após revisão**:
```
FASE 10 ✓ — Database setup completo!

Agora FASE 11 — REACT FRONTEND:

**Tarefas**:

1. Setup React project:
   ```bash
   cd web/
   npx create-react-app . --template typescript
   npm install axios react-router-dom @types/react-router-dom
   npm install -D tailwindcss postcss autoprefixer
   npx tailwindcss init -p
   ```

2. Estrutura de páginas em web/src/pages/:
   - Dashboard.tsx (lista applications)
   - ApplicationForm.tsx (multi-step form)
   - ProposalView.tsx (display generated proposal)

3. ApplicationForm.tsx (multi-step):
   ```tsx
   import React, { useState } from 'react';
   
   export const ApplicationForm: React.FC = () => {
       const [step, setStep] = useState(1);
       const [formData, setFormData] = useState({
           companyName: '',
           nif: '',
           tetoMax: 0,
           cofinanciamento: 0,
           iesFiles: []
       });
       
       const handleSubmit = async () => {
           const formDataObj = new FormData();
           formDataObj.append('company_name', formData.companyName);
           formDataObj.append('nif', formData.nif);
           formDataObj.append('teto_max', formData.tetoMax.toString());
           formDataObj.append('cofinanciamento', formData.cofinanciamento.toString());
           
           formData.iesFiles.forEach(file => {
               formDataObj.append('ies_files', file);
           });
           
           const response = await fetch('http://localhost:8000/applications', {
               method: 'POST',
               body: formDataObj
           });
           
           const result = await response.json();
           window.location.href = `/applications/${result.application_id}`;
       };
       
       return (
           <div className="max-w-4xl mx-auto p-6">
               <h1 className="text-3xl font-serif mb-6">Nova Candidatura IFIC</h1>
               
               {step === 1 && <Step1_CompanyInfo data={formData} setData={setFormData} />}
               {step === 2 && <Step2_BudgetGate data={formData} setData={setFormData} />}
               {step === 3 && <Step3_FinancialDocs data={formData} setData={setFormData} />}
               {step === 4 && <Step4_Review data={formData} />}
               
               <div className="flex justify-between mt-8">
                   {step > 1 && <button onClick={() => setStep(step - 1)}>Anterior</button>}
                   {step < 4 && <button onClick={() => setStep(step + 1)}>Próximo</button>}
                   {step === 4 && <button onClick={handleSubmit}>Gerar Proposta</button>}
               </div>
           </div>
       );
   };
   ```

4. Componentes reutilizáveis em web/src/components/:
   - BudgetTierSelector.tsx (3 buttons: Essencial/Recomendado/Completo)
   - MeritScoreSimulator.tsx (inputs: jobs, VAB → output: MP)
   - StackAnalyzer.tsx (display existing + recommendations)

5. Styling com Tailwind:
   ```css
   /* tailwind.config.js */
   module.exports = {
     theme: {
       extend: {
         fontFamily: {
           sans: ['Inter', 'sans-serif'],
           serif: ['IBM Plex Serif', 'serif']
         },
         colors: {
           primary: '#0066CC',
           secondary: '#00A86B'
         }
       }
     }
   }
   ```

6. ProposalView.tsx:
   ```tsx
   export const ProposalView: React.FC<{applicationId: string}> = ({applicationId}) => {
       const [proposalHtml, setProposalHtml] = useState('');
       
       useEffect(() => {
           fetch(`http://localhost:8000/applications/${applicationId}/proposal.html`)
               .then(res => res.text())
               .then(html => setProposalHtml(html));
       }, [applicationId]);
       
       return (
           <div className="container mx-auto">
               <div dangerouslySetInnerHTML={{__html: proposalHtml}} />
               
               <div className="flex gap-4 mt-8">
                   <a href={`/api/applications/${applicationId}/budget.csv`} download>
                       Download Budget CSV
                   </a>
                   <a href={`/api/applications/${applicationId}/timeline.csv`} download>
                       Download Timeline CSV
                   </a>
               </div>
           </div>
       );
   };
   ```

**Referência**: IFIC_SAAS_CLAUDE_CONFIG.md linhas 1095-1180

Mostra ApplicationForm.tsx + componentes + ProposalView.tsx.
```

---

## 🐳 FASE 11 — REACT FRONTEND

**Prompt após revisão**:
```
FASE 11 ✓ — Frontend React funcional!

Agora FASE 12 FINAL — DEPLOYMENT:

**Tarefas**:

1. Cria Dockerfile para API:
   ```dockerfile
   FROM python:3.11-slim
   
   WORKDIR /app
   
   COPY requirements.txt .
   RUN pip install --no-cache-dir -r requirements.txt
   
   COPY . .
   
   CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
   ```

2. docker-compose.yml completo:
   ```yaml
   version: '3.8'
   
   services:
     api:
       build: .
       ports:
         - "8000:8000"
       environment:
         - CLAUDE_API_KEY=${CLAUDE_API_KEY}
         - DATABASE_URL=postgresql://fundai:password@db:5432/fundai
       depends_on:
         - db
       volumes:
         - ./data:/app/data
         - ./templates:/app/templates
     
     db:
       image: postgres:15
       environment:
         - POSTGRES_DB=fundai
         - POSTGRES_USER=fundai
         - POSTGRES_PASSWORD=password
       volumes:
         - pgdata:/var/lib/postgresql/data
       ports:
         - "5432:5432"
     
     web:
       build: ./web
       ports:
         - "3000:3000"
       depends_on:
         - api
       environment:
         - REACT_APP_API_URL=http://localhost:8000
   
   volumes:
     pgdata:
   ```

3. .env.example:
   ```
   CLAUDE_API_KEY=sk-ant-...
   DATABASE_URL=postgresql://fundai:password@localhost:5432/fundai
   ENVIRONMENT=development
   LOG_LEVEL=INFO
   ```

4. README.md deployment:
   ```markdown
   # FundAI — Deployment Guide
   
   ## Prerequisites
   - Docker & Docker Compose
   - Claude API key (Anthropic)
   
   ## Setup
   1. Clone repo
   2. Copy `.env.example` to `.env` and fill CLAUDE_API_KEY
   3. Run: `docker-compose up --build`
   4. Access:
      - API: http://localhost:8000
      - Frontend: http://localhost:3000
      - API Docs: http://localhost:8000/docs
   
   ## Testing
   ```bash
   # Unit tests
   pytest tests/unit/
   
   # Integration tests
   pytest tests/integration/
   
   # API tests
   pytest tests/api/
   ```
   
   ## Production Deployment
   - Use environment variables for secrets
   - Enable HTTPS (Traefik/Caddy)
   - Setup monitoring (Prometheus + Grafana)
   - Configure backups (PostgreSQL)
   ```

5. Health check endpoint:
   ```python
   @app.get("/health")
   async def health_check():
       return {
           "status": "healthy",
           "version": "1.0",
           "agents": {
               "orchestrator": "ok",
               "researcher": "ok",
               "stack_intel": "ok",
               "financial": "ok",
               "scorer": "ok",
               "writer": "ok",
               "validator": "ok"
           }
       }
   ```

6. Teste deployment:
   ```bash
   docker-compose up --build
   
   # Em outro terminal:
   curl http://localhost:8000/health
   # Deve retornar {"status": "healthy", ...}
   
   # Teste create application:
   curl -X POST http://localhost:8000/applications \
     -F "company_name=Test Company" \
     -F "nif=123456789" \
     -F "teto_max=80000" \
     -F "cofinanciamento=20000"
   
   # Deve retornar application_id
   ```

**Referência**: IFIC_SAAS_CLAUDE_CONFIG.md linhas 1185-1250

Mostra Dockerfile + docker-compose.yml + README.md + teste de deployment.

APÓS ISTO, MVP ESTÁ COMPLETO! 🎉
```

---

## 🎉 CHECKLIST FINAL DE VALIDAÇÃO

**Use este checklist antes de considerar MVP pronto**:

```
[ ] `docker-compose up` funciona sem erros
[ ] Health check endpoint responde 200 OK
[ ] Frontend carrega em http://localhost:3000
[ ] API docs acessível em http://localhost:8000/docs
[ ] Criar application via frontend funciona
[ ] Proposal HTML gerado é válido e visualmente correto
[ ] CSVs exportam com dados corretos
[ ] Testes unitários: 100% pass (pytest tests/unit/)
[ ] Testes integração: 100% pass (pytest tests/integration/)
[ ] Testes API: 100% pass (pytest tests/api/)
[ ] Stack Intelligence: PHC NÃO sugere Monday.com ✓
[ ] Stack Intelligence: M365 NÃO sugere Slack ✓
[ ] Merit Score: MP ≥ 3.0 para todas propostas
[ ] Merit Score: Job creation refletido em B1 corretamente
[ ] ROI projection: Sempre <100% (caps funcionando)
[ ] Budget distribution: RH 60-70%, Formação ≤15%
[ ] Compliance: RGPD checks PASS
[ ] Compliance: DNSH checks PASS
[ ] Proposal HTML: 6 módulos presentes
[ ] Proposal HTML: Elementos interativos funcionam (tier selector, MP calculator)
[ ] Database migrations: Aplicam sem erros
[ ] Logs: Detalhados em cada fase do orchestrator
[ ] Processing time: <3 minutos end-to-end
```

---

## 📞 AJUDA & DEBUG

Se Claude Code encontrar problemas:

1. **Erro de import**: Verifica requirements.txt tem todas as dependências
2. **Teste falhando**: Mostra stack trace completo para debug
3. **Claude API timeout**: Aumenta max_tokens ou divide prompt
4. **Database connection**: Verifica docker-compose db service está running
5. **Frontend não carrega**: Check REACT_APP_API_URL em .env

Para qualquer ambiguidade nas specs, consultar **IFIC_SAAS_CLAUDE_CONFIG.md** como fonte de verdade.

---

**FIM DOS PROMPTS** 🚀

Copy-paste sequencialmente para Claude Code. Sucesso na implementação!

**Bilal @ AiParaTi | 2025-11-01**
