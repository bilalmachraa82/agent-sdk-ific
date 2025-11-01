# IFIC SAAS — Claude Code Master Configuration
**Project**: FundAI - AI Agent para Candidaturas IFIC (PT2030)  
**Owner**: AiParaTi (Bilal)  
**Target**: MVP Q1 2026 | Piloto Q2 2026 | €150k ARR Q4 2026  
**Stack**: Python 3.11+ | FastAPI | PostgreSQL | Claude API | React  

---

## 🎯 PROJECT MISSION

Automatizar candidaturas ao Aviso IFIC 03/C05-i14.01/2025 ("IA nas PME") com:
- **Taxa aprovação >70%** (vs 30-40% DIY)
- **Tempo <3 dias** (vs 2-3 semanas manual)
- **Merit Score médio ≥4.0** (competitivo)
- **Stack Intelligence** (zero redundâncias tecnológicas)

**Core Differentiator**: Inteligência de stack existente — nunca sugerir Monday.com a quem usa PHC, nem Slack a quem tem M365.

---

## 📁 PROJECT STRUCTURE

```
fundai/
├── .claude/
│   └── instructions.md              # Este ficheiro
├── agents/
│   ├── __init__.py
│   ├── orchestrator.py              # Main multi-agent controller
│   ├── researcher.py                # eInforma/Racius/web scraping
│   ├── stack_intelligence.py        # Tech stack detection + redundancy rules
│   ├── financial_analyst.py         # IES parsing, ratio calculations
│   ├── proposal_writer.py           # HTML/CSV generation (6 modules)
│   ├── merit_scorer.py              # MP calculation + scenario simulator
│   └── compliance_validator.py      # RGPD/DNSH/double-funding checks
├── mcp_servers/
│   ├── einforma_mcp/
│   │   ├── server.py                # MCP for eInforma API
│   │   └── parsers.py
│   ├── racius_mcp/
│   │   └── server.py
│   ├── stack_detector_mcp/
│   │   ├── server.py
│   │   └── rules.yaml               # Redundancy rules DB
│   └── siga_bf_mcp/
│       ├── server.py
│       └── field_mappings.json      # SIGA-BF copy map
├── templates/
│   ├── proposal_premium.html        # 6-module McKinsey-grade template
│   ├── budget_simulator.html        # Interactive 3-tier calculator
│   ├── merit_scorer.html            # MP scenario simulator
│   └── styles/
│       ├── glassmorphism.css
│       └── typography.css           # Inter + IBM Plex Serif
├── data/
│   ├── regulatory/
│   │   ├── portaria_286_2025.json   # Parsed rules
│   │   ├── ific_thresholds.yaml
│   │   └── merit_criteria.json      # A/B1/B2 scoring grids
│   ├── market/
│   │   ├── saas_pricing_oct2025.csv # Current pricing (Claude/ChatGPT/etc)
│   │   └── erp_compatibility.json   # PHC/SAP/Sage integrations
│   └── companies/
│       └── .gitkeep                 # Client data (not in git)
├── api/
│   ├── main.py                      # FastAPI entry point
│   ├── routes/
│   │   ├── applications.py          # POST /applications, GET /applications/{id}
│   │   ├── research.py              # GET /research/{nif}
│   │   └── proposals.py             # POST /proposals/generate
│   └── models/
│       ├── company.py               # Pydantic models
│       ├── proposal.py
│       └── validation.py
├── database/
│   ├── models.py                    # SQLAlchemy ORM
│   ├── migrations/                  # Alembic
│   └── seeds/
│       └── test_companies.sql
├── web/
│   ├── package.json
│   ├── src/
│   │   ├── App.tsx
│   │   ├── pages/
│   │   │   ├── Dashboard.tsx
│   │   │   ├── ApplicationForm.tsx  # Multi-step questionnaire
│   │   │   └── ProposalView.tsx
│   │   └── components/
│   │       ├── BudgetTierSelector.tsx
│   │       ├── MeritScoreSimulator.tsx
│   │       └── StackAnalyzer.tsx
│   └── public/
├── scripts/
│   ├── scrape_einforma.py           # Dev tool (respect ToS)
│   ├── update_pricing.py            # Monthly job
│   └── seed_db.py
├── tests/
│   ├── unit/
│   │   ├── test_stack_intelligence.py
│   │   ├── test_merit_scorer.py
│   │   └── test_budget_calculator.py
│   ├── integration/
│   │   └── test_full_pipeline.py
│   └── fixtures/
│       ├── mock_einforma.json
│       └── golden_proposal.html     # Reference output
├── docs/
│   ├── API.md
│   ├── REGULATORY_COMPLIANCE.md     # IFIC rules summary
│   └── DEPLOYMENT.md
├── .env.example
├── docker-compose.yml
├── requirements.txt
├── pyproject.toml
└── README.md
```

---

## 🧠 AGENT ARCHITECTURE (Detailed Specs)

### 1. Orchestrator (`agents/orchestrator.py`)

**Responsibility**: Coordena todo o pipeline de candidatura.

