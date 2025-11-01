# 🚀 QUICK START — Para Claude Code

## 📋 INSTRUÇÕES DE IMPLEMENTAÇÃO

**Passo 1**: Copia o ficheiro `IFIC_SAAS_CLAUDE_CONFIG.md` para o Claude Code

**Passo 2**: Usa este prompt inicial:

```
Olá! Vou construir o FundAI — um SaaS para automatizar candidaturas IFIC (fundos PT2030).

Li a configuração completa em IFIC_SAAS_CLAUDE_CONFIG.md.

Por favor, começa pela FASE 1 — FOUNDATION:

1. Cria a estrutura de pastas completa do projeto conforme especificado
2. Inicializa o ambiente Python com requirements.txt
3. Configura o projeto base (pyproject.toml, .env.example, docker-compose.yml)
4. Cria o skeleton do Orchestrator em agents/orchestrator.py
5. Implementa a classe base para todos os agentes com logging comum

Depois de cada passo, mostra-me o código criado e espera pela minha confirmação antes de avançar.

IMPORTANTE: 
- Segue religiosamente as especificações do IFIC_SAAS_CLAUDE_CONFIG.md
- Usa type hints em todo o código Python
- Adiciona docstrings completas (Google style)
- Cria testes unitários para cada componente
```

---

## 🎯 FASES DE IMPLEMENTAÇÃO (Ordem Sequencial)

### FASE 1: FOUNDATION (Semana 1)
✅ Estrutura de pastas  
✅ Requirements & environment setup  
✅ Orchestrator skeleton  
✅ Base agent classes  
✅ Logging & monitoring setup  

**Prompt para Claude Code**:
```
FASE 1 completa. Agora implementa a FASE 2 — COMPANY RESEARCH AGENT:

1. Cria agents/researcher.py com a classe CompanyResearchAgent
2. Implementa método fetch() com prioridade eInforma → Racius → Website
3. Por agora, usa MOCK para eInforma (cria fixtures/mock_einforma.json)
4. Implementa _detect_stack_from_website() usando Claude API com web_fetch
5. Adiciona _infer_nuts_ii() com mapeamento de cidades
6. Cria testes em tests/unit/test_researcher.py

Mostra-me o código e aguarda confirmação.
```

### FASE 2: COMPANY RESEARCH AGENT (Semana 1)
✅ CompanyResearchAgent  
✅ eInforma mock integration  
✅ NUTS II inference  
✅ Tech stack detection from website  
✅ Unit tests  

**Prompt para Claude Code**:
```
FASE 2 OK. Avança para FASE 3 — STACK INTELLIGENCE:

1. Cria mcp_servers/stack_detector_mcp/rules.yaml com redundancy rules
2. Implementa agents/stack_intelligence.py com StackIntelligenceAgent
3. Método analyze() deve detectar conflitos (ex: PHC bloqueia Monday.com)
4. Usa Claude API para sugerir ferramentas complementares (não redundantes)
5. Gera integration_strategy narrative
6. Testes críticos: test_phc_blocks_mondaycom(), test_m365_blocks_slack()

Aguardo código.
```

### FASE 3: STACK INTELLIGENCE (Semana 2)
✅ StackIntelligenceAgent  
✅ Redundancy rules database  
✅ Integration strategy generator  
✅ Critical unit tests (PHC/M365 scenarios)  

**Prompt para Claude Code**:
```
FASE 3 ✓. Agora FASE 4 — FINANCIAL ANALYST:

1. Cria agents/financial_analyst.py com FinancialAnalysisAgent
2. Implementa _parse_ies_pdf() usando Claude API com documento PDF
3. Calcula ratios: CAGR, current ratio, ROE, debt-to-equity
4. Calcula VAB (Valor Acrescentado Bruto) = Revenue - External Costs
5. Projeta ROI em 3 cenários: conservative (25-35%), moderate (35-45%), ambitious (45-60%)
6. Adiciona testes com fixtures/ies_2024_mock.pdf

Mostra código e espera confirmação.
```

