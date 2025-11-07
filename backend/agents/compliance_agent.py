"""
ComplianceAgent - PT2030/PRR/SITCE Funding Compliance Validation

Validates project compliance against Portuguese funding program rules.
100% deterministic logic - NO AI/LLM involved.

Checks:
- Financial metrics (VALF, TRF)
- Company eligibility (size, sector, legal status)
- Investment eligibility (type, amount, costs)
- Funding rate limits
- Environmental and social criteria
- State aid rules
"""

from typing import Dict, List, Optional, Tuple
from datetime import datetime
from decimal import Decimal
from enum import Enum
import json
from pathlib import Path

from pydantic import BaseModel, Field, field_validator


class CompanySize(str, Enum):
    """Company size classification for funding rates."""
    MICRO = "micro"
    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"


class FundingProgram(str, Enum):
    """Portuguese funding programs."""
    PT2030 = "pt2030"
    PRR = "prr"
    SITCE = "sitce"


class CheckSeverity(str, Enum):
    """Severity level for compliance checks."""
    CRITICAL = "critical"  # Must pass to be compliant
    WARNING = "warning"    # Should pass but not blocking
    INFO = "info"          # Informational only


class ComplianceCheck(BaseModel):
    """Individual compliance check result."""
    check_id: str = Field(..., description="Unique identifier for this check")
    check_name: str = Field(..., description="Human-readable check name")
    severity: CheckSeverity = Field(..., description="Severity level")
    passed: bool = Field(..., description="Whether check passed")
    expected_value: Optional[str] = Field(None, description="Expected value")
    actual_value: Optional[str] = Field(None, description="Actual value")
    message: str = Field(..., description="Detailed message")
    rule_reference: Optional[str] = Field(None, description="Reference to regulation")


class CompanyInfo(BaseModel):
    """Company information for eligibility checks."""
    nif: str = Field(..., min_length=9, max_length=9, description="Portuguese Tax ID")
    company_size: CompanySize = Field(..., description="Company size classification")
    employees: int = Field(..., ge=0, description="Number of employees")
    annual_turnover: Decimal = Field(..., ge=0, description="Annual turnover in EUR")
    balance_sheet_total: Decimal = Field(..., ge=0, description="Balance sheet total in EUR")
    sector: str = Field(..., description="Business sector (e.g., 'manufacturing', 'ict')")
    region: str = Field(..., description="Geographic region (e.g., 'Porto', 'Lisboa')")
    company_age_years: int = Field(..., ge=0, description="Age of company in years")
    has_tax_debt: bool = Field(default=False, description="Whether company has tax debts")
    has_social_security_debt: bool = Field(default=False, description="Whether company has social security debts")
    in_difficulty: bool = Field(default=False, description="Whether company is in difficulty per EU definition")


class InvestmentInfo(BaseModel):
    """Investment information for eligibility checks."""
    total_investment: Decimal = Field(..., gt=0, description="Total project investment in EUR")
    eligible_investment: Decimal = Field(..., gt=0, description="Eligible investment in EUR")
    funding_requested: Decimal = Field(..., gt=0, description="Funding amount requested in EUR")

    # Investment breakdown
    equipment_costs: Decimal = Field(default=0, description="Equipment acquisition costs")
    software_costs: Decimal = Field(default=0, description="Software and IT costs")
    construction_costs: Decimal = Field(default=0, description="Building construction/renovation")
    rd_costs: Decimal = Field(default=0, description="R&D costs")
    training_costs: Decimal = Field(default=0, description="Training costs")
    consulting_costs: Decimal = Field(default=0, description="Consulting costs")
    other_costs: Decimal = Field(default=0, description="Other eligible costs")

    # Investment type flags
    investment_types: List[str] = Field(default_factory=list, description="Types of investment")

    # Sustainability
    green_investment_percent: Decimal = Field(default=0, ge=0, le=100, description="% of green investment")
    digital_investment_percent: Decimal = Field(default=0, ge=0, le=100, description="% of digital investment")

    @field_validator('funding_requested')
    @classmethod
    def validate_funding(cls, v, info):
        """Ensure funding doesn't exceed eligible investment."""
        eligible = info.data.get('eligible_investment')
        if eligible and v > eligible:
            raise ValueError("Funding requested cannot exceed eligible investment")
        return v


