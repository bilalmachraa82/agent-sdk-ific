#!/usr/bin/env python3
"""
Example usage of ComplianceAgent for PT2030 funding validation.
Demonstrates how to validate a project against Portuguese funding rules.
"""

from decimal import Decimal
from agents.compliance_agent import (
    ComplianceAgent,
    ComplianceInput,
    CompanyInfo,
    InvestmentInfo,
    ProjectInfo,
    CompanySize,
    FundingProgram
)


def example_compliant_project():
    """Example of a fully compliant PT2030 project."""
    print("="*80)
    print("EXAMPLE 1: Fully Compliant PT2030 Project")
    print("="*80)

    # Initialize agent
    agent = ComplianceAgent()

    # Define company (Small Manufacturing Company in Porto)
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

    # Define investment (€500k project with R&D and digitalization)
    investment = InvestmentInfo(
        total_investment=Decimal("500000"),
        eligible_investment=Decimal("450000"),
        funding_requested=Decimal("225000"),  # 50% of eligible
        equipment_costs=Decimal("300000"),
        software_costs=Decimal("100000"),
        rd_costs=Decimal("50000"),
        construction_costs=Decimal("50000"),
        investment_types=["equipment_acquisition", "it_infrastructure", "rd_equipment"],
        green_investment_percent=Decimal("20"),
        digital_investment_percent=Decimal("30")
    )

    # Define project (negative VALF, low TRF, creates jobs)
    project = ProjectInfo(
        project_name="Digital Manufacturing Upgrade",
        project_duration_years=5,
        jobs_created=3,
        jobs_maintained=25,
        valf=Decimal("-50000"),  # Negative NPV (good for PT2030)
        trf=Decimal("3.5"),      # Below 4% discount rate (good)
        sustainability_score=50,
        dnsh_compliant=True,
        gender_equality_plan=True,
        accessibility_compliant=True
    )

    # Validate
    input_data = ComplianceInput(
        program=FundingProgram.PT2030,
        company=company,
        investment=investment,
        project=project
    )

    result = agent.validate(input_data)

    # Display results
    print(f"\n📊 VALIDATION RESULTS")
    print(f"├─ Compliant: {'✅ YES' if result.is_compliant else '❌ NO'}")
    print(f"├─ Program: {result.program}")
    print(f"├─ Critical Failures: {result.critical_failures}")
    print(f"├─ Warnings: {result.warnings}")
    print(f"├─ Confidence: {result.confidence_score:.1%}")
    print(f"└─ Rules Version: {result.rules_version}")

    print(f"\n💰 FUNDING CALCULATION")
    print(f"├─ Max Funding Rate: {result.max_funding_rate_percent}%")
    print(f"├─ Max Funding Amount: €{result.calculated_funding_amount:,.2f}")
    print(f"├─ Requested Funding: €{investment.funding_requested:,.2f}")
    print(f"└─ Request Valid: {'✅ YES' if result.requested_funding_valid else '❌ NO'}")

    print(f"\n📋 COMPLIANCE CHECKS ({len(result.checks)} total)")

    # Group checks by severity
    critical = [c for c in result.checks if c.severity.value == "critical"]
    warnings = [c for c in result.checks if c.severity.value == "warning"]
    info = [c for c in result.checks if c.severity.value == "info"]

    print(f"\n🔴 CRITICAL CHECKS ({len(critical)})")
    for check in critical:
        status = "✅" if check.passed else "❌"
        print(f"  {status} {check.check_name}")
        if not check.passed:
            print(f"     Expected: {check.expected_value}")
            print(f"     Actual: {check.actual_value}")

    if warnings:
        print(f"\n🟡 WARNINGS ({len(warnings)})")
        for check in warnings:
            status = "✅" if check.passed else "⚠️"
            print(f"  {status} {check.check_name}")

    if info:
        print(f"\n🔵 INFORMATIONAL ({len(info)})")
        for check in info:
            print(f"  ℹ️  {check.check_name}: {check.actual_value}")

    print(f"\n💡 RECOMMENDATIONS")
    for i, rec in enumerate(result.recommendations, 1):
        print(f"  {i}. {rec}")

    print()