### FASE 4: FINANCIAL ANALYST (Semana 2)
✅ FinancialAnalysisAgent  
✅ IES PDF parsing  
✅ Financial ratios calculation  
✅ VAB calculation (critical for B2 scoring)  
✅ Realistic ROI projection (capped at 60%)  

**Prompt para Claude Code**:
```
FASE 4 completa. FASE 5 — MERIT SCORER:

1. Cria data/regulatory/merit_criteria.json com grids A/B1/B2
2. Implementa agents/merit_scorer.py com MeritScoringAgent
3. Método simulate() gera cenários com job_creation × vab_growth
4. Fórmula: MP = 0.50×A + 0.50×min(B1, B2)
5. CRÍTICO: Job creation = 25% do total merit (B1)
6. Classifica ranking: <3.0 Inelegível, 3.0-3.5 Baixo, 3.5-4.0 Médio, ≥4.0 Alto
7. Testes: test_job_creation_impact(), test_mp_formula()

Código please.
```

### FASE 5: MERIT SCORER (Semana 3)
✅ MeritScoringAgent  
✅ Regulatory criteria database  
✅ Scenario simulator (job × VAB matrix)  
✅ MP calculation with correct formula  
✅ Ranking classifier  

**Prompt para Claude Code**:
```
FASE 5 ✓. Avança FASE 6 — PROPOSAL WRITER:

1. Cria templates/proposal_premium.html com estrutura de 6 módulos
2. CSS glassmorphism embedded (Inter + IBM Plex Serif fonts)
3. JavaScript para tier selector e merit score calculator interativo
4. Implementa agents/proposal_writer.py com ProposalWriterAgent
5. Método generate() usa Jinja2 para render template
6. _generate_use_cases() usa Claude para criar 3-5 use cases por indústria
7. Exporta CSVs: budget, timeline, copy_map
8. Testes: test_html_generation(), test_interactive_elements()

Mostra template HTML e agent code.
```

### FASE 6: PROPOSAL WRITER (Semana 3-4)
✅ Premium HTML template (6 modules)  
✅ Glassmorphism CSS + typography  
✅ Interactive elements (tier selector, MP calculator)  
✅ ProposalWriterAgent with Jinja2  
✅ Use case generator (Claude-powered)  
✅ CSV exporters  

**Prompt para Claude Code**:
```
FASE 6 OK. FASE 7 — COMPLIANCE VALIDATOR:

1. Cria data/regulatory/compliance_checklists/ (rgpd.yaml, dnsh.yaml)
2. Implementa agents/compliance_validator.py com ComplianceValidator
3. Método check() valida contra 4 frameworks: RGPD, DNSH, DuploFinanciamento, IFIC_Eligibility
4. Para cada framework, retorna status (PASS/WARN/FAIL) + details
5. RGPD: verifica se proposta menciona data handling, consent, DPO
6. DNSH: valida "Do No Significant Harm" principles
7. Testes: test_rgpd_validation(), test_dnsh_compliance()

Aguardo código.
```

### FASE 7: COMPLIANCE VALIDATOR (Semana 4)
✅ ComplianceValidator agent  
✅ Regulatory checklists (YAML)  
✅ Multi-framework validation  
✅ RGPD + DNSH checks  
✅ Validation reporting  

**Prompt para Claude Code**:
```
FASE 7 ✓. Integração FASE 8 — ORCHESTRATOR COMPLETO:

1. Completa agents/orchestrator.py com pipeline full:
   - Phase 1: Research
   - Phase 2: Stack Intelligence
   - Phase 3: Budget Gate validation
   - Phase 4: Financial Analysis
   - Phase 5: Merit Scoring
   - Phase 6: Proposal Generation
   - Phase 7: Compliance Validation
2. Implementa _validate_budget_gate() com todas as regras
3. _calculate_tiers() com distribuição realista (60-70% RH)
4. Gera audit_trail completo com session_id, timestamps, sources
5. TESTE CRÍTICO: tests/integration/test_full_pipeline.py
   - Mock company input
   - Valida output completo (HTML + CSVs + validation)
   - Assert merit_score ≥ 3.0, ROI < 100%, zero redundancies

Mostra código da integração.
```