class ProjectInfo(BaseModel):
    """Project information for compliance checks."""
    project_name: str
    project_duration_years: int = Field(..., ge=1, le=20)
    jobs_created: int = Field(default=0, ge=0, description="Number of jobs created")
    jobs_maintained: int = Field(default=0, ge=0, description="Number of jobs maintained")

    # Financial metrics (from FinancialAgent)
    valf: Decimal = Field(..., description="Financial NPV in EUR")
    trf: Decimal = Field(..., description="Financial IRR in %")

    # Environmental and social
    sustainability_score: Optional[int] = Field(None, ge=0, le=100, description="Sustainability score (0-100)")
    dnsh_compliant: bool = Field(default=False, description="Do No Significant Harm compliance")
    gender_equality_plan: bool = Field(default=False, description="Has gender equality plan")
    accessibility_compliant: bool = Field(default=False, description="Accessibility standards compliant")


class ComplianceInput(BaseModel):
    """Complete input for compliance validation."""
    program: FundingProgram = Field(..., description="Funding program to validate against")
    company: CompanyInfo
    investment: InvestmentInfo
    project: ProjectInfo


class ComplianceResult(BaseModel):
    """Complete compliance validation result."""
    is_compliant: bool = Field(..., description="Overall compliance status")
    program: str = Field(..., description="Funding program validated against")
    checks: List[ComplianceCheck] = Field(..., description="All compliance checks performed")
    recommendations: List[str] = Field(default_factory=list, description="Recommendations for achieving compliance")
    confidence_score: float = Field(..., ge=0, le=1, description="Confidence in result (0-1)")

    # Detailed results
    critical_failures: int = Field(..., description="Number of critical check failures")
    warnings: int = Field(..., description="Number of warnings")

    # Funding calculations
    max_funding_rate_percent: Decimal = Field(..., description="Maximum funding rate allowed (%)")
    calculated_funding_amount: Decimal = Field(..., description="Calculated max funding amount in EUR")
    requested_funding_valid: bool = Field(..., description="Whether requested funding is within limits")

    # Metadata
    validation_timestamp: datetime = Field(default_factory=datetime.utcnow)
    rules_version: str = Field(..., description="Version of rules used")
    validator_version: str = Field(..., description="Version of ComplianceAgent")