```python
from anthropic import Anthropic
from typing import Dict, List
import asyncio

class IFICOrchestrator:
    """
    Main controller for IFIC application processing.
    Coordinates 6 specialized subagents in sequence.
    """
    
    def __init__(self, claude_api_key: str):
        self.client = Anthropic(api_key=claude_api_key)
        self.subagents = {
            "researcher": CompanyResearchAgent(self.client),
            "stack_intel": StackIntelligenceAgent(self.client),
            "financial": FinancialAnalysisAgent(self.client),
            "writer": ProposalWriterAgent(self.client),
            "scorer": MeritScoringAgent(self.client),
            "validator": ComplianceValidator(self.client)
        }
        
    async def process_application(
        self,
        company_input: Dict,
        regulatory_docs: List[str]
    ) -> Dict:
        """
        Full pipeline:
        1. Company research (eInforma → Racius → website)
        2. Stack intelligence (detect existing tech)
        3. Budget gate validation
        4. Financial deep dive (IES analysis)
        5. Merit scoring simulation
        6. Proposal generation (HTML + CSVs)
        7. Compliance validation (RGPD/DNSH)
        
        Returns:
            {
                "artifacts": {
                    "html": str,
                    "budget_csv": str,
                    "timeline_csv": str,
                    "copy_map_csv": str
                },
                "validation": {
                    "status": "PASS|WARN|FAIL",
                    "checks": [...]
                },
                "metrics": {
                    "merit_score": float,
                    "roi_estimated": float,
                    "processing_time_seconds": float
                },
                "audit_trail": {
                    "session_id": str,
                    "timestamp": str,
                    "sources": [...]
                }
            }
        """
        session_id = self._generate_session_id()
        start_time = time.time()
        
        # Phase 1: Research
        company_data = await self.subagents["researcher"].fetch(
            nome=company_input["nome"],
            nif=company_input.get("nif"),
            sources=["einforma", "racius", "website"]
        )
        
        # Phase 2: Stack Intelligence
        stack_analysis = await self.subagents["stack_intel"].analyze(
            existing_stack=company_data.get("tech_stack", []),
            industry_cae=company_data["cae"],
            employee_count=company_data.get("headcount", 0)
        )
        
        # Phase 3: Budget Gate
        budget_validation = self._validate_budget_gate(
            teto_max=company_input["teto_max"],
            cofinanciamento=company_input["cofinanciamento"],
            elegiveis_target=company_input.get("elegiveis_target", 0)
        )
        
        if not budget_validation["valid"]:
            return {"error": budget_validation["message"], "session_id": session_id}
        
        budget_tiers = self._calculate_tiers(
            teto=company_input["teto_max"],
            distribution_prefs=company_input.get("preferencias", {})
        )
        
        # Phase 4: Financial Analysis
        financial_model = await self.subagents["financial"].analyze(
            ies_docs=company_input.get("ies_files", []),
            years=[2022, 2023, 2024],
            cae=company_data["cae"]
        )
        
        # Phase 5: Merit Scoring
        scoring_scenarios = await self.subagents["scorer"].simulate(
            base_quality_score=4.0,  # From project quality assessment
            job_creation_range=[0, 1, 2],
            vab_growth_range=[0, 5, 8, 12],
            industry_benchmark=financial_model["industry_avg"]
        )
        
        # Phase 6: Proposal Generation
        artifacts = await self.subagents["writer"].generate(
            template="premium_6_modules",
            company=company_data,
            stack=stack_analysis,
            financial=financial_model,
            budget_tiers=budget_tiers,
            scoring=scoring_scenarios,
            regulatory_citations=regulatory_docs
        )
        
        # Phase 7: Compliance
        validation = await self.subagents["validator"].check(
            proposal_html=artifacts["html"],
            company_data=company_data,
            frameworks=["RGPD", "DNSH", "DuploFinanciamento", "IFIC_Eligibility"]
        )
        
        processing_time = time.time() - start_time
        
        return {
            "artifacts": artifacts,
            "validation": validation,
            "metrics": {
                "merit_score": scoring_scenarios["recommended"]["mp"],
                "roi_estimated": financial_model["roi_projection"],
                "processing_time_seconds": processing_time
            },
            "audit_trail": {
                "session_id": session_id,
                "timestamp": datetime.now().isoformat(),
                "sources": company_data["sources"] + stack_analysis["sources"]
            }
        }
    
    def _validate_budget_gate(self, teto_max: float, cofinanciamento: float, elegiveis_target: float) -> Dict:
        """
        Critical validations before proceeding.
        """
        errors = []
        
        # Minimum eligible investment
        if elegiveis_target < 5000:
            errors.append("Investimento elegível mínimo: €5.000 [Aviso art.6]")
        
        # Teto vs eligible
        if elegiveis_target > teto_max:
            errors.append(f"Elegíveis (€{elegiveis_target}) > Teto (€{teto_max})")
        
        # Co-financing minimum (base rate 75% = 25% company)
        min_cofinanciamento = elegiveis_target * 0.25
        if cofinanciamento < min_cofinanciamento:
            errors.append(f"Cofinanciamento mínimo: €{min_cofinanciamento:.2f} (25% de €{elegiveis_target})")
        
        if errors:
            return {"valid": False, "message": "BUDGET GATE FAILED:\n" + "\n".join(errors)}
        
        return {"valid": True}
    
    def _calculate_tiers(self, teto: float, distribution_prefs: Dict) -> Dict:
        """
        Generate 3 budget tiers within teto.
        Default distribution (if prefs empty):
            RH: 60-70%
            SaaS/Software: 15-25%
            Consultoria: 8-15%
            Formação: 4-10%
            Equipamentos: 0-10%
            ROC/CC: ≤2.500
        """
        # Implementation with realistic IFIC-approved distributions
        ...
        
    def _generate_session_id(self) -> str:
        import uuid
        return str(uuid.uuid4())
```

**Output**: Orchestrates entire pipeline, returns complete package ready for client delivery.

---

### 2. Company Research Agent (`agents/researcher.py`)

**Responsibility**: Fetch company data from eInforma, Racius, website.

```python
class CompanyResearchAgent:
    """
    Multi-source company intelligence gatherer.
    Priority: eInforma (most comprehensive) → Racius (cross-check) → Website (tech stack)
    """
    
    def __init__(self, claude_client):
        self.claude = claude_client
        self.einforma = EInformaClient()  # MCP server
        self.racius = RaciusClient()      # MCP server
        
    async def fetch(self, nome: str, nif: str = None, sources: List[str] = ["einforma", "racius", "website"]) -> Dict:
        """
        Returns:
            {
                "nome_legal": str,
                "nif": str,
                "cae": str,
                "cae_description": str,
                "nuts_ii": str,
                "dimensao": "micro|pequena|media",
                "headcount": int,
                "sede": str,
                "financials": {
                    "volume_negocios_2024": float,
                    "ebitda_2024": float,
                    "capital_proprio": float,
                    ...
                },
                "tech_stack": List[str],  # Detected systems
                "compliance_alerts": List[str],  # Insolvency, tax issues, etc.
                "sources": [
                    {"name": "eInforma", "url": "...", "accessed": "2025-11-01"},
                    ...
                ]
            }
        """
        result = {
            "sources": []
        }
        
        # 1. eInforma (preferencial)
        if "einforma" in sources:
            try:
                einforma_data = await self.einforma.fetch_report(nif=nif, nome=nome)
                result.update({
                    "nome_legal": einforma_data["legal_name"],
                    "nif": einforma_data["nif"],
                    "cae": einforma_data["cae_principal"],
                    "sede": einforma_data["address"],
                    "financials": einforma_data["balance_sheet"],
                    "compliance_alerts": einforma_data["risk_signals"]
                })
                result["sources"].append({
                    "name": "eInforma",
                    "accessed": datetime.now().isoformat()
                })
            except Exception as e:
                # Log and continue to Racius
                pass
        
        # 2. Racius (complemento/cross-check)
        if "racius" in sources:
            racius_data = await self.racius.fetch_profile(nif=result.get("nif", nif))
            # Merge data, prioritize eInforma for conflicts
            ...
        
        # 3. Website (tech stack detection)
        if "website" in sources and result.get("website_url"):
            stack = await self._detect_stack_from_website(result["website_url"])
            result["tech_stack"] = stack
        
        # 4. Deduce NUTS II from sede
        result["nuts_ii"] = self._infer_nuts_ii(result["sede"])
        
        # 5. Classify dimensão (micro/pequena/media)
        result["dimensao"] = self._classify_sme_size(
            headcount=result.get("headcount", 0),
            revenue=result["financials"].get("volume_negocios_2024", 0)
        )
        
        return result
    
    async def _detect_stack_from_website(self, url: str) -> List[str]:
        """
        Use Claude with web_fetch to identify tech stack.
        Look for: ERP mentions (PHC, SAP, Primavera), CRM (Salesforce, HubSpot),
        Email (M365, Google Workspace), Cloud (AWS, Azure).
        """
        # Use MCP web_fetch + Claude analysis
        ...
    
    def _infer_nuts_ii(self, address: str) -> str:
        """
        Map address to NUTS II region.
        PT11 = Norte, PT16 = Centro, PT17 = Lisboa, PT18 = Alentejo, PT15 = Algarve
        """
        mapping = {
            "Porto": "PT11",
            "Braga": "PT11",
            "Lisboa": "PT17",
            "Setúbal": "PT17",
            "Coimbra": "PT16",
            ...
        }
        # Fuzzy match
        ...
    
    def _classify_sme_size(self, headcount: int, revenue: float) -> str:
        """
        EU SME definition:
        Micro: <10 employees AND <€2M revenue
        Pequena: <50 employees AND <€10M revenue
        Media: <250 employees AND <€50M revenue
        """
        if headcount < 10 and revenue < 2_000_000:
            return "micro"
        elif headcount < 50 and revenue < 10_000_000:
            return "pequena"
        elif headcount < 250 and revenue < 50_000_000:
            return "media"
        else:
            return "grande"  # Not SME, ineligible for IFIC
```

