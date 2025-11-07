# ComplianceAgent Usage Guide

## Overview

The `ComplianceAgent` validates Portuguese funding applications (PT2030, PRR, SITCE) against official regulatory requirements. It uses **100% deterministic logic** - no AI/LLM is involved in compliance validation.

## Features

- ✅ **Financial Requirements**: VALF, TRF, investment limits
- ✅ **Company Eligibility**: Size classification, tax compliance, sector
- ✅ **Investment Validation**: Eligible vs ineligible costs
- ✅ **Funding Calculations**: Max rates with all bonuses (regional, innovation, sustainability)
- ✅ **Environmental Criteria**: DNSH compliance, sustainability scores
- ✅ **Social Criteria**: Job creation, gender equality, accessibility
- ✅ **Program-Specific Rules**: PRR digital/green transition, SITCE performance indicators
- ✅ **Recommendations**: Actionable suggestions to achieve compliance

## Quick Start

```python
from backend.agents.compliance_agent import (
    ComplianceAgent,
    ComplianceInput,
    CompanyInfo,
    InvestmentInfo,
    ProjectInfo,
    CompanySize,
    FundingProgram
)
from decimal import Decimal

# Initialize agent
agent = ComplianceAgent()

# Define company information
company = CompanyInfo(
    nif="123456789",
    company_size=CompanySize.SMALL,
    employees=25,
    annual_turnover=Decimal("5000000"),
    balance_sheet_total=Decimal("4000000"),
    sector="manufacturing",
    region="Porto",
    company_age_years=5,
    has_tax_debt=False,
    has_social_security_debt=False,
    in_difficulty=False
)

# Define investment information
investment = InvestmentInfo(
    total_investment=Decimal("500000"),
    eligible_investment=Decimal("450000"),
    funding_requested=Decimal("225000"),
    equipment_costs=Decimal("300000"),
    software_costs=Decimal("100000"),
    rd_costs=Decimal("50000"),
    investment_types=["equipment_acquisition", "it_infrastructure"],
    green_investment_percent=Decimal("20"),
    digital_investment_percent=Decimal("30")
)

# Define project information
project = ProjectInfo(
    project_name="Digital Manufacturing Upgrade",
    project_duration_years=5,
    jobs_created=3,
    valf=Decimal("-50000"),  # Must be negative
    trf=Decimal("3.5"),      # Must be < 4%
    sustainability_score=50,
    dnsh_compliant=True,
    gender_equality_plan=True,
    accessibility_compliant=True
)

# Validate compliance
input_data = ComplianceInput(
    program=FundingProgram.PT2030,
    company=company,
    investment=investment,
    project=project
)

result = agent.validate(input_data)

# Check results
print(f"Compliant: {result.is_compliant}")
print(f"Critical Failures: {result.critical_failures}")
print(f"Max Funding Rate: {result.max_funding_rate_percent}%")
print(f"Max Funding Amount: €{result.calculated_funding_amount:,.2f}")

# Review checks
for check in result.checks:
    status = "✅" if check.passed else "❌"
    print(f"{status} {check.check_name}: {check.message}")

# Get recommendations
for recommendation in result.recommendations:
    print(f"💡 {recommendation}")
```

## Output Example

```python
ComplianceResult(
    is_compliant=True,
    program='PT2030',
    critical_failures=0,
    warnings=1,
    max_funding_rate_percent=Decimal('70'),  # 55% base + 15% bonuses
    calculated_funding_amount=Decimal('315000'),
    requested_funding_valid=True,
    confidence_score=0.85,
    checks=[
        ComplianceCheck(
            check_id='FIN_001',
            check_name='VALF (NPV) Requirement',
            severity=CheckSeverity.CRITICAL,
            passed=True,
            expected_value='< 0 EUR',
            actual_value='-50000.00 EUR',
            message='VALF must be negative (< 0) to demonstrate project needs EU funding.',
            rule_reference='PT2030/financial_requirements/valf_max'
        ),
        # ... more checks
    ],
    recommendations=[
        '💡 You could request up to €90,000.00 more funding (max rate: 70%). Consider increasing funding request if project scope allows.',
        '✅ Project meets all compliance requirements. Proceed with application preparation.'
    ]
)
```

## Compliance Checks Performed