class ComplianceAgent:
    """
    Deterministic compliance validation agent.

    Validates projects against PT2030/PRR/SITCE rules using pure logic.
    NO AI/LLM is used - only rule-based validation.
    """

    VERSION = "1.0.0"
    AGENT_NAME = "ComplianceAgent"

    def __init__(self, rules_path: Optional[Path] = None):
        """
        Initialize ComplianceAgent.

        Args:
            rules_path: Path to PT2030 rules JSON file. If None, uses default location.
        """
        if rules_path is None:
            # Default to regulations/pt2030_rules.json
            rules_path = Path(__file__).parent.parent / "regulations" / "pt2030_rules.json"

        self.rules_path = rules_path
        self.rules = self._load_rules()

    def _load_rules(self) -> Dict:
        """Load compliance rules from JSON file."""
        if not self.rules_path.exists():
            raise FileNotFoundError(f"Rules file not found: {self.rules_path}")

        with open(self.rules_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def validate(self, input_data: ComplianceInput) -> ComplianceResult:
        """
        Perform complete compliance validation.

        Args:
            input_data: Complete input data for validation

        Returns:
            ComplianceResult with all checks and recommendations
        """
        program_key = input_data.program.value.upper()
        program_rules = self.rules['programs'].get(program_key)

        if not program_rules:
            raise ValueError(f"Unknown funding program: {input_data.program}")

        checks: List[ComplianceCheck] = []

        # Run all compliance checks
        checks.extend(self._check_financial_requirements(input_data, program_rules))
        checks.extend(self._check_company_eligibility(input_data, program_rules))
        checks.extend(self._check_investment_eligibility(input_data, program_rules))
        checks.extend(self._check_funding_rates(input_data, program_rules))
        checks.extend(self._check_sector_eligibility(input_data, program_rules))
        checks.extend(self._check_environmental_criteria(input_data, program_rules))
        checks.extend(self._check_social_criteria(input_data, program_rules))

        # Program-specific checks
        if input_data.program == FundingProgram.PRR:
            checks.extend(self._check_prr_specific(input_data, program_rules))
        elif input_data.program == FundingProgram.SITCE:
            checks.extend(self._check_sitce_specific(input_data, program_rules))

        # Calculate results
        critical_failures = sum(1 for c in checks if c.severity == CheckSeverity.CRITICAL and not c.passed)
        warnings = sum(1 for c in checks if c.severity == CheckSeverity.WARNING and not c.passed)
        is_compliant = critical_failures == 0

        # Calculate max funding
        max_funding_rate, calculated_funding = self._calculate_max_funding(input_data, program_rules)
        requested_valid = input_data.investment.funding_requested <= calculated_funding

        # Generate recommendations
        recommendations = self._generate_recommendations(checks, input_data, program_rules)

        # Calculate confidence score
        confidence = self._calculate_confidence(checks, input_data)

        return ComplianceResult(
            is_compliant=is_compliant,
            program=program_key,
            checks=checks,
            recommendations=recommendations,
            confidence_score=confidence,
            critical_failures=critical_failures,
            warnings=warnings,
            max_funding_rate_percent=max_funding_rate,
            calculated_funding_amount=calculated_funding,
            requested_funding_valid=requested_valid,
            rules_version=self.rules.get('version', 'unknown'),
            validator_version=self.VERSION
        )

    def _check_financial_requirements(self, input_data: ComplianceInput, program_rules: Dict) -> List[ComplianceCheck]:
        """Check VALF and TRF requirements."""
        checks = []
        fin_req = program_rules['financial_requirements']

        # VALF Check
        valf_max = fin_req['valf_max']
        valf_passed = float(input_data.project.valf) < valf_max
        checks.append(ComplianceCheck(
            check_id="FIN_001",
            check_name="VALF (NPV) Requirement",
            severity=CheckSeverity.CRITICAL,
            passed=valf_passed,
            expected_value=f"< {valf_max} EUR",
            actual_value=f"{input_data.project.valf:.2f} EUR",
            message=f"VALF must be negative (< {valf_max}) to demonstrate project needs EU funding. {fin_req['valf_description']}",
            rule_reference=f"{input_data.program.value.upper()}/financial_requirements/valf_max"
        ))

        # TRF Check
        trf_max = fin_req['trf_max_percent']
        trf_passed = float(input_data.project.trf) < trf_max
        checks.append(ComplianceCheck(
            check_id="FIN_002",
            check_name="TRF (IRR) Requirement",
            severity=CheckSeverity.CRITICAL,
            passed=trf_passed,
            expected_value=f"< {trf_max}%",
            actual_value=f"{input_data.project.trf:.2f}%",
            message=f"TRF must be less than {trf_max}% discount rate. {fin_req['trf_description']}",
            rule_reference=f"{input_data.program.value.upper()}/financial_requirements/trf_max_percent"
        ))

        # Investment amount limits
        min_inv = fin_req.get('minimum_investment', 0)
        max_inv = fin_req.get('maximum_investment', float('inf'))

        total_inv = float(input_data.investment.total_investment)
        inv_in_range = min_inv <= total_inv <= max_inv

        checks.append(ComplianceCheck(
            check_id="FIN_003",
            check_name="Investment Amount Limits",
            severity=CheckSeverity.CRITICAL,
            passed=inv_in_range,
            expected_value=f"{min_inv:,.0f} - {max_inv:,.0f} EUR",
            actual_value=f"{total_inv:,.0f} EUR",
            message=f"Total investment must be between {min_inv:,.0f} and {max_inv:,.0f} EUR",
            rule_reference=f"{input_data.program.value.upper()}/financial_requirements/investment_limits"
        ))

        return checks

    def _check_company_eligibility(self, input_data: ComplianceInput, program_rules: Dict) -> List[ComplianceCheck]:
        """Check company eligibility criteria."""
        checks = []
        company = input_data.company

        # Company size validation
        size_criteria = program_rules.get('company_size_criteria', {}).get(company.company_size.value, {})
        if size_criteria:
            size_valid = True
            size_msg = []

            if 'employees_max' in size_criteria and company.employees > size_criteria['employees_max']:
                size_valid = False
                size_msg.append(f"employees ({company.employees}) exceeds max ({size_criteria['employees_max']})")

            if 'turnover_max' in size_criteria and company.annual_turnover > size_criteria['turnover_max']:
                size_valid = False
                size_msg.append(f"turnover ({company.annual_turnover:,.0f}) exceeds max ({size_criteria['turnover_max']:,.0f})")

            if 'balance_sheet_max' in size_criteria and company.balance_sheet_total > size_criteria['balance_sheet_max']:
                size_valid = False
                size_msg.append(f"balance sheet ({company.balance_sheet_total:,.0f}) exceeds max ({size_criteria['balance_sheet_max']:,.0f})")

            checks.append(ComplianceCheck(
                check_id="COMP_001",
                check_name="Company Size Classification",
                severity=CheckSeverity.CRITICAL,
                passed=size_valid,
                expected_value=f"{company.company_size.value} criteria met",
                actual_value=", ".join(size_msg) if size_msg else "criteria met",
                message=f"Company must meet {company.company_size.value} enterprise criteria",
                rule_reference=f"{input_data.program.value.upper()}/company_size_criteria/{company.company_size.value}"
            ))

        # Tax and social security compliance
        checks.append(ComplianceCheck(
            check_id="COMP_002",
            check_name="Tax Compliance",
            severity=CheckSeverity.CRITICAL,
            passed=not company.has_tax_debt,
            expected_value="No tax debt",
            actual_value="Tax debt exists" if company.has_tax_debt else "Compliant",
            message="Company must have no outstanding tax debts",
            rule_reference="common_exclusions/excluded_companies/tax_debt"
        ))

        checks.append(ComplianceCheck(
            check_id="COMP_003",
            check_name="Social Security Compliance",
            severity=CheckSeverity.CRITICAL,
            passed=not company.has_social_security_debt,
            expected_value="No social security debt",
            actual_value="Social security debt exists" if company.has_social_security_debt else "Compliant",
            message="Company must have no outstanding social security debts",
            rule_reference="common_exclusions/excluded_companies/social_security_debt"
        ))

        # Company in difficulty check
        checks.append(ComplianceCheck(
            check_id="COMP_004",
            check_name="Company Financial Health",
            severity=CheckSeverity.CRITICAL,
            passed=not company.in_difficulty,
            expected_value="Not in difficulty",
            actual_value="Company in difficulty" if company.in_difficulty else "Healthy",
            message="Company must not be classified as 'undertaking in difficulty' per EU definition",
            rule_reference="common_exclusions/excluded_companies/companies_in_difficulty"
        ))

        return checks

    def _check_investment_eligibility(self, input_data: ComplianceInput, program_rules: Dict) -> List[ComplianceCheck]:
        """Check investment type eligibility."""
        checks = []

        # Check that eligible investment doesn't exceed total
        eligible_valid = input_data.investment.eligible_investment <= input_data.investment.total_investment
        checks.append(ComplianceCheck(
            check_id="INV_001",
            check_name="Eligible Investment Amount",
            severity=CheckSeverity.CRITICAL,
            passed=eligible_valid,
            expected_value=f"<= {input_data.investment.total_investment:,.2f} EUR",
            actual_value=f"{input_data.investment.eligible_investment:,.2f} EUR",
            message="Eligible investment cannot exceed total investment",
            rule_reference="general/investment_validation"
        ))

        # Check investment types against eligible list
        eligible_investments = program_rules.get('eligible_investments', [])
        ineligible_investments = program_rules.get('ineligible_investments', [])

        invalid_types = [t for t in input_data.investment.investment_types if t in ineligible_investments]

        checks.append(ComplianceCheck(
            check_id="INV_002",
            check_name="Investment Type Eligibility",
            severity=CheckSeverity.CRITICAL,
            passed=len(invalid_types) == 0,
            expected_value="All types eligible",
            actual_value=f"Ineligible types: {', '.join(invalid_types)}" if invalid_types else "All eligible",
            message=f"Investment types must be eligible. Ineligible types found: {invalid_types}" if invalid_types else "All investment types are eligible",
            rule_reference=f"{input_data.program.value.upper()}/eligible_investments"
        ))

        return checks

    def _check_funding_rates(self, input_data: ComplianceInput, program_rules: Dict) -> List[ComplianceCheck]:
        """Check funding rate limits."""
        checks = []

        funding_rates = program_rules.get('funding_rates', {})

        # Get base rate for company size
        size_key = f"{input_data.company.company_size.value}_max_percent"
        if input_data.company.company_size == CompanySize.LARGE:
            size_key = "large_enterprise_max_percent"
        elif input_data.company.company_size == CompanySize.MEDIUM:
            size_key = "medium_enterprise_max_percent"
        elif input_data.company.company_size == CompanySize.SMALL:
            size_key = "small_enterprise_max_percent"
        elif input_data.company.company_size == CompanySize.MICRO:
            size_key = "micro_enterprise_max_percent"

        base_rate = funding_rates.get(size_key, funding_rates.get('default_max_percent', 50))

        # Calculate actual funding rate requested
        requested_rate = (float(input_data.investment.funding_requested) /
                         float(input_data.investment.eligible_investment) * 100)

        # Check against maximum (with bonuses calculated separately)
        max_total = funding_rates.get('max_total_percent', 100)
        rate_valid = requested_rate <= max_total

        checks.append(ComplianceCheck(
            check_id="FUND_001",
            check_name="Funding Rate Limit",
            severity=CheckSeverity.CRITICAL,
            passed=rate_valid,
            expected_value=f"<= {max_total}%",
            actual_value=f"{requested_rate:.2f}%",
            message=f"Funding rate must not exceed {max_total}% (base: {base_rate}%, potential bonuses available)",
            rule_reference=f"{input_data.program.value.upper()}/funding_rates"
        ))

        return checks

    def _check_sector_eligibility(self, input_data: ComplianceInput, program_rules: Dict) -> List[ComplianceCheck]:
        """Check sector eligibility and priority."""
        checks = []

        sector_priorities = program_rules.get('sector_priorities', {})
        excluded_sectors = sector_priorities.get('excluded_sectors', [])

        # Check if sector is excluded
        sector_excluded = input_data.company.sector.lower() in [s.lower() for s in excluded_sectors]

        checks.append(ComplianceCheck(
            check_id="SECT_001",
            check_name="Sector Eligibility",
            severity=CheckSeverity.CRITICAL,
            passed=not sector_excluded,
            expected_value="Eligible sector",
            actual_value=f"Excluded sector: {input_data.company.sector}" if sector_excluded else f"Eligible: {input_data.company.sector}",
            message=f"Sector must not be in excluded list. Excluded: {excluded_sectors}",
            rule_reference=f"{input_data.program.value.upper()}/sector_priorities/excluded_sectors"
        ))

        # Determine priority level (informational)
        priority_level = "unknown"
        for level in ['high_priority', 'medium_priority', 'low_priority']:
            sectors = sector_priorities.get(level, [])
            if input_data.company.sector.lower() in [s.lower() for s in sectors]:
                priority_level = level
                break

        checks.append(ComplianceCheck(
            check_id="SECT_002",
            check_name="Sector Priority Level",
            severity=CheckSeverity.INFO,
            passed=priority_level in ['high_priority', 'medium_priority'],
            expected_value="High or medium priority",
            actual_value=priority_level,
            message=f"Sector '{input_data.company.sector}' is classified as {priority_level}",
            rule_reference=f"{input_data.program.value.upper()}/sector_priorities"
        ))

        return checks

    def _check_environmental_criteria(self, input_data: ComplianceInput, program_rules: Dict) -> List[ComplianceCheck]:
        """Check environmental compliance criteria."""
        checks = []

        env_criteria = program_rules.get('environmental_criteria', {})

        if not env_criteria:
            return checks

        # DNSH compliance (Do No Significant Harm)
        if env_criteria.get('dnsh_compliance_required', False):
            checks.append(ComplianceCheck(
                check_id="ENV_001",
                check_name="DNSH Compliance",
                severity=CheckSeverity.CRITICAL,
                passed=input_data.project.dnsh_compliant,
                expected_value="DNSH compliant",
                actual_value="Compliant" if input_data.project.dnsh_compliant else "Not compliant",
                message=f"Project must comply with DNSH principle: {env_criteria.get('dnsh_description', 'Do No Significant Harm')}",
                rule_reference=f"{input_data.program.value.upper()}/environmental_criteria/dnsh_compliance_required"
            ))

        # Sustainability score
        min_score = env_criteria.get('minimum_sustainability_score')
        if min_score and input_data.project.sustainability_score is not None:
            score_valid = input_data.project.sustainability_score >= min_score
            checks.append(ComplianceCheck(
                check_id="ENV_002",
                check_name="Sustainability Score",
                severity=CheckSeverity.WARNING,
                passed=score_valid,
                expected_value=f">= {min_score}",
                actual_value=str(input_data.project.sustainability_score),
                message=f"Sustainability score should be at least {min_score}/100",
                rule_reference=f"{input_data.program.value.upper()}/environmental_criteria/minimum_sustainability_score"
            ))

        return checks

    def _check_social_criteria(self, input_data: ComplianceInput, program_rules: Dict) -> List[ComplianceCheck]:
        """Check social compliance criteria."""
        checks = []

        social_criteria = program_rules.get('social_criteria', {})

        if not social_criteria:
            return checks

        # Job creation
        min_jobs = social_criteria.get('minimum_job_creation', 0)
        if min_jobs > 0:
            jobs_valid = input_data.project.jobs_created >= min_jobs
            checks.append(ComplianceCheck(
                check_id="SOC_001",
                check_name="Job Creation Target",
                severity=CheckSeverity.WARNING,
                passed=jobs_valid,
                expected_value=f">= {min_jobs} jobs",
                actual_value=f"{input_data.project.jobs_created} jobs",
                message=f"Project should create at least {min_jobs} job(s)",
                rule_reference=f"{input_data.program.value.upper()}/social_criteria/minimum_job_creation"
            ))

        # Gender equality
        if social_criteria.get('gender_equality_required', False):
            checks.append(ComplianceCheck(
                check_id="SOC_002",
                check_name="Gender Equality Plan",
                severity=CheckSeverity.WARNING,
                passed=input_data.project.gender_equality_plan,
                expected_value="Has plan",
                actual_value="Has plan" if input_data.project.gender_equality_plan else "No plan",
                message="Project should have a gender equality plan",
                rule_reference=f"{input_data.program.value.upper()}/social_criteria/gender_equality_required"
            ))

        # Accessibility
        if social_criteria.get('accessibility_compliance_required', False):
            checks.append(ComplianceCheck(
                check_id="SOC_003",
                check_name="Accessibility Compliance",
                severity=CheckSeverity.WARNING,
                passed=input_data.project.accessibility_compliant,
                expected_value="Compliant",
                actual_value="Compliant" if input_data.project.accessibility_compliant else "Not compliant",
                message="Project should comply with accessibility standards",
                rule_reference=f"{input_data.program.value.upper()}/social_criteria/accessibility_compliance_required"
            ))

        return checks

    def _check_prr_specific(self, input_data: ComplianceInput, program_rules: Dict) -> List[ComplianceCheck]:
        """PRR-specific compliance checks."""
        checks = []

        # Digital transition minimum
        digital_req = program_rules.get('digital_transition_requirements', {})
        min_digital = digital_req.get('minimum_investment_percent', 0)

        if min_digital > 0:
            digital_valid = input_data.investment.digital_investment_percent >= min_digital
            checks.append(ComplianceCheck(
                check_id="PRR_001",
                check_name="Digital Transition Investment",
                severity=CheckSeverity.CRITICAL,
                passed=digital_valid,
                expected_value=f">= {min_digital}%",
                actual_value=f"{input_data.investment.digital_investment_percent}%",
                message=f"PRR requires at least {min_digital}% of investment in digital transition",
                rule_reference="PRR/digital_transition_requirements/minimum_investment_percent"
            ))

        # Green transition minimum
        green_req = program_rules.get('green_transition_requirements', {})
        min_green = green_req.get('minimum_investment_percent', 0)

        if min_green > 0:
            green_valid = input_data.investment.green_investment_percent >= min_green
            checks.append(ComplianceCheck(
                check_id="PRR_002",
                check_name="Green Transition Investment",
                severity=CheckSeverity.CRITICAL,
                passed=green_valid,
                expected_value=f">= {min_green}%",
                actual_value=f"{input_data.investment.green_investment_percent}%",
                message=f"PRR requires at least {min_green}% of investment in green transition",
                rule_reference="PRR/green_transition_requirements/minimum_investment_percent"
            ))

        return checks

    def _check_sitce_specific(self, input_data: ComplianceInput, program_rules: Dict) -> List[ComplianceCheck]:
        """SITCE-specific compliance checks."""
        checks = []

        # SITCE has different intervention typologies with specific requirements
        # This would need additional input data to fully validate

        # Performance indicators check (informational)
        perf_indicators = program_rules.get('performance_indicators', {})

        if perf_indicators.get('jobs_created_minimum', 0) > 0:
            min_jobs = perf_indicators['jobs_created_minimum']
            jobs_valid = input_data.project.jobs_created >= min_jobs
            checks.append(ComplianceCheck(
                check_id="SITCE_001",
                check_name="SITCE Job Creation Target",
                severity=CheckSeverity.WARNING,
                passed=jobs_valid,
                expected_value=f">= {min_jobs} jobs",
                actual_value=f"{input_data.project.jobs_created} jobs",
                message=f"SITCE expects at least {min_jobs} jobs created",
                rule_reference="SITCE/performance_indicators/jobs_created_minimum"
            ))

        return checks

    def _calculate_max_funding(self, input_data: ComplianceInput, program_rules: Dict) -> Tuple[Decimal, Decimal]:
        """
        Calculate maximum funding rate and amount with all bonuses.

        Returns:
            Tuple of (max_rate_percent, max_funding_amount)
        """
        funding_rates = program_rules.get('funding_rates', {})

        # Get base rate for company size
        size_key = f"{input_data.company.company_size.value}_max_percent"
        if input_data.company.company_size == CompanySize.LARGE:
            size_key = "large_enterprise_max_percent"
        elif input_data.company.company_size == CompanySize.MEDIUM:
            size_key = "medium_enterprise_max_percent"
        elif input_data.company.company_size == CompanySize.SMALL:
            size_key = "small_enterprise_max_percent"
        elif input_data.company.company_size == CompanySize.MICRO:
            size_key = "micro_enterprise_max_percent"

        base_rate = Decimal(str(funding_rates.get(size_key, funding_rates.get('default_max_percent', 50))))

        # Add bonuses
        total_bonus = Decimal('0')

        # Innovation bonus (if R&D costs > 0)
        if input_data.investment.rd_costs > 0:
            innovation_bonus = Decimal(str(funding_rates.get('innovation_bonus_percent', 0)))
            total_bonus += innovation_bonus

        # Digitalization bonus
        if input_data.investment.digital_investment_percent > 0:
            digital_bonus = Decimal(str(funding_rates.get('digitalization_bonus_percent', 0)))
            total_bonus += digital_bonus

        # Sustainability bonus
        if input_data.investment.green_investment_percent > 0:
            sustainability_bonus = Decimal(str(funding_rates.get('sustainability_bonus_percent', 0)))
            total_bonus += sustainability_bonus

        # Regional bonus
        regional_incentives = program_rules.get('regional_incentives', {})
        for region_key, region_data in regional_incentives.items():
            if input_data.company.region in region_data.get('regions', []):
                regional_bonus = Decimal(str(region_data.get('bonus_percent', 0)))
                total_bonus += regional_bonus
                break

        # Calculate final rate (capped at max_total_percent)
        max_rate = base_rate + total_bonus
        max_total = Decimal(str(funding_rates.get('max_total_percent', 100)))
        max_rate = min(max_rate, max_total)

        # Calculate max funding amount
        max_funding = input_data.investment.eligible_investment * (max_rate / Decimal('100'))

        return max_rate, max_funding

    def _generate_recommendations(self, checks: List[ComplianceCheck],
                                 input_data: ComplianceInput,
                                 program_rules: Dict) -> List[str]:
        """Generate recommendations to achieve compliance."""
        recommendations = []

        # Check for critical failures and provide guidance
        for check in checks:
            if not check.passed and check.severity == CheckSeverity.CRITICAL:
                if check.check_id == "FIN_001":  # VALF too high
                    recommendations.append(
                        "⚠️ VALF is not negative. Consider: (1) Reducing revenue projections, "
                        "(2) Increasing operating costs to be more conservative, or "
                        "(3) Requesting higher funding amount to reduce project viability without subsidy."
                    )
                elif check.check_id == "FIN_002":  # TRF too high
                    recommendations.append(
                        "⚠️ TRF exceeds discount rate. Consider: (1) Extending project timeline, "
                        "(2) Reducing revenue growth assumptions, or "
                        "(3) Increasing initial investment to lower returns."
                    )
                elif check.check_id == "FUND_001":  # Funding rate too high
                    recommendations.append(
                        f"⚠️ Funding rate exceeds limits. Reduce funding requested or increase eligible investment. "
                        f"Maximum funding available: {self._calculate_max_funding(input_data, program_rules)[1]:,.2f} EUR"
                    )
                elif check.check_id.startswith("COMP_"):  # Company eligibility
                    recommendations.append(f"⚠️ Company eligibility issue: {check.message}")

        # Positive recommendations for optimization
        max_rate, max_funding = self._calculate_max_funding(input_data, program_rules)
        if input_data.investment.funding_requested < max_funding:
            difference = max_funding - input_data.investment.funding_requested
            recommendations.append(
                f"💡 You could request up to {difference:,.2f} EUR more funding (max rate: {max_rate}%). "
                "Consider increasing funding request if project scope allows."
            )

        # Regional bonus opportunities
        regional_incentives = program_rules.get('regional_incentives', {})
        current_bonus = Decimal('0')
        for region_key, region_data in regional_incentives.items():
            if input_data.company.region in region_data.get('regions', []):
                current_bonus = Decimal(str(region_data.get('bonus_percent', 0)))
                break

        if current_bonus == 0:
            max_regional = max((Decimal(str(r.get('bonus_percent', 0)))
                              for r in regional_incentives.values()), default=Decimal('0'))
            if max_regional > 0:
                recommendations.append(
                    f"💡 Consider locating project in regions with higher bonuses (up to {max_regional}% available in Açores/Madeira)"
                )

        # Innovation bonus
        if input_data.investment.rd_costs == 0:
            innovation_bonus = program_rules.get('funding_rates', {}).get('innovation_bonus_percent', 0)
            if innovation_bonus > 0:
                recommendations.append(
                    f"💡 Include R&D activities to qualify for {innovation_bonus}% innovation bonus"
                )

        # Sustainability recommendations
        if input_data.investment.green_investment_percent < 30:
            recommendations.append(
                "💡 Increase green/sustainable investment to qualify for sustainability bonuses and improve competitiveness"
            )

        # General advice
        if not recommendations:
            recommendations.append("✅ Project meets all compliance requirements. Proceed with application preparation.")

        return recommendations

    def _calculate_confidence(self, checks: List[ComplianceCheck], input_data: ComplianceInput) -> float:
        """
        Calculate confidence score in validation result.

        Confidence is reduced by:
        - Missing optional data
        - Edge case values
        - Assumptions made during validation
        """
        confidence = 1.0

        # Reduce confidence if sustainability data is missing
        if input_data.project.sustainability_score is None:
            confidence -= 0.05

        # Reduce confidence if investment breakdown is incomplete
        total_costs = (
            input_data.investment.equipment_costs +
            input_data.investment.software_costs +
            input_data.investment.construction_costs +
            input_data.investment.rd_costs +
            input_data.investment.training_costs +
            input_data.investment.consulting_costs +
            input_data.investment.other_costs
        )

        if total_costs == 0:
            confidence -= 0.1  # No detailed breakdown provided
        elif abs(total_costs - input_data.investment.total_investment) > 100:
            confidence -= 0.05  # Breakdown doesn't match total

        # Reduce confidence if investment types not specified
        if not input_data.investment.investment_types:
            confidence -= 0.1

        # Reduce confidence if jobs data is minimal
        if input_data.project.jobs_created == 0 and input_data.project.jobs_maintained == 0:
            confidence -= 0.05

        return max(0.0, min(1.0, confidence))