---

### 3. Stack Intelligence Agent (`agents/stack_intelligence.py`)

**Responsibility**: Detect redundancies, suggest integrations.

```python
class StackIntelligenceAgent:
    """
    CRITICAL AGENT: Prevents suggesting tools that duplicate existing functionality.
    Example: Never recommend Monday.com to PHC users, Slack to M365 users.
    """
    
    def __init__(self, claude_client):
        self.claude = claude_client
        self.rules = self._load_redundancy_rules()
        
    def _load_redundancy_rules(self) -> Dict:
        """
        Load from mcp_servers/stack_detector_mcp/rules.yaml
        
        Example structure:
        {
            "PHC": {
                "category": "ERP",
                "blocks": ["Monday.com", "HubSpot CRM", "Salesforce Sales Cloud"],
                "suggests": ["Power BI Embedded", "Azure ML integration", "PHC Copilot (if exists)"]
            },
            "Microsoft 365": {
                "category": "Productivity Suite",
                "blocks": ["Slack", "Notion", "Trello", "Asana"],
                "suggests": ["Microsoft Copilot", "Power Automate", "Dynamics 365"]
            },
            "SAP": {
                "blocks": ["NetSuite", "Odoo", "Sage"],
                "suggests": ["SAP Analytics Cloud", "SAP AI Business Services"]
            }
        }
        """
        # Load YAML file
        ...
    
    async def analyze(self, existing_stack: List[str], industry_cae: str, employee_count: int) -> Dict:
        """
        Returns:
            {
                "existing_systems": [
                    {"name": "PHC", "category": "ERP", "coverage": ["CRM", "Finance", "Inventory"]}
                ],
                "redundancies_detected": [
                    {"proposed": "Monday.com", "conflicts_with": "PHC", "reason": "Duplicate CRM functionality"}
                ],
                "recommended_additions": [
                    {
                        "name": "Power BI Embedded in PHC",
                        "category": "Analytics",
                        "rationale": "Leverages existing PHC data",
                        "estimated_cost": 15000,
                        "ific_eligible": true
                    }
                ],
                "integration_strategy": str,  # Long-form explanation
                "sources": [...]
            }
        """
        result = {
            "existing_systems": [],
            "redundancies_detected": [],
            "recommended_additions": [],
            "sources": []
        }
        
        # 1. Classify existing systems
        for system in existing_stack:
            if system in self.rules:
                result["existing_systems"].append({
                    "name": system,
                    "category": self.rules[system]["category"],
                    "coverage": self._infer_coverage(system)
                })
        
        # 2. Check for common redundant proposals
        blocked_tools = []
        for system_info in result["existing_systems"]:
            system = system_info["name"]
            if system in self.rules:
                blocked_tools.extend(self.rules[system]["blocks"])
        
        result["blocked_tools"] = list(set(blocked_tools))
        
        # 3. Use Claude to suggest smart additions
        prompt = f"""
        Company profile:
        - Industry CAE: {industry_cae}
        - Employees: {employee_count}
        - Existing tech stack: {', '.join(existing_stack)}
        - Blocked tools (redundant): {', '.join(blocked_tools)}
        
        Task: Suggest 3-5 AI-powered tools/platforms that:
        1. Complement (not replace) existing systems
        2. Are IFIC-eligible (SaaS/software for productivity or AI implementation)
        3. Have realistic pricing (€5k-€50k range for SME)
        4. Align with industry best practices for CAE {industry_cae}
        
        For each suggestion, provide:
        - Name
        - Integration approach with existing stack
        - Estimated annual cost
        - Specific IFIC use case (productivity gain or AI capability)
        - Portuguese language support (critical!)
        
        Respond in JSON:
        [
            {{
                "name": "...",
                "category": "...",
                "integration": "...",
                "cost_eur": 0,
                "use_case": "...",
                "pt_support": true/false
            }}
        ]
        """
        
        response = await self.claude.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}]
        )
        
        suggestions = json.loads(response.content[0].text)
        
        # 4. Filter suggestions to ensure no redundancies
        for suggestion in suggestions:
            if suggestion["name"] not in blocked_tools:
                result["recommended_additions"].append({
                    **suggestion,
                    "ific_eligible": self._check_ific_eligibility(suggestion)
                })
        
        # 5. Generate integration strategy narrative
        result["integration_strategy"] = await self._generate_integration_narrative(
            existing=result["existing_systems"],
            additions=result["recommended_additions"]
        )
        
        return result
    
    def _infer_coverage(self, system: str) -> List[str]:
        """
        Map system to functional coverage areas.
        """
        coverage_map = {
            "PHC": ["CRM", "Finance", "Inventory", "Sales", "Purchasing"],
            "SAP": ["ERP", "Finance", "Supply Chain", "HR"],
            "Microsoft 365": ["Email", "Collaboration", "Document Management", "Communication"],
            ...
        }
        return coverage_map.get(system, [])
    
    def _check_ific_eligibility(self, tool: Dict) -> bool:
        """
        Validate if tool category is IFIC-eligible.
        Eligible: SaaS, Software licenses, AI platforms
        Not eligible: Hardware (unless edge computing/GPUs justified), pure consultancy
        """
        eligible_categories = [
            "Analytics", "AI/ML Platform", "CRM", "Marketing Automation",
            "Productivity", "Collaboration", "Data Management", "Cybersecurity"
        ]
        return tool["category"] in eligible_categories
```

---

### 4. Financial Analyst Agent (`agents/financial_analyst.py`)

**Responsibility**: Parse IES documents, calculate ratios, project ROI.