### FASE 8: FULL ORCHESTRATOR (Semana 4)
✅ Complete pipeline integration  
✅ Budget gate with all validations  
✅ 3-tier budget calculator  
✅ Audit trail generation  
✅ End-to-end integration test  

---

## 🌐 FASES 9-12: API & FRONTEND (Semanas 5-6)

**Prompt consolidado para Claude Code**:
```
Fases 1-8 completas — core agents funcionais!

Agora implementa CAMADA API & WEB:

FASE 9 — FastAPI Backend:
1. Cria api/main.py com FastAPI app
2. Endpoints: POST /applications, GET /applications/{id}/proposal.html
3. Integra com Orchestrator
4. Implementa database/models.py (SQLAlchemy ORM)
5. Alembic migrations setup
6. Testes API: test_create_application_endpoint()

FASE 10 — React Frontend:
1. Scaffold web/ com Create React App + TypeScript
2. Páginas: Dashboard.tsx, ApplicationForm.tsx (multi-step), ProposalView.tsx
3. Componentes: BudgetTierSelector.tsx, MeritScoreSimulator.tsx
4. Integração com API backend
5. Styling com Tailwind CSS

FASE 11 — Database:
1. PostgreSQL schema implementation
2. Seed data (test companies)
3. Migrations para prod
4. Backup strategy

FASE 12 — Deployment:
1. Dockerfile para API
2. docker-compose.yml completo (api + db + web)
3. .env.example com todas as vars
4. README.md deployment instructions

Mostra código por fase, aguardo confirmações.
```

---

## ✅ CHECKLIST DE VALIDAÇÃO FINAL

Antes de considerar MVP pronto:

```
[ ] Orchestrator processa candidatura end-to-end em <3 minutos
[ ] Zero sugestões redundantes (PHC não gera Monday.com, M365 não gera Slack)
[ ] Merit score médio ≥ 4.0 em testes
[ ] ROI projection realista (30-50% range)
[ ] HTML proposal tem 6 módulos + elementos interativos
[ ] CSVs exportam corretamente
[ ] Compliance validator PASS em RGPD + DNSH
[ ] API responde em <5s para criação de application
[ ] Frontend permite upload IES files
[ ] Docker compose up funciona out-of-the-box
[ ] Testes passam 100% (unit + integration)
[ ] Documentação API completa (OpenAPI/Swagger)
```

---

## 🎯 APÓS MVP — FASE 13+ (Semanas 7-8)

```
FASE 13 — Real Integrations:
- eInforma API real (substituir mock)
- Racius scraper (Playwright)
- MCP servers em produção

FASE 14 — Advanced Features:
- Multi-language support (EN além de PT)
- PDF export da proposta
- Email notifications
- Payment integration (Stripe)

FASE 15 — Beta Launch:
- 3-5 clientes piloto
- Feedback loop
- Pricing validation
- Marketing materials (landing page)

FASE 16 — Scale & Optimization:
- Caching layer (Redis)
- Background jobs (Celery)
- Monitoring (Prometheus + Grafana)
- CI/CD pipeline (GitHub Actions)
```

---

## 📞 SUPORTE

Se Claude Code tiver dúvidas ou encontrar ambiguidades:

1. **Consulta sempre** `IFIC_SAAS_CLAUDE_CONFIG.md` como fonte de verdade
2. **Pergunta** antes de fazer assumptions sobre business logic
3. **Mostra código** antes de implementar features grandes
4. **Testa incrementalmente** — não avances sem testes passing

---

## 🎉 RESULTADO ESPERADO

Após implementação completa:

✅ **SaaS funcional** para candidaturas IFIC  
✅ **80% automação** do processo manual  
✅ **<3 dias turnaround** vs 2-3 semanas  
✅ **>70% approval rate** com merit scores 4.0+  
✅ **Zero redundâncias** tecnológicas (diferenciador chave)  
✅ **€150k ARR potential** em Year 1  

---

**READY TO BUILD?** 🚀

Copia este ficheiro + `IFIC_SAAS_CLAUDE_CONFIG.md` para Claude Code e começa pela FASE 1!

---

**Bilal @ AiParaTi**  
**2025-11-01**  
**Version**: 1.0 (Quick Start)