### Critical Checks (Must Pass)
1. **FIN_001**: VALF < 0 (negative NPV)
2. **FIN_002**: TRF < discount rate (typically 4%)
3. **FIN_003**: Investment within min/max limits
4. **COMP_001**: Company size classification valid
5. **COMP_002**: No tax debt
6. **COMP_003**: No social security debt
7. **COMP_004**: Company not in difficulty
8. **INV_001**: Eligible ≤ Total investment
9. **INV_002**: Investment types eligible
10. **FUND_001**: Funding rate within limits
11. **SECT_001**: Sector not excluded
12. **ENV_001**: DNSH compliance (if required)

### Warning Checks (Should Pass)
- **ENV_002**: Sustainability score
- **SOC_001**: Job creation targets
- **SOC_002**: Gender equality plan
- **SOC_003**: Accessibility compliance

### Informational Checks
- **SECT_002**: Sector priority level

## Funding Rate Calculation

The agent calculates maximum funding rate by combining:

**Base Rate** (by company size):
- Micro: 60%
- Small: 55%
- Medium: 50%
- Large: 40%

**Plus Bonuses:**
- Innovation (R&D costs > 0): +15%
- Digitalization (digital investment > 0): +10%
- Sustainability (green investment > 0): +10%
- Regional (Norte, Centro, Alentejo, etc.): +5% to +15%

**Maximum Total**: 75% (PT2030)

Example for Small Enterprise in Porto with R&D:
- Base: 55%
- Regional (Norte): +5%
- Innovation: +15%
- **Total: 75%** (capped at max)

## Program-Specific Requirements

### PT2030
- VALF < 0
- TRF < 4%
- Investment: €5,000 - €15,000,000
- Max funding: 75%

### PRR
- VALF ≤ 0
- TRF < 5%
- Investment: €10,000 - €50,000,000
- Digital investment ≥ 20%
- Green investment ≥ 37%
- Max funding: 85%

### SITCE
- VALF < 0
- TRF < 4%
- Investment: €25,000 - €10,000,000
- Job creation targets
- Max funding: 60%

## Integration with FinancialAgent

The ComplianceAgent works seamlessly with FinancialAgent:

```python
from backend.agents import FinancialAgent, ComplianceAgent

# 1. Calculate financial metrics
financial_agent = FinancialAgent(discount_rate=0.04)
financial_result = financial_agent.calculate(financial_input)

# 2. Use results for compliance validation
project_info = ProjectInfo(
    project_name="My Project",
    project_duration_years=5,
    jobs_created=3,
    valf=financial_result.valf,  # From FinancialAgent
    trf=financial_result.trf,    # From FinancialAgent
    dnsh_compliant=True
)

# 3. Validate compliance
compliance_agent = ComplianceAgent()
compliance_result = compliance_agent.validate(compliance_input)
```

## Error Handling

```python
try:
    result = agent.validate(input_data)
except ValueError as e:
    print(f"Invalid input: {e}")
except FileNotFoundError as e:
    print(f"Rules file not found: {e}")
```

## Custom Rules

You can use custom compliance rules:

```python
from pathlib import Path

custom_rules = Path("/path/to/custom_rules.json")
agent = ComplianceAgent(rules_path=custom_rules)
```

## Audit Trail

Every validation includes:
- `validation_timestamp`: When validation was performed
- `rules_version`: Version of rules used (e.g., "1.0.0")
- `validator_version`: ComplianceAgent version
- `confidence_score`: 0-1 confidence in result

## Best Practices

1. **Always validate VALF and TRF first** using FinancialAgent
2. **Provide complete data** for highest confidence scores
3. **Review recommendations** even when compliant
4. **Check funding calculations** to optimize request
5. **Use exact Decimal types** for financial values
6. **Validate company size** matches actual metrics

## Common Issues

### Issue: VALF is positive
**Solution**: Project is too profitable without funding. Reduce revenue projections or increase funding request.

### Issue: TRF exceeds discount rate
**Solution**: Project returns are too high. Extend timeline or reduce growth assumptions.

### Issue: Funding rate exceeds limits
**Solution**: Reduce funding request or increase eligible investment. Check `calculated_funding_amount` for maximum.

### Issue: Low confidence score
**Solution**: Provide complete investment breakdown, sustainability score, and job creation data.

## Testing

Run comprehensive tests:

```bash
pytest backend/tests/test_compliance_agent.py -v
```

## Support

For questions about compliance rules, refer to:
- `backend/regulations/pt2030_rules.json` - Complete rule definitions
- Official PT2030 documentation: https://portugal2030.pt
- PRR documentation: https://recuperarportugal.gov.pt

## Version History

- **v1.0.0** (2025-01-15): Initial release with PT2030/PRR/SITCE support