```python
class FinancialAnalysisAgent:
    """
    Deep financial analysis for IFIC merit scoring (B2 criteria).
    Parses IES (Informação Empresarial Simplificada), calculates key ratios.
    """
    
    async def analyze(self, ies_docs: List[str], years: List[int], cae: str) -> Dict:
        """
        Args:
            ies_docs: List of file paths to IES PDFs (3 years typical)
            years: [2022, 2023, 2024]
            cae: Industry code for benchmarking
        
        Returns:
            {
                "historical_financials": {
                    "2024": {"revenue": float, "ebitda": float, "net_margin": float, ...},
                    "2023": {...},
                    "2022": {...}
                },
                "growth_trends": {
                    "revenue_cagr": float,
                    "vab_growth_2y": float
                },
                "ratios": {
                    "current_ratio": float,
                    "debt_to_equity": float,
                    "roe": float
                },
                "industry_benchmark": {
                    "avg_revenue_cae": float,
                    "percentile": int  # Where company ranks
                },
                "roi_projection": {
                    "conservative": float,  # 25-35%
                    "moderate": float,      # 35-45%
                    "ambitious": float      # 45-60%
                },
                "vab_impact_estimate": {
                    "baseline_vab": float,
                    "post_ia_vab": float,
                    "growth_percent": float
                },
                "risk_assessment": {
                    "financial_health": "strong|adequate|weak",
                    "alerts": List[str]
                }
            }
        """
        # 1. Parse IES docs (use Claude with PDFs)
        financials_by_year = {}
        for doc, year in zip(ies_docs, years):
            financials_by_year[str(year)] = await self._parse_ies_pdf(doc)
        
        # 2. Calculate growth trends
        revenues = [financials_by_year[str(y)]["revenue"] for y in sorted(years)]
        cagr = self._calculate_cagr(revenues, len(years))
        
        # 3. Calculate VAB (Valor Acrescentado Bruto)
        # VAB = Revenue - External Purchases
        vab_2024 = financials_by_year["2024"]["revenue"] - financials_by_year["2024"]["external_costs"]
        vab_2022 = financials_by_year["2022"]["revenue"] - financials_by_year["2022"]["external_costs"]
        vab_growth = ((vab_2024 - vab_2022) / vab_2022) * 100
        
        # 4. Industry benchmarking (use eInforma sector data if available)
        benchmark = await self._get_industry_benchmark(cae)
        
        # 5. ROI projection (realistic ranges based on AI implementation studies)
        roi_projection = self._project_roi(
            current_revenue=financials_by_year["2024"]["revenue"],
            investment_planned=50000,  # Placeholder, will be updated
            industry_avg_margin=benchmark["avg_margin"]
        )
        
        # 6. VAB impact estimate (for B2 scoring)
        vab_impact = self._estimate_vab_impact(
            baseline_vab=vab_2024,
            ai_productivity_gain=0.08  # 8% conservative estimate
        )
        
        # 7. Risk assessment
        current_ratio = financials_by_year["2024"]["current_assets"] / financials_by_year["2024"]["current_liabilities"]
        financial_health = "strong" if current_ratio > 1.5 else "adequate" if current_ratio > 1.0 else "weak"
        
        return {
            "historical_financials": financials_by_year,
            "growth_trends": {
                "revenue_cagr": cagr,
                "vab_growth_2y": vab_growth
            },
            "ratios": {
                "current_ratio": current_ratio,
                # ... other ratios
            },
            "industry_benchmark": benchmark,
            "roi_projection": roi_projection,
            "vab_impact_estimate": vab_impact,
            "risk_assessment": {
                "financial_health": financial_health,
                "alerts": self._generate_risk_alerts(financials_by_year["2024"])
            }
        }
    
    async def _parse_ies_pdf(self, pdf_path: str) -> Dict:
        """
        Use Claude with PDF support to extract financial data.
        """
        with open(pdf_path, 'rb') as f:
            pdf_base64 = base64.b64encode(f.read()).decode()
        
        prompt = """
        Extract the following financial data from this IES document:
        - Volume de negócios (Revenue)
        - EBITDA (if stated, else calculate from EBIT + D&A)
        - Resultado líquido (Net income)
        - Ativo corrente (Current assets)
        - Passivo corrente (Current liabilities)
        - Capital próprio (Equity)
        - Fornecimentos e serviços externos (External costs)
        
        Respond in JSON with numeric values (no currency symbols).
        """
        
        response = await self.claude.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1500,
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "document",
                        "source": {
                            "type": "base64",
                            "media_type": "application/pdf",
                            "data": pdf_base64
                        }
                    },
                    {"type": "text", "text": prompt}
                ]
            }]
        )
        
        return json.loads(response.content[0].text)
    
    def _calculate_cagr(self, values: List[float], periods: int) -> float:
        """
        CAGR = (Ending Value / Beginning Value)^(1/periods) - 1
        """
        if len(values) < 2:
            return 0.0
        return ((values[-1] / values[0]) ** (1 / (periods - 1))) - 1
    
    def _project_roi(self, current_revenue: float, investment_planned: float, industry_avg_margin: float) -> Dict:
        """
        Conservative AI ROI estimates based on academic studies:
        - Productivity gains: 15-25% (McKinsey 2023)
        - Revenue impact: 5-10% (conditional on implementation quality)
        
        Formula: ROI = (Revenue_Gain + Cost_Savings - Investment) / Investment
        """
        # Conservative: 5% revenue boost + 10% cost savings
        revenue_gain_conservative = current_revenue * 0.05
        cost_savings_conservative = current_revenue * industry_avg_margin * 0.10
        roi_conservative = ((revenue_gain_conservative + cost_savings_conservative) / investment_planned) * 100
        
        # Moderate: 8% + 15%
        roi_moderate = ((current_revenue * 0.08 + current_revenue * industry_avg_margin * 0.15) / investment_planned) * 100
        
        # Ambitious: 12% + 20%
        roi_ambitious = ((current_revenue * 0.12 + current_revenue * industry_avg_margin * 0.20) / investment_planned) * 100
        
        return {
            "conservative": min(roi_conservative, 35),  # Cap at 35%
            "moderate": min(roi_moderate, 45),          # Cap at 45%
            "ambitious": min(roi_ambitious, 60)         # Cap at 60%
        }
```

---

### 5. Proposal Writer Agent (`agents/proposal_writer.py`)

**Responsibility**: Generate premium HTML proposal (6 modules).