def example_non_compliant_project():
    """Example of a non-compliant project with positive VALF."""
    print("="*80)
    print("EXAMPLE 2: Non-Compliant Project (Positive VALF)")
    print("="*80)

    agent = ComplianceAgent()

    company = CompanyInfo(
        nif="987654321",
        company_size=CompanySize.MEDIUM,
        employees=100,
        annual_turnover=Decimal("20000000"),
        balance_sheet_total=Decimal("15000000"),
        sector="ict",
        region="Lisboa",
        company_age_years=10,
        has_tax_debt=False,
        has_social_security_debt=False,
        in_difficulty=False
    )

    investment = InvestmentInfo(
        total_investment=Decimal("1000000"),
        eligible_investment=Decimal("900000"),
        funding_requested=Decimal("450000"),
        equipment_costs=Decimal("600000"),
        software_costs=Decimal("300000"),
        rd_costs=Decimal("100000"),
        investment_types=["it_infrastructure", "software_licenses"],
        green_investment_percent=Decimal("10"),
        digital_investment_percent=Decimal("80")
    )

    # This project is TOO profitable - doesn't need EU funding!
    project = ProjectInfo(
        project_name="Profitable SaaS Platform",
        project_duration_years=5,
        jobs_created=5,
        valf=Decimal("150000"),  # ❌ Positive VALF (bad)
        trf=Decimal("8.5"),      # ❌ Above 4% discount rate (bad)
        sustainability_score=40,
        dnsh_compliant=True,
        gender_equality_plan=False,
        accessibility_compliant=True
    )

    input_data = ComplianceInput(
        program=FundingProgram.PT2030,
        company=company,
        investment=investment,
        project=project
    )

    result = agent.validate(input_data)

    print(f"\n📊 VALIDATION RESULTS")
    print(f"├─ Compliant: {'✅ YES' if result.is_compliant else '❌ NO'}")
    print(f"├─ Critical Failures: {result.critical_failures}")
    print(f"└─ Warnings: {result.warnings}")

    print(f"\n❌ FAILED CHECKS")
    failed = [c for c in result.checks if not c.passed and c.severity.value == "critical"]
    for check in failed:
        print(f"  ❌ {check.check_name}")
        print(f"     {check.message}")
        print(f"     Expected: {check.expected_value}, Got: {check.actual_value}")
        print()

    print(f"💡 RECOMMENDATIONS")
    for i, rec in enumerate(result.recommendations, 1):
        print(f"  {i}. {rec}")

    print()


def example_prr_validation():
    """Example of PRR validation with green/digital requirements."""
    print("="*80)
    print("EXAMPLE 3: PRR (Recovery Plan) Validation")
    print("="*80)

    agent = ComplianceAgent()

    company = CompanyInfo(
        nif="111222333",
        company_size=CompanySize.SMALL,
        employees=30,
        annual_turnover=Decimal("6000000"),
        balance_sheet_total=Decimal("5000000"),
        sector="renewable_energy",
        region="Alentejo",
        company_age_years=3,
        has_tax_debt=False,
        has_social_security_debt=False,
        in_difficulty=False
    )

    investment = InvestmentInfo(
        total_investment=Decimal("800000"),
        eligible_investment=Decimal("750000"),
        funding_requested=Decimal("600000"),  # 80% of eligible
        equipment_costs=Decimal("500000"),
        software_costs=Decimal("150000"),
        rd_costs=Decimal("100000"),
        consulting_costs=Decimal("50000"),
        investment_types=["renewable_energy", "digitalization_tools"],
        green_investment_percent=Decimal("65"),   # ✅ Above 37% required
        digital_investment_percent=Decimal("25")  # ✅ Above 20% required
    )

    project = ProjectInfo(
        project_name="Solar Energy & IoT Monitoring System",
        project_duration_years=7,
        jobs_created=4,
        valf=Decimal("-30000"),
        trf=Decimal("4.5"),  # Below 5% for PRR (ok)
        sustainability_score=85,
        dnsh_compliant=True,
        gender_equality_plan=True,
        accessibility_compliant=True
    )

    input_data = ComplianceInput(
        program=FundingProgram.PRR,  # Using PRR instead of PT2030
        company=company,
        investment=investment,
        project=project
    )

    result = agent.validate(input_data)

    print(f"\n📊 PRR VALIDATION RESULTS")
    print(f"├─ Compliant: {'✅ YES' if result.is_compliant else '❌ NO'}")
    print(f"├─ Max Funding Rate: {result.max_funding_rate_percent}%")
    print(f"└─ Max Funding: €{result.calculated_funding_amount:,.2f}")

    # Check PRR-specific requirements
    prr_checks = [c for c in result.checks if c.check_id.startswith("PRR_")]
    if prr_checks:
        print(f"\n🇪🇺 PRR-SPECIFIC REQUIREMENTS")
        for check in prr_checks:
            status = "✅" if check.passed else "❌"
            print(f"  {status} {check.check_name}: {check.message}")

    print()


if __name__ == "__main__":
    # Run all examples
    example_compliant_project()
    example_non_compliant_project()
    example_prr_validation()

    print("="*80)
    print("✅ All examples completed!")
    print("="*80)
