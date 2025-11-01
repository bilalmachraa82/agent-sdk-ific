"""
IFIC Orchestrator Agent
Coordinates all subagents to process funding applications
"""

import uuid
from datetime import datetime
from typing import Any
from loguru import logger
from anthropic import Anthropic

from core.config import settings
from core.schemas import (
    CompanyInput,
    ProjectInput,
    BudgetInput,
    ImpactMetrics,
    FundingApplication,
    ApplicationStatus,
    AuditTrail,
)
from agents.researcher import CompanyResearchAgent
from agents.stack_intel import StackIntelligenceAgent
from agents.financial import FinancialAnalysisAgent
from agents.writer import ProposalWriterAgent
from agents.scorer import MeritScoringAgent
from agents.validator import ComplianceValidatorAgent


class IFICOrchestrator:
    """
    Main orchestrator for IFIC funding applications
    
    Workflow:
    1. Company Research (eInforma → Racius → Website)
    2. Stack Intelligence (redundancy detection)
    3. Budget Gate (tier calculation)
    4. Financial Deep Dive (IES parsing, ratios)
    5. Use Case Generation
    6. Merit Scoring (MP calculation with scenarios)
    7. Compliance Validation (RGPD/DNSH/duplo financiamento)
    8. Proposal Generation (6-module HTML + CSVs)
    """

    def __init__(self):
        self.client = Anthropic(api_key=settings.anthropic_api_key)
        self.session_id = str(uuid.uuid4())
        
        # Initialize subagents
        self.researcher = CompanyResearchAgent(self.client)
        self.stack_intel = StackIntelligenceAgent(self.client)
        self.financial = FinancialAnalysisAgent(self.client)
        self.writer = ProposalWriterAgent(self.client)
        self.scorer = MeritScoringAgent(self.client)
        self.validator = ComplianceValidatorAgent(self.client)
        
        logger.info(f"Orchestrator initialized | session_id={self.session_id}")

    async def process_application(
        self,
        company_input: CompanyInput,
        project_input: ProjectInput,
        budget_input: BudgetInput,
        impact_metrics: ImpactMetrics,
        user_id: str | None = None,
    ) -> FundingApplication:
        """
        Complete end-to-end processing of IFIC application
        
        Args:
            company_input: Company basic information
            project_input: Project scope and timeline
            budget_input: Budget constraints
            impact_metrics: Expected impact (jobs, VAB growth)
            user_id: Optional user identifier
            
        Returns:
            Complete FundingApplication with all artifacts
            
        Raises:
            ValidationError: If critical validation fails
            ValueError: If budget constraints violated
        """
        timestamps = {"started": datetime.utcnow()}
        agent_calls = []
        
        logger.info(f"Starting application processing | company={company_input.nome}")
        
        try:
            # ================================================================
            # PHASE 1: Company Research
            # ================================================================
            timestamps["research_start"] = datetime.utcnow()
            logger.info("Phase 1: Company Research")
            
            company_data = await self.researcher.fetch_company_data(
                nome=company_input.nome,
                nif=company_input.nif,
                url=str(company_input.url) if company_input.url else None,
                cae=company_input.cae,
            )
            
            agent_calls.append({
                "agent": "researcher",
                "action": "fetch_company_data",
                "timestamp": datetime.utcnow().isoformat(),
                "sources": list(company_data.data_sources.keys()),
            })
            
            timestamps["research_complete"] = datetime.utcnow()
            
            # ================================================================
            # PHASE 2: Stack Intelligence
            # ================================================================
            timestamps["stack_analysis_start"] = datetime.utcnow()
            logger.info("Phase 2: Stack Intelligence Analysis")
            
            stack_analysis = await self.stack_intel.analyze_stack(
                existing_stack=company_data.tech_stack,
                industry_cae=company_data.cae,
                company_size=company_data.dimensao,
            )
            
            agent_calls.append({
                "agent": "stack_intel",
                "action": "analyze_stack",
                "timestamp": datetime.utcnow().isoformat(),
                "redundancies_found": len(stack_analysis.get("redundancias_detectadas", [])),
            })
            
            timestamps["stack_analysis_complete"] = datetime.utcnow()
            
            # ================================================================
            # PHASE 3: Budget Gate Validation
            # ================================================================
            timestamps["budget_gate_start"] = datetime.utcnow()
            logger.info("Phase 3: Budget Gate Validation")
            
            self._validate_budget_gate(budget_input)
            
            budget_scenarios = self._calculate_budget_tiers(
                teto_max=budget_input.teto_max_investimento,
                cofinanciamento=budget_input.cofinanciamento_disponivel,
                preferencias=budget_input.preferencias,
                stack_recommendations=stack_analysis.get("recomendacoes", []),
            )
            
            timestamps["budget_gate_complete"] = datetime.utcnow()
            
            # ================================================================
            # PHASE 4: Financial Analysis (if files provided)
            # ================================================================
            timestamps["financial_start"] = datetime.utcnow()
            logger.info("Phase 4: Financial Deep Dive")
            
            financial_model = await self.financial.analyze_financials(
                company_data=company_data,
                budget_scenarios=budget_scenarios,
            )
            
            agent_calls.append({
                "agent": "financial",
                "action": "analyze_financials",
                "timestamp": datetime.utcnow().isoformat(),
            })
            
            timestamps["financial_complete"] = datetime.utcnow()
            
            # ================================================================
            # PHASE 5: Use Case Generation
            # ================================================================
            timestamps["use_cases_start"] = datetime.utcnow()
            logger.info("Phase 5: Use Case Generation")
            
            use_cases = await self.writer.generate_use_cases(
                company_data=company_data,
                project_input=project_input,
                stack_analysis=stack_analysis,
            )
            
            training_plan = await self.writer.generate_training_plan(
                use_cases=use_cases,
                company_size=company_data.dimensao,
            )
            
            agent_calls.append({
                "agent": "writer",
                "action": "generate_use_cases",
                "timestamp": datetime.utcnow().isoformat(),
                "use_cases_count": len(use_cases),
            })
            
            timestamps["use_cases_complete"] = datetime.utcnow()
            
            # ================================================================
            # PHASE 6: Merit Scoring
            # ================================================================
            timestamps["scoring_start"] = datetime.utcnow()
            logger.info("Phase 6: Merit Scoring Calculation")
            
            merit_scoring = await self.scorer.calculate_merit_score(
                project_quality_indicators=financial_model.get("quality_indicators", {}),
                impact_metrics=impact_metrics,
            )
            
            scoring_scenarios = await self.scorer.generate_scenarios(
                base_score=merit_scoring,
                job_range=[0, 1, 2],
                vab_range=[0, 5, 8, 12],
            )
            
            agent_calls.append({
                "agent": "scorer",
                "action": "calculate_merit_score",
                "timestamp": datetime.utcnow().isoformat(),
                "mp_final": merit_scoring.merit_point_final,
            })
            
            timestamps["scoring_complete"] = datetime.utcnow()
            
            # ================================================================
            # PHASE 7: Compliance Validation
            # ================================================================
            timestamps["validation_start"] = datetime.utcnow()
            logger.info("Phase 7: Compliance Validation")
            
            compliance_report = await self.validator.validate_compliance(
                company_data=company_data,
                project_input=project_input,
                budget_scenarios=budget_scenarios,
                use_cases=use_cases,
            )
            
            agent_calls.append({
                "agent": "validator",
                "action": "validate_compliance",
                "timestamp": datetime.utcnow().isoformat(),
                "status": compliance_report.overall_status,
            })
            
            timestamps["validation_complete"] = datetime.utcnow()
            
            # ================================================================
            # PHASE 8: Proposal Generation
            # ================================================================
            timestamps["proposal_start"] = datetime.utcnow()
            logger.info("Phase 8: Proposal Artifact Generation")
            
            artifacts = await self.writer.generate_proposal_artifacts(
                company_data=company_data,
                project_input=project_input,
                budget_scenarios=budget_scenarios,
                use_cases=use_cases,
                training_plan=training_plan,
                merit_scoring=merit_scoring,
                scoring_scenarios=scoring_scenarios,
                compliance_report=compliance_report,
                financial_model=financial_model,
            )
            
            agent_calls.append({
                "agent": "writer",
                "action": "generate_proposal_artifacts",
                "timestamp": datetime.utcnow().isoformat(),
                "artifacts_count": len(artifacts),
            })
            
            timestamps["proposal_complete"] = datetime.utcnow()
            timestamps["finished"] = datetime.utcnow()
            
            # ================================================================
            # FINAL: Assemble Complete Application
            # ================================================================
            
            audit_trail = AuditTrail(
                session_id=self.session_id,
                user_id=user_id,
                company_nif=company_data.nif,
                timestamps=timestamps,
                data_sources=company_data.data_sources,
                agent_calls=agent_calls,
                validations=compliance_report.validations,
                final_status=ApplicationStatus.READY,
            )
            
            application = FundingApplication(
                application_id=str(uuid.uuid4()),
                status=ApplicationStatus.READY,
                company=company_data,
                project=project_input,
                budget=budget_input,
                impact=impact_metrics,
                budget_scenarios=budget_scenarios,
                use_cases=use_cases,
                training_plan=training_plan,
                merit_scoring=merit_scoring,
                scoring_scenarios=scoring_scenarios,
                compliance=compliance_report,
                artifacts=artifacts,
                audit_trail=audit_trail,
            )
            
            duration = (timestamps["finished"] - timestamps["started"]).total_seconds()
            logger.success(
                f"Application processing complete | "
                f"duration={duration:.1f}s | "
                f"mp={merit_scoring.merit_point_final} | "
                f"status={compliance_report.overall_status}"
            )
            
            return application
            
        except Exception as e:
            logger.error(f"Application processing failed | error={str(e)}")
            raise

    def _validate_budget_gate(self, budget: BudgetInput) -> None:
        """
        Validate budget constraints before processing
        
        Raises:
            ValueError: If critical budget constraint violated
        """
        if budget.teto_max_investimento < settings.ific_min_eligible:
            raise ValueError(
                f"Teto inviável: €{budget.teto_max_investimento:,.2f} < "
                f"mínimo €{settings.ific_min_eligible:,.2f}"
            )
        
        min_cofinancing = budget.teto_max_investimento * (1 - settings.ific_cofinancing_rate)
        if budget.cofinanciamento_disponivel < min_cofinancing:
            raise ValueError(
                f"Cofinanciamento insuficiente: €{budget.cofinanciamento_disponivel:,.2f} < "
                f"mínimo €{min_cofinancing:,.2f} (25%)"
            )
        
        logger.info("Budget gate validation passed")

    def _calculate_budget_tiers(
        self,
        teto_max: float,
        cofinanciamento: float,
        preferencias: list[str],
        stack_recommendations: list[dict[str, Any]],
    ) -> list[Any]:
        """
        Calculate 3 budget tiers (Essencial, Recomendado, Completo)
        
        Returns:
            List of BudgetScenario objects
        """
        # Implementation delegated to financial agent
        # This is a placeholder that will be filled by actual calculation logic
        logger.info(f"Calculating budget tiers | teto={teto_max:,.2f}")
        return []