```python
class ProposalWriterAgent:
    """
    Generates McKinsey-grade HTML proposal with interactive elements.
    Uses Jinja2 templates + embedded CSS/JS.
    """
    
    def __init__(self, claude_client):
        self.claude = claude_client
        self.template_loader = jinja2.FileSystemLoader('templates/')
        self.env = jinja2.Environment(loader=self.template_loader)
        
    async def generate(
        self,
        template: str,
        company: Dict,
        stack: Dict,
        financial: Dict,
        budget_tiers: Dict,
        scoring: Dict,
        regulatory_citations: List[str]
    ) -> Dict:
        """
        Generate complete proposal package.
        
        Returns:
            {
                "html": str,  # Full proposal_premium.html
                "budget_csv": str,
                "timeline_csv": str,
                "copy_map_csv": str
            }
        """
        # 1. Load template
        tmpl = self.env.get_template(f'{template}.html')
        
        # 2. Prepare data for template
        context = {
            "company": company,
            "project": {
                "use_cases": await self._generate_use_cases(company["cae"], stack),
                "training_plan": self._generate_training_plan(company["dimensao"]),
                "consultoria_plan": self._generate_consultoria_plan()
            },
            "budget": budget_tiers,
            "scoring": scoring,
            "timeline": self._generate_timeline(),
            "compliance": self._generate_compliance_checklist(regulatory_citations),
            "citations": regulatory_citations,
            "metadata": {
                "generated_at": datetime.now().isoformat(),
                "version": "2.1",
                "session_id": uuid.uuid4()
            }
        }
        
        # 3. Render HTML
        html_output = tmpl.render(**context)
        
        # 4. Generate CSVs
        budget_csv = self._export_budget_csv(budget_tiers)
        timeline_csv = self._export_timeline_csv(context["timeline"])
        copy_map_csv = self._export_copy_map_csv(context)
        
        return {
            "html": html_output,
            "budget_csv": budget_csv,
            "timeline_csv": timeline_csv,
            "copy_map_csv": copy_map_csv
        }
    
    async def _generate_use_cases(self, cae: str, stack: Dict) -> List[Dict]:
        """
        Use Claude to generate 3-5 industry-specific AI use cases.
        """
        prompt = f"""
        Generate 3-5 AI use cases for a Portuguese SME:
        - Industry CAE: {cae}
        - Existing tech stack: {', '.join([s['name'] for s in stack['existing_systems']])}
        
        Each use case should include:
        1. Title (concise, action-oriented)
        2. Problem statement (current pain point)
        3. AI solution (specific technology/approach)
        4. Data requirements (what data is needed)
        5. KPIs (2-3 measurable outcomes)
        6. Implementation complexity (Low/Medium/High)
        7. Estimated ROI impact (% contribution to overall ROI)
        8. IFIC eligibility rationale (cite Aviso if possible)
        
        Prioritize use cases that:
        - Integrate with existing stack (not replace)
        - Have clear productivity gains
        - Are realistic for SME context (not enterprise-only)
        - Support Portuguese language
        
        Respond in JSON array.
        """
        
        response = await self.claude.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=3000,
            messages=[{"role": "user", "content": prompt}]
        )
        
        use_cases = json.loads(response.content[0].text)
        return use_cases
    
    def _generate_training_plan(self, dimensao: str) -> Dict:
        """
        Standard IFIC training plan structure.
        Allocation: 4-10% of budget (not 47%!).
        """
        profiles = {
            "micro": {
                "participants": 5,
                "hours": 40,
                "modules": ["IA Fundamentals", "Tool-specific training", "Change management"]
            },
            "pequena": {
                "participants": 15,
                "hours": 60,
                "modules": ["IA Fundamentals", "Data literacy", "Tool-specific", "Advanced analytics", "Ethics & RGPD"]
            },
            "media": {
                "participants": 30,
                "hours": 80,
                "modules": ["IA Strategy", "Data science basics", "ML ops", "Tool-specific", "Leadership in AI", "RGPD deep-dive"]
            }
        }
        
        plan = profiles.get(dimensao, profiles["pequena"])
        plan["cost_estimate"] = plan["participants"] * plan["hours"] * 35  # €35/hour average
        
        return plan
    
    def _generate_timeline(self) -> List[Dict]:
        """
        Standard IFIC timeline: ≤24 months, phased approach.
        """
        return [
            {"phase": "Preparação", "start": "M1", "end": "M2", "milestones": ["Kick-off", "Stack audit", "Data assessment"]},
            {"phase": "Implementação Fase 1", "start": "M3", "end": "M9", "milestones": ["UC1-UC2 deploy", "Training wave 1"]},
            {"phase": "Implementação Fase 2", "start": "M10", "end": "M18", "milestones": ["UC3-UC4 deploy", "Integration complete"]},
            {"phase": "Consolidação", "start": "M19", "end": "M24", "milestones": ["KPI tracking", "Optimization", "Final report"]}
        ]
```

---

### 6. Merit Scorer Agent (`agents/merit_scorer.py`)

**Responsibility**: Calculate MP, simulate scenarios.

```python
class MeritScoringAgent:
    """
    IFIC Merit Score calculator.
    Formula: MP = 0.50×A + 0.50×min(B1, B2)
    Where:
        A = Project quality (0-5)
        B1 = Job creation impact (0-5) — 25% of total merit!
        B2 = Market/export impact (0-5)
    """
    
    def __init__(self, claude_client):
        self.claude = claude_client
        self.criteria = self._load_merit_criteria()
        
    def _load_merit_criteria(self) -> Dict:
        """
        Load from data/regulatory/merit_criteria.json
        
        Structure:
        {
            "A_quality": {
                "innovation": {"weight": 0.25, "scale": [...]},
                "methodology": {"weight": 0.20, ...},
                ...
            },
            "B1_jobs": {
                "thresholds": {
                    "0_jobs": 1.0,
                    "1_job": 3.0,
                    "2_jobs": 4.0,
                    "3+_jobs": 5.0
                }
            },
            "B2_market": {
                "vab_growth": {
                    "0-5%": 2.0,
                    "5-10%": 3.5,
                    "10-15%": 4.5,
                    "15%+": 5.0
                }
            }
        }
        """
        with open('data/regulatory/merit_criteria.json', 'r') as f:
            return json.load(f)
    
    async def simulate(
        self,
        base_quality_score: float,
        job_creation_range: List[int],
        vab_growth_range: List[float],
        industry_benchmark: Dict
    ) -> Dict:
        """
        Generate merit score scenarios.
        
        Returns:
            {
                "base": {"jobs": 0, "vab": 0, "A": 4.0, "B1": 3.0, "B2": 3.2, "MP": 3.1, "ranking": "Baixo"},
                "scenarios": [
                    {"jobs": 1, "vab": 5, "A": 4.0, "B1": 3.8, "B2": 3.5, "MP": 3.7, "ranking": "Médio"},
                    {"jobs": 2, "vab": 8, "A": 4.0, "B1": 4.2, "B2": 3.7, "MP": 4.0, "ranking": "Alto"},
                    ...
                ],
                "recommended": {...},  # Scenario with MP ≥ 4.0
                "analysis": str  # Long-form explanation
            }
        """
        scenarios = []
        
        for jobs in job_creation_range:
            for vab in vab_growth_range:
                b1_score = self._calculate_b1(jobs)
                b2_score = self._calculate_b2(vab, industry_benchmark)
                b_score = min(b1_score, b2_score)
                mp = 0.50 * base_quality_score + 0.50 * b_score
                
                scenarios.append({
                    "jobs": jobs,
                    "vab_growth": vab,
                    "A": base_quality_score,
                    "B1": b1_score,
                    "B2": b2_score,
                    "B": b_score,
                    "MP": round(mp, 2),
                    "ranking": self._classify_ranking(mp)
                })
        
        # Sort by MP descending
        scenarios.sort(key=lambda x: x["MP"], reverse=True)
        
        # Find recommended scenario (first with MP ≥ 4.0)
        recommended = next((s for s in scenarios if s["MP"] >= 4.0), scenarios[0])
        
        # Generate analysis narrative
        analysis = await self._generate_scoring_analysis(scenarios, recommended)
        
        return {
            "base": scenarios[-1],  # Worst case (0 jobs, 0 VAB growth)
            "scenarios": scenarios,
            "recommended": recommended,
            "analysis": analysis
        }
    
    def _calculate_b1(self, jobs_created: int) -> float:
        """
        B1 scoring based on job creation.
        Critical: Employment = 25% of total merit score!
        """
        thresholds = self.criteria["B1_jobs"]["thresholds"]
        
        if jobs_created == 0:
            return thresholds["0_jobs"]
        elif jobs_created == 1:
            return thresholds["1_job"]
        elif jobs_created == 2:
            return thresholds["2_jobs"]
        else:  # 3+
            return thresholds["3+_jobs"]
    
    def _calculate_b2(self, vab_growth_percent: float, benchmark: Dict) -> float:
        """
        B2 scoring based on VAB growth and market impact.
        """
        ranges = self.criteria["B2_market"]["vab_growth"]
        
        if vab_growth_percent < 5:
            return ranges["0-5%"]
        elif vab_growth_percent < 10:
            return ranges["5-10%"]
        elif vab_growth_percent < 15:
            return ranges["10-15%"]
        else:
            return ranges["15%+"]
    
    def _classify_ranking(self, mp: float) -> str:
        if mp < 3.0:
            return "Inelegível"
        elif mp < 3.5:
            return "Baixo"
        elif mp < 4.0:
            return "Médio"
        else:
            return "Alto"
    
    async def _generate_scoring_analysis(self, scenarios: List[Dict], recommended: Dict) -> str:
        """
        Use Claude to generate strategic narrative.
        """
        prompt = f"""
        Analyze these IFIC merit score scenarios and provide strategic recommendations:
        
        Scenarios: {json.dumps(scenarios, indent=2)}
        Recommended: {json.dumps(recommended, indent=2)}
        
        Provide:
        1. Key insight: Why the recommended scenario is optimal
        2. Job creation strategy (how to achieve the target)
        3. VAB growth drivers (operational changes needed)
        4. Risk mitigation (if targets not met)
        5. Competitive positioning (vs typical IFIC applications)
        
        Write in pt-PT, professional tone, max 400 words.
        """
        
        response = await self.claude.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=800,
            messages=[{"role": "user", "content": prompt}]
        )
        
        return response.content[0].text
```

---

## 🔧 MCP SERVERS (Custom Tools)

### eInforma MCP (`mcp_servers/einforma_mcp/server.py`)

```python
from mcp.server import MCPServer
import httpx

class EInformaServer(MCPServer):
    """
    MCP server for eInforma API.
    Note: Respect ToS — use for individual queries, not mass scraping.
    """
    
    def __init__(self):
        super().__init__("einforma-fetcher")
        self.base_url = "https://www.einforma.pt"
        self.session = httpx.AsyncClient()
        
    @self.tool("fetch_company_report")
    async def fetch_company_report(self, nif: str = None, nome: str = None) -> dict:
        """
        Fetch company report from eInforma.
        Prioritize free reports if available.
        """
        # Implementation with respect to ToS
        # Use Selenium/Playwright for authenticated scraping if needed
        ...
    
    @self.tool("parse_financials")
    async def parse_financials(self, report_html: str) -> dict:
        """
        Extract structured financial data from report HTML.
        """
        # BeautifulSoup parsing
        ...
```

### Stack Detector MCP (`mcp_servers/stack_detector_mcp/server.py`)

```python
class StackDetectorServer(MCPServer):
    """
    Detects tech stack from website and checks redundancies.
    """
    
    @self.tool("detect_from_website")
    async def detect_from_website(self, url: str) -> List[str]:
        """
        Use various signals:
        - DNS records (MX for email provider)
        - HTTP headers (X-Powered-By, Server)
        - HTML meta tags
        - JavaScript libraries (Wappalyzer-style)
        - Content analysis (mentions of "PHC", "SAP", etc.)
        """
        ...
    
    @self.tool("check_redundancy")
    async def check_redundancy(self, existing: List[str], proposed: List[str]) -> Dict:
        """
        Cross-reference with rules.yaml
        """
        ...
```

---

## 🗄️ DATABASE SCHEMA

```sql
-- database/models.py (SQLAlchemy)

CREATE TABLE companies (
    id UUID PRIMARY KEY,
    nome_legal VARCHAR(255) NOT NULL,
    nif VARCHAR(9) UNIQUE NOT NULL,
    cae VARCHAR(5),
    nuts_ii VARCHAR(4),
    dimensao VARCHAR(20),
    tech_stack JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE applications (
    id UUID PRIMARY KEY,
    company_id UUID REFERENCES companies(id),
    status VARCHAR(50),  -- 'draft', 'processing', 'completed', 'submitted'
    teto_max DECIMAL(10,2),
    cofinanciamento DECIMAL(10,2),
    merit_score DECIMAL(3,2),
    proposal_html TEXT,
    budget_csv TEXT,
    timeline_csv TEXT,
    audit_trail JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE use_cases (
    id UUID PRIMARY KEY,
    application_id UUID REFERENCES applications(id),
    title VARCHAR(255),
    description TEXT,
    roi_impact DECIMAL(5,2),
    complexity VARCHAR(20)
);

CREATE TABLE validations (
    id UUID PRIMARY KEY,
    application_id UUID REFERENCES applications(id),
    framework VARCHAR(50),  -- 'RGPD', 'DNSH', etc.
    status VARCHAR(20),     -- 'PASS', 'WARN', 'FAIL'
    details JSONB,
    validated_at TIMESTAMP DEFAULT NOW()
);
```

---

## 🌐 API ENDPOINTS

```python
# api/main.py

from fastapi import FastAPI, UploadFile, File
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
    Start a new IFIC application.
    Triggers full orchestrator pipeline.
    """
    orchestrator = IFICOrchestrator(api_key=os.getenv("CLAUDE_API_KEY"))
    
    result = await orchestrator.process_application(
        company_input={
            "nome": company_name,
            "nif": nif,
            "teto_max": teto_max,
            "cofinanciamento": cofinanciamento,
            "ies_files": [f.file for f in ies_files] if ies_files else []
        },
        regulatory_docs=load_regulatory_docs()
    )
    
    # Save to DB
    application_id = save_to_database(result)
    
    return {
        "application_id": application_id,
        "status": "completed",
        "merit_score": result["metrics"]["merit_score"],
        "artifacts": {
            "proposal_url": f"/applications/{application_id}/proposal.html",
            "budget_url": f"/applications/{application_id}/budget.csv"
        }
    }

@app.get("/applications/{application_id}/proposal.html")
async def get_proposal(application_id: str):
    """
    Retrieve generated proposal HTML.
    """
    ...

@app.post("/research/company")
async def research_company(nif: str = None, nome: str = None):
    """
    Standalone company research (for pre-sales).
    """
    researcher = CompanyResearchAgent(claude_client)
    data = await researcher.fetch(nome=nome, nif=nif)
    return data
```

---

## 🎨 FRONTEND (React)

```typescript
// web/src/pages/ApplicationForm.tsx

import React, { useState } from 'react';
import { BudgetTierSelector, MeritScoreSimulator, StackAnalyzer } from '../components';

export const ApplicationForm: React.FC = () => {
    const [formData, setFormData] = useState({
        companyName: '',
        nif: '',
        tetoMax: 0,
        cofinanciamento: 0,
        iesFiles: []
    });
    
    const handleSubmit = async () => {
        const response = await fetch('/api/applications', {
            method: 'POST',
            body: JSON.stringify(formData)
        });
        
        const result = await response.json();
        
        // Redirect to proposal view
        window.location.href = `/applications/${result.application_id}`;
    };
    
    return (
        <div className="max-w-4xl mx-auto p-6">
            <h1 className="text-3xl font-serif mb-6">Nova Candidatura IFIC</h1>
            
            {/* Multi-step form */}
            <Step1_CompanyInfo />
            <Step2_BudgetGate />
            <Step3_TechStack />
            <Step4_FinancialDocs />
            <Step5_Review />
            
            <button onClick={handleSubmit} className="btn-primary">
                Gerar Proposta
            </button>
        </div>
    );
};
```

---

## 📊 HTML TEMPLATE STRUCTURE

```html
<!-- templates/proposal_premium.html -->
<!DOCTYPE html>
<html lang="pt-PT">
<head>
    <meta charset="UTF-8">
    <title>Proposta IFIC — {{ company.nome_legal }}</title>
    <style>
        /* Glassmorphism + Premium Typography */
        :root {
            --primary: #0066CC;
            --secondary: #00A86B;
            --glass-bg: rgba(255, 255, 255, 0.1);
            --glass-border: rgba(255, 255, 255, 0.2);
            --shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
        }
        
        body {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            font-size: 16px;
            line-height: 1.6;
            color: #1a1a1a;
            background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
        }
        
        h1, h2, h3 {
            font-family: 'IBM Plex Serif', Georgia, serif;
            font-weight: 600;
        }
        
        .card {
            background: var(--glass-bg);
            backdrop-filter: blur(10px);
            border: 1px solid var(--glass-border);
            border-radius: 16px;
            padding: 2rem;
            margin-bottom: 2rem;
            box-shadow: var(--shadow);
        }
        
        .badge {
            display: inline-block;
            padding: 0.5rem 1rem;
            border-radius: 20px;
            font-size: 0.875rem;
            font-weight: 600;
        }
        
        .badge.elegivel { background: #00A86B; color: white; }
        .badge.mp { background: #0066CC; color: white; }
        .badge.incentivo { background: #FF6B35; color: white; }
        
        /* Interactive elements */
        .tier-selector button {
            padding: 1rem 2rem;
            margin: 0.5rem;
            border: 2px solid var(--primary);
            border-radius: 8px;
            background: transparent;
            cursor: pointer;
            transition: all 0.3s;
        }
        
        .tier-selector button.active {
            background: var(--primary);
            color: white;
        }
        
        /* Scoring simulator */
        #score-calc input[type="number"] {
            width: 100px;
            padding: 0.5rem;
            border: 1px solid #ccc;
            border-radius: 4px;
        }
        
        #score-calc output {
            font-size: 1.5rem;
            font-weight: 700;
            color: var(--primary);
        }
    </style>
</head>
<body>
    <!-- MÓDULO 1: Dashboard Executivo -->
    <header class="card">
        <h1>Proposta de Candidatura IFIC</h1>
        <p class="subtitle">{{ company.nome_legal }} — NIF {{ company.nif }}</p>
        
        <div class="badges">
            <span class="badge elegivel">✓ Elegível</span>
            <span class="badge mp">MP: {{ scoring.recommended.MP }}/5.0</span>
            <span class="badge incentivo">Incentivo: €{{ '{:,.0f}'.format(budget.recommended.incentivo) }}</span>
        </div>
    </header>
    
    <!-- MÓDULO 2: Stack Intelligence & Use Cases -->
    <section id="projeto" class="card">
        <h2>2. Projeto IA Integrado</h2>
        
        <div class="stack-atual">
            <h3>Stack Tecnológico Existente</h3>
            <ul>
                {% for system in stack.existing_systems %}
                <li><strong>{{ system.name }}</strong> ({{ system.category }}) — <em>manter e expandir</em></li>
                {% endfor %}
            </ul>
        </div>
        
        <div class="use-cases">
            {% for uc in project.use_cases %}
            <article class="use-case card">
                <h4>{{ uc.title }}</h4>
                <p>{{ uc.description }}</p>
                <div class="metrics">
                    <span class="kpi">ROI: {{ uc.roi_impact }}%</span>
                    <span class="complexity">Complexidade: {{ uc.complexity }}</span>
                </div>
            </article>
            {% endfor %}
        </div>
    </section>
    
    <!-- MÓDULO 3: Orçamento 3-Tier Interativo -->
    <section id="orcamento" class="card">
        <h2>3. Orçamento (Tiers)</h2>
        
        <div class="tier-selector">
            <button onclick="showTier(1)">Essencial (€{{ '{:,.0f}'.format(budget.tier1.total) }})</button>
            <button onclick="showTier(2)" class="active">Recomendado (€{{ '{:,.0f}'.format(budget.tier2.total) }})</button>
            <button onclick="showTier(3)">Completo (€{{ '{:,.0f}'.format(budget.tier3.total) }})</button>
        </div>
        
        <table id="budget-table">
            <thead>
                <tr>
                    <th>Rubrica</th>
                    <th>Tier 1</th>
                    <th>Tier 2</th>
                    <th>Tier 3</th>
                    <th>Elegível?</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td>RH Dedicados</td>
                    <td>€{{ '{:,.0f}'.format(budget.tier1.rh) }}</td>
                    <td>€{{ '{:,.0f}'.format(budget.tier2.rh) }}</td>
                    <td>€{{ '{:,.0f}'.format(budget.tier3.rh) }}</td>
                    <td>✓</td>
                </tr>
                <!-- More rows -->
            </tbody>
        </table>
    </section>
    
    <!-- MÓDULO 4: Scoring Simulator -->
    <section id="scoring" class="card">
        <h2>4. Simulador de Merit Score</h2>
        
        <form id="score-calc">
            <label>
                Empregos criados:
                <input type="number" id="jobs" value="{{ scoring.recommended.jobs }}" min="0" max="5">
            </label>
            <label>
                Crescimento VAB (%):
                <input type="number" id="vab" value="{{ scoring.recommended.vab_growth }}" min="0" max="20" step="0.1">
            </label>
            <output id="mp-result">MP = {{ scoring.recommended.MP }}</output>
        </form>
        
        <table class="score-breakdown">
            <tr><th>Critério</th><th>Score</th><th>Peso</th></tr>
            <tr><td>A - Qualidade Projeto</td><td>{{ scoring.recommended.A }}</td><td>50%</td></tr>
            <tr><td>B1 - Criação Empregos</td><td>{{ scoring.recommended.B1 }}</td><td>25%*</td></tr>
            <tr><td>B2 - Impacto Mercado</td><td>{{ scoring.recommended.B2 }}</td><td>25%*</td></tr>
            <tr class="total"><td><strong>Merit Final</strong></td><td colspan="2"><strong>{{ scoring.recommended.MP }}</strong></td></tr>
        </table>
        <p><small>*B = min(B1, B2), peso total 50%</small></p>
    </section>
    
    <!-- MÓDULO 5: Cronograma Gantt (SVG) -->
    <!-- MÓDULO 6: Checklist SIGA-BF -->
    
    <footer>
        <p>Proposta gerada por <strong>AiParaTi</strong> — Especialistas em Candidaturas IFIC</p>
        <p>Versão {{ metadata.version }} | {{ metadata.generated_at }} | Audit ID: {{ metadata.session_id }}</p>
    </footer>
    
    <script>
        // Interactive budget tier switching
        function showTier(tier) {
            // Update table display
            document.querySelectorAll('.tier-selector button').forEach(btn => btn.classList.remove('active'));
            event.target.classList.add('active');
            
            // Update budget table (show/hide columns)
            // ...
        }
        
        // Merit score live calculator
        document.getElementById('jobs').addEventListener('input', recalculateMP);
        document.getElementById('vab').addEventListener('input', recalculateMP);
        
        function recalculateMP() {
            const jobs = parseInt(document.getElementById('jobs').value);
            const vab = parseFloat(document.getElementById('vab').value);
            
            // Simplified scoring logic (real logic in Python)
            let b1 = jobs === 0 ? 3.0 : jobs === 1 ? 3.8 : jobs >= 2 ? 4.2 : 3.0;
            let b2 = vab < 5 ? 3.2 : vab < 10 ? 3.7 : vab < 15 ? 4.3 : 4.8;
            let b = Math.min(b1, b2);
            let mp = (0.50 * 4.0) + (0.50 * b);  // A=4.0 fixed
            
            document.getElementById('mp-result').textContent = `MP = ${mp.toFixed(2)}`;
        }
    </script>
</body>
</html>
```

---

## ✅ TESTING STRATEGY

```python
# tests/integration/test_full_pipeline.py

import pytest
from agents.orchestrator import IFICOrchestrator

@pytest.mark.asyncio
async def test_full_pipeline_micro_company():
    """
    Test complete pipeline with mock micro company.
    """
    orchestrator = IFICOrchestrator(api_key=os.getenv("CLAUDE_API_KEY"))
    
    mock_input = {
        "nome": "InnovaSolutions Lda",
        "nif": "123456789",
        "cae": "62010",
        "teto_max": 80000,
        "cofinanciamento": 20000,
        "ies_files": ["tests/fixtures/ies_2024.pdf"]
    }
    
    result = await orchestrator.process_application(
        company_input=mock_input,
        regulatory_docs=["data/regulatory/portaria_286_2025.json"]
    )
    
    # Assertions
    assert result["validation"]["status"] == "PASS"
    assert result["metrics"]["merit_score"] >= 3.0  # Minimum eligible
    assert 5000 <= result["artifacts"]["budget_csv_parsed"]["total_eligible"] <= 80000
    assert result["artifacts"]["html"] is not None
    assert len(result["artifacts"]["html"]) > 10000  # Substantial HTML
    
    # Check for redundancies (should be 0 if stack intelligence worked)
    assert len(result["stack_analysis"]["redundancies_detected"]) == 0
    
    # Validate ROI is realistic (<100%)
    assert result["metrics"]["roi_estimated"] < 100
    
    # Check citations present
    assert "[Aviso" in result["artifacts"]["html"]
    assert "[Anexo" in result["artifacts"]["html"]
```

---

## 🚀 DEPLOYMENT

```yaml
# docker-compose.yml

version: '3.8'

services:
  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - CLAUDE_API_KEY=${CLAUDE_API_KEY}
      - DATABASE_URL=postgresql://user:pass@db:5432/fundai
    depends_on:
      - db
    volumes:
      - ./data:/app/data
      - ./templates:/app/templates
  
  db:
    image: postgres:15
    environment:
      - POSTGRES_DB=fundai
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=pass
    volumes:
      - pgdata:/var/lib/postgresql/data
  
  web:
    build: ./web
    ports:
      - "3000:3000"
    depends_on:
      - api

volumes:
  pgdata:
```

---

## 📈 SUCCESS METRICS (Instrumentation)

```python
# Add to orchestrator.py

import prometheus_client as prom

# Define metrics
processing_time = prom.Histogram('application_processing_seconds', 'Time to process application')
approval_rate = prom.Counter('applications_approved', 'Approved applications')
merit_score_avg = prom.Gauge('merit_score_average', 'Average merit score')

@processing_time.time()
async def process_application(self, ...):
    # Existing code
    
    # At end:
    if result["validation"]["status"] == "PASS":
        approval_rate.inc()
    
    merit_score_avg.set(result["metrics"]["merit_score"])
```

---

## 🎯 NEXT STEPS (Implementation Order)

### Week 1-2: Foundation
1. ✅ Setup project structure (`fundai/` folder)
2. ✅ Implement `Orchestrator` skeleton
3. ✅ Create `CompanyResearchAgent` with mock eInforma
4. ✅ Build `StackIntelligenceAgent` with rules.yaml
5. ✅ Write unit tests for stack redundancy detection

### Week 3-4: Core Agents
6. ✅ Implement `FinancialAnalysisAgent` with IES parsing
7. ✅ Build `MeritScoringAgent` with scenario simulator
8. ✅ Create `ProposalWriterAgent` with Jinja2 template
9. ✅ Design `proposal_premium.html` template (6 modules)
10. ✅ Integration test: End-to-end pipeline with mock data

### Week 5-6: API & Frontend
11. ✅ FastAPI backend (`api/main.py`)
12. ✅ React frontend (`web/src/`)
13. ✅ Database setup (PostgreSQL + migrations)
14. ✅ Deploy to staging (Docker Compose)

### Week 7-8: Polish & Launch
15. ✅ Real eInforma/Racius integration (respect ToS)
16. ✅ RGPD compliance validation
17. ✅ Load testing (simulate 20 concurrent applications)
18. ✅ Beta launch with 3-5 pilot clients

---

## 💰 PRICING & GTM

```yaml
Launch_Pricing:
  DIY_Tool:
    price: €1.500
    margin: 90%
    target: 50 users/year
    
  Standard:
    price: €5.000
    margin: 70%
    target: 15 users/year
    
  Premium:
    price: €8.000
    margin: 65%
    target: 10 users/year

Year_1_Revenue_Projection:
  Total: €150.000
  Breakdown:
    - DIY: €75k (50 × €1.5k)
    - Standard: €75k (15 × €5k)
    - Premium: €80k (10 × €8k) — this exceeds total, adjust

# Realistic Year 1 (conservative):
  Total: €120.000
  Breakdown:
    - DIY: €30k (20 × €1.5k)
    - Standard: €50k (10 × €5k)
    - Premium: €40k (5 × €8k)
```

---

## 📚 REGULATORY DATA SOURCES

```
data/regulatory/
├── portaria_286_2025.json          # Parsed from PDF
├── ific_thresholds.yaml             # Min/max limits
├── merit_criteria.json              # A/B1/B2 grids
├── eligible_expenses.json           # What's eligible vs not
└── compliance_checklists/
    ├── rgpd.yaml
    ├── dnsh.yaml
    └── double_funding.yaml
```

---

## 🔐 SECURITY & COMPLIANCE

```python
# Implement in all agents

def redact_pii(data: dict) -> dict:
    """
    Redact personal identifiable information before logging.
    """
    sensitive_fields = ["nif", "address", "shareholders", "bank_accounts"]
    redacted = data.copy()
    
    for field in sensitive_fields:
        if field in redacted:
            redacted[field] = "[REDACTED]"
    
    return redacted

# Usage:
logger.info(f"Processing application: {redact_pii(company_data)}")
```

---

## 📝 PROMPTS FOR CLAUDE CODE

Copy this entire file to Claude Code and say:

> "Scaffold the FundAI project based on this configuration. Start with:
> 1. Create folder structure
> 2. Implement Orchestrator skeleton
> 3. Build CompanyResearchAgent with eInforma mock
> 4. Create stack_intelligence with redundancy rules
> 5. Write first integration test
> 
> After each step, show me the code and ask for approval before proceeding."

---

## 🎉 EXPECTED OUTCOMES

After full implementation:
- ✅ **80% automation** of IFIC proposal creation
- ✅ **<3 days** turnaround (vs 2-3 weeks manual)
- ✅ **>70% approval rate** (vs 30-40% DIY)
- ✅ **€150k ARR** potential in Year 1
- ✅ **Zero redundant tech suggestions** (stack intelligence)
- ✅ **4.0+ average merit score** (competitive positioning)

---

**STATUS**: Ready for Claude Code implementation 🚀

**OWNER**: Bilal @ AiParaTi  
**DATE**: 2025-11-01  
**VERSION**: 1.0 (MVP Spec)
