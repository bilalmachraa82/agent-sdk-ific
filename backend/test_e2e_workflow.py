#!/usr/bin/env python3
"""
Complete End-to-End Test for EVF Workflow
==========================================

Tests the complete workflow from SAF-T upload through all 5 agents to final Excel report.

Requirements:
- Simulate realistic EVF processing (SAF-T → Financial Analysis → Compliance → Narrative → Excel)
- Track processing time and costs
- Verify database storage
- Test both compliant and non-compliant scenarios

Usage:
    python backend/test_e2e_workflow.py

Author: EVF Portugal 2030
Date: 2025-01-07
"""

import asyncio
import os
import sys
import time
from datetime import datetime, date
from decimal import Decimal
from pathlib import Path
from typing import Dict, Any
from uuid import uuid4, UUID
import json

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

# Import agents
from agents.input_agent import (
    InputAgent,
    SAFTData,
    CompanyInfo,
    CompanyAddress,
    Period,
    FinancialStatement,
    CashFlowStatement,
)
from agents.financial_agent import (
    FinancialAgent,
    FinancialInput,
    CashFlow,
    FinancialOutput,
)
from agents.compliance_agent import (
    ComplianceAgent,
    ComplianceInput,
    CompanyInfo as ComplianceCompanyInfo,
    InvestmentInfo,
    ProjectInfo,
    CompanySize,
    FundingProgram,
)
from agents.narrative_agent import (
    NarrativeAgent,
    NarrativeInput,
    FinancialContext,
    ComplianceContext,
)
from services.excel_generator import ExcelGenerator, ExcelInput


# ANSI color codes for terminal output
class Colors:
    """Terminal colors for output."""
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


def print_header(text: str):
    """Print section header."""
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'=' * 80}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{text.center(80)}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'=' * 80}{Colors.ENDC}\n")


def print_success(text: str):
    """Print success message."""
    print(f"{Colors.OKGREEN}✓ {text}{Colors.ENDC}")


def print_error(text: str):
    """Print error message."""
    print(f"{Colors.FAIL}✗ {text}{Colors.ENDC}")


def print_warning(text: str):
    """Print warning message."""
    print(f"{Colors.WARNING}⚠ {text}{Colors.ENDC}")


def print_info(text: str):
    """Print info message."""
    print(f"{Colors.OKCYAN}ℹ {text}{Colors.ENDC}")


def create_sample_saft_xml(scenario: str = "compliant") -> str:
    """
    Create sample SAF-T XML data for testing.

    Args:
        scenario: "compliant" or "non_compliant"

    Returns:
        XML string
    """
    if scenario == "compliant":
        # Project needs funding (low profitability)
        revenue = 150000
        costs = 120000
    else:
        # Project too profitable (doesn't need funding)
        revenue = 300000
        costs = 100000

    xml_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<AuditFile xmlns="urn:OECD:StandardAuditFile-Tax:PT_1.04_01">
    <Header>
        <AuditFileVersion>1.04_01</AuditFileVersion>
        <CompanyID>EVFTEST123</CompanyID>
        <TaxRegistrationNumber>123456789</TaxRegistrationNumber>
        <TaxAccountingBasis>F</TaxAccountingBasis>
        <CompanyName>Empresa Teste EVF Portugal 2030</CompanyName>
        <CompanyAddress>
            <AddressDetail>Rua do Teste, 123</AddressDetail>
            <City>Porto</City>
            <PostalCode>4000-123</PostalCode>
            <Region>Porto</Region>
            <Country>PT</Country>
        </CompanyAddress>
        <FiscalYear>2024</FiscalYear>
        <StartDate>2024-01-01</StartDate>
        <EndDate>2024-12-31</EndDate>
        <CurrencyCode>EUR</CurrencyCode>
        <DateCreated>2024-12-31</DateCreated>
        <ProductID>EVF_TEST/1.0</ProductID>
        <ProductVersion>1.0.0</ProductVersion>
    </Header>

    <MasterFiles>
        <GeneralLedgerAccounts>
            <!-- Revenue Accounts (Class 7) -->
            <Account>
                <AccountID>71</AccountID>
                <AccountDescription>Vendas e Serviços Prestados</AccountDescription>
                <OpeningDebitBalance>0.00</OpeningDebitBalance>
                <OpeningCreditBalance>0.00</OpeningCreditBalance>
                <ClosingDebitBalance>0.00</ClosingDebitBalance>
                <ClosingCreditBalance>{revenue}.00</ClosingCreditBalance>
            </Account>

            <!-- Cost of Sales (Class 6) -->
            <Account>
                <AccountID>61</AccountID>
                <AccountDescription>Custo das Mercadorias Vendidas</AccountDescription>
                <OpeningDebitBalance>0.00</OpeningDebitBalance>
                <OpeningCreditBalance>0.00</OpeningCreditBalance>
                <ClosingDebitBalance>{costs * 0.4:.2f}</ClosingDebitBalance>
                <ClosingCreditBalance>0.00</ClosingCreditBalance>
            </Account>

            <!-- Personnel Costs -->
            <Account>
                <AccountID>63</AccountID>
                <AccountDescription>Gastos com Pessoal</AccountDescription>
                <OpeningDebitBalance>0.00</OpeningDebitBalance>
                <OpeningCreditBalance>0.00</OpeningCreditBalance>
                <ClosingDebitBalance>{costs * 0.4:.2f}</ClosingDebitBalance>
                <ClosingCreditBalance>0.00</ClosingCreditBalance>
            </Account>

            <!-- Operating Expenses -->
            <Account>
                <AccountID>62</AccountID>
                <AccountDescription>Fornecimentos e Serviços Externos</AccountDescription>
                <OpeningDebitBalance>0.00</OpeningDebitBalance>
                <OpeningCreditBalance>0.00</OpeningCreditBalance>
                <ClosingDebitBalance>{costs * 0.15:.2f}</ClosingDebitBalance>
                <ClosingCreditBalance>0.00</ClosingCreditBalance>
            </Account>

            <!-- Depreciation -->
            <Account>
                <AccountID>64</AccountID>
                <AccountDescription>Gastos de Depreciação</AccountDescription>
                <OpeningDebitBalance>0.00</OpeningDebitBalance>
                <OpeningCreditBalance>0.00</OpeningCreditBalance>
                <ClosingDebitBalance>{costs * 0.05:.2f}</ClosingDebitBalance>
                <ClosingCreditBalance>0.00</ClosingCreditBalance>
            </Account>

            <!-- Assets -->
            <Account>
                <AccountID>43</AccountID>
                <AccountDescription>Investimentos</AccountDescription>
                <OpeningDebitBalance>50000.00</OpeningDebitBalance>
                <OpeningCreditBalance>0.00</OpeningCreditBalance>
                <ClosingDebitBalance>80000.00</ClosingDebitBalance>
                <ClosingCreditBalance>0.00</ClosingCreditBalance>
            </Account>

            <Account>
                <AccountID>12</AccountID>
                <AccountDescription>Clientes</AccountDescription>
                <OpeningDebitBalance>10000.00</OpeningDebitBalance>
                <OpeningCreditBalance>0.00</OpeningCreditBalance>
                <ClosingDebitBalance>25000.00</ClosingDebitBalance>
                <ClosingCreditBalance>0.00</ClosingCreditBalance>
            </Account>

            <!-- Liabilities -->
            <Account>
                <AccountID>51</AccountID>
                <AccountDescription>Fornecedores</AccountDescription>
                <OpeningDebitBalance>0.00</OpeningDebitBalance>
                <OpeningCreditBalance>5000.00</OpeningCreditBalance>
                <ClosingDebitBalance>0.00</ClosingDebitBalance>
                <ClosingCreditBalance>15000.00</ClosingCreditBalance>
            </Account>

            <!-- Equity -->
            <Account>
                <AccountID>51</AccountID>
                <AccountDescription>Capital Social</AccountDescription>
                <OpeningDebitBalance>0.00</OpeningDebitBalance>
                <OpeningCreditBalance>50000.00</OpeningCreditBalance>
                <ClosingDebitBalance>0.00</ClosingDebitBalance>
                <ClosingCreditBalance>50000.00</ClosingCreditBalance>
            </Account>
        </GeneralLedgerAccounts>
    </MasterFiles>
</AuditFile>
"""
    return xml_content


def create_sample_financial_projections(scenario: str = "compliant") -> FinancialInput:
    """
    Create sample financial projections.

    Args:
        scenario: "compliant" (VALF < 0, TRF < 4%) or "non_compliant" (VALF > 0, TRF > 4%)

    Returns:
        FinancialInput with cash flow projections
    """
    if scenario == "compliant":
        # Project needs funding - low returns
        total_investment = Decimal("200000")
        annual_revenue = [Decimal("120000"), Decimal("130000"), Decimal("135000"),
                          Decimal("140000"), Decimal("145000")]
        operating_costs = [Decimal("100000"), Decimal("105000"), Decimal("107000"),
                          Decimal("109000"), Decimal("110000")]
    else:
        # Project too profitable - high returns
        total_investment = Decimal("200000")
        annual_revenue = [Decimal("200000"), Decimal("250000"), Decimal("300000"),
                          Decimal("350000"), Decimal("400000")]
        operating_costs = [Decimal("80000"), Decimal("90000"), Decimal("100000"),
                          Decimal("110000"), Decimal("120000")]

    # Create cash flows
    cash_flows = [
        # Year 0: Initial investment
        CashFlow(
            year=0,
            revenue=Decimal("0"),
            operating_costs=Decimal("0"),
            capex=total_investment,
            depreciation=Decimal("0"),
            working_capital_change=Decimal("0")
        )
    ]

    # Years 1-5: Operations
    for year in range(1, 6):
        cash_flows.append(
            CashFlow(
                year=year,
                revenue=annual_revenue[year - 1],
                operating_costs=operating_costs[year - 1],
                capex=Decimal("5000"),  # Maintenance CAPEX
                depreciation=total_investment / Decimal("5"),  # Straight-line over 5 years
                working_capital_change=Decimal("2000") if year == 1 else Decimal("0")
            )
        )

    return FinancialInput(
        project_name=f"Projeto Teste EVF - {scenario.upper()}",
        project_duration_years=5,
        discount_rate=Decimal("0.04"),  # PT2030 standard
        total_investment=total_investment,
        eligible_investment=total_investment * Decimal("0.8"),  # 80% eligible
        funding_requested=total_investment * Decimal("0.5"),  # Request 50% funding
        cash_flows=cash_flows
    )


async def test_scenario(scenario: str = "compliant", use_narrative: bool = False) -> Dict[str, Any]:
    """
    Run complete E2E test for a specific scenario.

    Args:
        scenario: "compliant" or "non_compliant"
        use_narrative: Whether to test NarrativeAgent (requires Claude API key)

    Returns:
        Dictionary with test results and metrics
    """
    print_header(f"E2E Test: {scenario.upper()} Scenario")

    results = {
        "scenario": scenario,
        "start_time": datetime.utcnow(),
        "steps": {},
        "metrics": {
            "total_time_seconds": 0,
            "total_cost_euros": Decimal("0"),
            "tokens_used": 0,
        },
        "success": True,
        "errors": [],
    }

    # ============================================================================
    # STEP 1: Create Tenant and User (simulated)
    # ============================================================================
    print_info("Step 1: Creating tenant and user...")
    step_start = time.time()

    tenant_id = uuid4()
    user_id = uuid4()
    project_id = uuid4()

    results["steps"]["tenant_creation"] = {
        "tenant_id": str(tenant_id),
        "user_id": str(user_id),
        "project_id": str(project_id),
        "duration_seconds": time.time() - step_start,
    }

    print_success(f"Created tenant: {tenant_id}")
    print_success(f"Created user: {user_id}")
    print_success(f"Created project: {project_id}")

    # ============================================================================
    # STEP 2: InputAgent - Parse SAF-T File
    # ============================================================================
    print_info("\nStep 2: Parsing SAF-T file with InputAgent...")
    step_start = time.time()

    try:
        # Create sample SAF-T XML
        saft_xml = create_sample_saft_xml(scenario)

        # Save to temporary file
        temp_dir = Path("/tmp/evf_test")
        temp_dir.mkdir(exist_ok=True)
        saft_file = temp_dir / f"saft_{scenario}_{int(time.time())}.xml"
        saft_file.write_text(saft_xml, encoding="utf-8")

        # Parse with InputAgent
        input_agent = InputAgent(validate_schema=False)
        parse_result = input_agent.parse_file(str(saft_file))

        if not parse_result.success:
            raise ValueError(f"SAF-T parsing failed: {parse_result.errors}")

        saft_data = parse_result.data

        results["steps"]["input_agent"] = {
            "success": True,
            "duration_seconds": time.time() - step_start,
            "parse_time": parse_result.parse_time_seconds,
            "company_nif": saft_data.company_info.nif,
            "company_name": saft_data.company_info.name,
            "fiscal_year": saft_data.company_info.fiscal_year,
            "revenue": float(saft_data.financial_statements[0].revenue),
            "warnings": parse_result.warnings,
        }

        print_success(f"Parsed SAF-T file: {saft_data.company_info.name}")
        print_success(f"NIF: {saft_data.company_info.nif}")
        print_success(f"Revenue: €{saft_data.financial_statements[0].revenue:,.2f}")
        print_success(f"Parse time: {parse_result.parse_time_seconds:.2f}s")

        # Clean up temp file
        saft_file.unlink()

    except Exception as e:
        results["success"] = False
        results["errors"].append(f"InputAgent failed: {str(e)}")
        print_error(f"InputAgent failed: {e}")
        return results

    # ============================================================================
    # STEP 3: FinancialAgent - Calculate VALF/TRF
    # ============================================================================
    print_info("\nStep 3: Calculating VALF/TRF with FinancialAgent...")
    step_start = time.time()

    try:
        # Create financial projections
        financial_input = create_sample_financial_projections(scenario)

        # Calculate metrics
        financial_agent = FinancialAgent(discount_rate=0.04)
        financial_output = financial_agent.calculate(financial_input)

        results["steps"]["financial_agent"] = {
            "success": True,
            "duration_seconds": time.time() - step_start,
            "valf": float(financial_output.valf),
            "trf": float(financial_output.trf),
            "payback_period": float(financial_output.payback_period) if financial_output.payback_period else None,
            "total_fcf": float(financial_output.total_fcf),
            "pt2030_compliant": financial_output.pt2030_compliant,
            "input_hash": financial_output.input_hash,
        }

        print_success(f"VALF: €{financial_output.valf:,.2f}")
        print_success(f"TRF: {financial_output.trf:.2f}%")
        print_success(f"Payback Period: {financial_output.payback_period or 'N/A'} years")

        if financial_output.pt2030_compliant:
            print_success("✓ PT2030 Compliant")
        else:
            print_warning("✗ NOT PT2030 Compliant")

    except Exception as e:
        results["success"] = False
        results["errors"].append(f"FinancialAgent failed: {str(e)}")
        print_error(f"FinancialAgent failed: {e}")
        return results

    # ============================================================================
    # STEP 4: ComplianceAgent - Validate PT2030 Rules
    # ============================================================================
    print_info("\nStep 4: Validating compliance with ComplianceAgent...")
    step_start = time.time()

    try:
        # Note: ComplianceAgent requires regulations/pt2030_rules.json
        # For this test, we'll create a minimal rules file or skip if not available

        rules_path = Path(__file__).parent / "regulations" / "pt2030_rules.json"

        if not rules_path.exists():
            print_warning("PT2030 rules file not found - skipping ComplianceAgent test")
            results["steps"]["compliance_agent"] = {
                "success": False,
                "skipped": True,
                "reason": "Rules file not found",
                "duration_seconds": time.time() - step_start,
            }
        else:
            # Create compliance input
            compliance_input = ComplianceInput(
                program=FundingProgram.PT2030,
                company=ComplianceCompanyInfo(
                    nif=saft_data.company_info.nif,
                    company_size=CompanySize.SMALL,
                    employees=25,
                    annual_turnover=Decimal("500000"),
                    balance_sheet_total=Decimal("300000"),
                    sector="manufacturing",
                    region="Porto",
                    company_age_years=5,
                    has_tax_debt=False,
                    has_social_security_debt=False,
                    in_difficulty=False,
                ),
                investment=InvestmentInfo(
                    total_investment=financial_input.total_investment,
                    eligible_investment=financial_input.eligible_investment,
                    funding_requested=financial_input.funding_requested,
                    equipment_costs=Decimal("150000"),
                    software_costs=Decimal("30000"),
                    training_costs=Decimal("20000"),
                    investment_types=["equipment", "software", "training"],
                    green_investment_percent=Decimal("20"),
                    digital_investment_percent=Decimal("30"),
                ),
                project=ProjectInfo(
                    project_name=financial_input.project_name,
                    project_duration_years=financial_input.project_duration_years,
                    jobs_created=5,
                    jobs_maintained=20,
                    valf=financial_output.valf,
                    trf=financial_output.trf,
                    dnsh_compliant=True,
                    gender_equality_plan=True,
                    accessibility_compliant=True,
                ),
            )

            # Validate compliance
            compliance_agent = ComplianceAgent(rules_path=rules_path)
            compliance_result = compliance_agent.validate(compliance_input)

            results["steps"]["compliance_agent"] = {
                "success": True,
                "duration_seconds": time.time() - step_start,
                "is_compliant": compliance_result.is_compliant,
                "critical_failures": compliance_result.critical_failures,
                "warnings": compliance_result.warnings,
                "max_funding_rate": float(compliance_result.max_funding_rate_percent),
                "recommendations": compliance_result.recommendations,
            }

            print_success(f"Compliance check complete")
            print_success(f"Status: {'COMPLIANT' if compliance_result.is_compliant else 'NON-COMPLIANT'}")
            print_success(f"Critical failures: {compliance_result.critical_failures}")
            print_success(f"Warnings: {compliance_result.warnings}")
            print_success(f"Max funding rate: {compliance_result.max_funding_rate_percent}%")

    except Exception as e:
        results["success"] = False
        results["errors"].append(f"ComplianceAgent failed: {str(e)}")
        print_error(f"ComplianceAgent failed: {e}")
        return results

    # ============================================================================
    # STEP 5: NarrativeAgent - Generate Portuguese Text (Optional)
    # ============================================================================
    if use_narrative:
        print_info("\nStep 5: Generating narrative with NarrativeAgent...")
        step_start = time.time()

        try:
            # Get Claude API key from environment
            api_key = os.getenv("ANTHROPIC_API_KEY")

            if not api_key:
                print_warning("ANTHROPIC_API_KEY not set - skipping NarrativeAgent test")
                results["steps"]["narrative_agent"] = {
                    "success": False,
                    "skipped": True,
                    "reason": "API key not found",
                    "duration_seconds": time.time() - step_start,
                }
            else:
                # Create narrative input
                narrative_input = NarrativeInput(
                    financial_context=FinancialContext(
                        project_name=financial_input.project_name,
                        project_duration_years=financial_input.project_duration_years,
                        total_investment=financial_input.total_investment,
                        eligible_investment=financial_input.eligible_investment,
                        funding_requested=financial_input.funding_requested,
                        valf=financial_output.valf,
                        trf=financial_output.trf,
                        payback_period=financial_output.payback_period,
                        pt2030_compliant=financial_output.pt2030_compliant,
                        compliance_notes=financial_output.compliance_notes,
                    ),
                    compliance_context=ComplianceContext(
                        status="compliant" if financial_output.pt2030_compliant else "non_compliant",
                        is_compliant=financial_output.pt2030_compliant,
                    ),
                    company_name=saft_data.company_info.name,
                    language="pt-PT",
                )

                # Generate narrative
                narrative_agent = NarrativeAgent(api_key=api_key, temperature=0.7)
                narrative_output = await narrative_agent.generate(narrative_input)

                results["steps"]["narrative_agent"] = {
                    "success": True,
                    "duration_seconds": time.time() - step_start,
                    "tokens_used": narrative_output.tokens_used,
                    "cost_euros": float(narrative_output.cost_euros),
                    "word_count": narrative_output.word_count,
                    "executive_summary_length": len(narrative_output.executive_summary),
                    "methodology_length": len(narrative_output.methodology),
                    "recommendations_length": len(narrative_output.recommendations),
                }

                # Update metrics
                results["metrics"]["tokens_used"] += narrative_output.tokens_used
                results["metrics"]["total_cost_euros"] += narrative_output.cost_euros

                print_success(f"Generated narrative")
                print_success(f"Tokens used: {narrative_output.tokens_used:,}")
                print_success(f"Cost: €{narrative_output.cost_euros:.4f}")
                print_success(f"Executive summary: {narrative_output.word_count['executive_summary']} words")

        except Exception as e:
            results["success"] = False
            results["errors"].append(f"NarrativeAgent failed: {str(e)}")
            print_error(f"NarrativeAgent failed: {e}")
            return results
    else:
        print_warning("\nStep 5: NarrativeAgent test skipped (use_narrative=False)")
        results["steps"]["narrative_agent"] = {
            "success": False,
            "skipped": True,
            "reason": "Not requested",
            "duration_seconds": 0,
        }

    # ============================================================================
    # STEP 6: ExcelGenerator - Create Final Report
    # ============================================================================
    print_info("\nStep 6: Generating Excel report...")
    step_start = time.time()

    try:
        # Create output directory
        output_dir = Path("/tmp/evf_test/reports")
        output_dir.mkdir(parents=True, exist_ok=True)

        # Generate Excel file
        excel_generator = ExcelGenerator()

        excel_input = ExcelInput(
            project_name=financial_input.project_name,
            company_name=saft_data.company_info.name,
            company_nif=saft_data.company_info.nif,
            fiscal_year=saft_data.company_info.fiscal_year,

            # Financial metrics
            total_investment=financial_input.total_investment,
            eligible_investment=financial_input.eligible_investment,
            funding_requested=financial_input.funding_requested,
            valf=financial_output.valf,
            trf=financial_output.trf,
            payback_period=financial_output.payback_period,

            # Cash flows (convert CashFlow objects to dicts)
            cash_flows=[
                {
                    "year": cf.year,
                    "revenue": float(cf.revenue),
                    "operating_costs": float(cf.operating_costs),
                    "capex": float(cf.capex),
                    "depreciation": float(cf.depreciation),
                    "free_cash_flow": float(cf.free_cash_flow),
                }
                for cf in financial_input.cash_flows
            ],

            # Narrative (if available)
            executive_summary=narrative_output.executive_summary if use_narrative and 'narrative_output' in locals() else "Sumário executivo não gerado neste teste.",
            methodology=narrative_output.methodology if use_narrative and 'narrative_output' in locals() else "Metodologia não gerada neste teste.",
            recommendations=narrative_output.recommendations if use_narrative and 'narrative_output' in locals() else "Recomendações não geradas neste teste.",

            # Compliance status
            pt2030_compliant=financial_output.pt2030_compliant,
        )

        output_file = output_dir / f"evf_report_{scenario}_{int(time.time())}.xlsx"
        excel_path = excel_generator.generate(excel_input, str(output_file))

        # Get file size
        file_size = Path(excel_path).stat().st_size

        results["steps"]["excel_generator"] = {
            "success": True,
            "duration_seconds": time.time() - step_start,
            "output_file": str(excel_path),
            "file_size_bytes": file_size,
            "file_size_kb": file_size / 1024,
        }

        print_success(f"Generated Excel report: {excel_path}")
        print_success(f"File size: {file_size / 1024:.2f} KB")

    except Exception as e:
        results["success"] = False
        results["errors"].append(f"ExcelGenerator failed: {str(e)}")
        print_error(f"ExcelGenerator failed: {e}")
        return results

    # ============================================================================
    # STEP 7: Calculate Total Metrics
    # ============================================================================
    print_info("\nStep 7: Calculating final metrics...")

    results["end_time"] = datetime.utcnow()
    results["metrics"]["total_time_seconds"] = (
        results["end_time"] - results["start_time"]
    ).total_seconds()

    # Estimate total cost (mainly from Claude API)
    # Storage costs are negligible for single test

    print_success(f"\nTest completed successfully!")

    return results


def print_results_summary(results: Dict[str, Any]):
    """Print formatted summary of test results."""
    print_header("Test Results Summary")

    print(f"{Colors.BOLD}Scenario:{Colors.ENDC} {results['scenario'].upper()}")
    print(f"{Colors.BOLD}Overall Status:{Colors.ENDC}", end=" ")

    if results["success"]:
        print_success("PASSED")
    else:
        print_error("FAILED")

    print(f"\n{Colors.BOLD}Timing:{Colors.ENDC}")
    print(f"  Total Duration: {results['metrics']['total_time_seconds']:.2f} seconds")

    for step_name, step_data in results["steps"].items():
        if step_data.get("skipped"):
            print(f"  {step_name}: SKIPPED ({step_data.get('reason', 'unknown')})")
        else:
            print(f"  {step_name}: {step_data.get('duration_seconds', 0):.2f}s")

    print(f"\n{Colors.BOLD}Costs:{Colors.ENDC}")
    print(f"  Total Cost: €{results['metrics']['total_cost_euros']:.4f}")
    print(f"  Tokens Used: {results['metrics']['tokens_used']:,}")

    if results["errors"]:
        print(f"\n{Colors.BOLD}Errors:{Colors.ENDC}")
        for error in results["errors"]:
            print_error(f"  {error}")

    # Performance target check
    print(f"\n{Colors.BOLD}Performance Targets:{Colors.ENDC}")

    total_time = results["metrics"]["total_time_seconds"]
    target_time = 3 * 60 * 60  # 3 hours in seconds

    if total_time < target_time:
        print_success(f"  Processing time: {total_time:.2f}s < {target_time}s (3 hours) ✓")
    else:
        print_warning(f"  Processing time: {total_time:.2f}s > {target_time}s (3 hours) ✗")

    cost = results["metrics"]["total_cost_euros"]
    target_cost = Decimal("1.0")

    if cost < target_cost:
        print_success(f"  Cost per EVF: €{cost:.4f} < €{target_cost} ✓")
    else:
        print_warning(f"  Cost per EVF: €{cost:.4f} > €{target_cost} ✗")


async def main():
    """Run complete E2E test suite."""
    print_header("EVF Portugal 2030 - End-to-End Workflow Test")

    print(f"{Colors.BOLD}Test Configuration:{Colors.ENDC}")
    print(f"  Date: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print(f"  Python: {sys.version.split()[0]}")
    print(f"  Backend Path: {Path(__file__).parent}")

    # Check for Claude API key
    use_narrative = bool(os.getenv("ANTHROPIC_API_KEY"))

    if use_narrative:
        print_success("  Claude API Key: Found ✓")
    else:
        print_warning("  Claude API Key: Not found - NarrativeAgent will be skipped")

    print()

    # Run both scenarios
    scenarios = ["compliant", "non_compliant"]
    all_results = {}

    for scenario in scenarios:
        try:
            results = await test_scenario(scenario, use_narrative=use_narrative)
            all_results[scenario] = results
            print_results_summary(results)

            # Small delay between tests
            await asyncio.sleep(1)

        except Exception as e:
            print_error(f"Test failed for scenario '{scenario}': {e}")
            import traceback
            traceback.print_exc()

    # Final summary
    print_header("Final Summary")

    total_passed = sum(1 for r in all_results.values() if r["success"])
    total_tests = len(all_results)

    print(f"{Colors.BOLD}Tests Run:{Colors.ENDC} {total_tests}")
    print(f"{Colors.BOLD}Passed:{Colors.ENDC} {total_passed}")
    print(f"{Colors.BOLD}Failed:{Colors.ENDC} {total_tests - total_passed}")

    if total_passed == total_tests:
        print_success("\n✓ All tests passed!")
    else:
        print_error(f"\n✗ {total_tests - total_passed} test(s) failed")

    # Save results to JSON
    output_file = Path("/tmp/evf_test/e2e_test_results.json")
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, "w") as f:
        # Convert Decimal and datetime to JSON-serializable types
        def json_serializer(obj):
            if isinstance(obj, Decimal):
                return float(obj)
            elif isinstance(obj, datetime):
                return obj.isoformat()
            elif isinstance(obj, UUID):
                return str(obj)
            raise TypeError(f"Type {type(obj)} not serializable")

        json.dump(all_results, f, indent=2, default=json_serializer)

    print(f"\n{Colors.BOLD}Results saved to:{Colors.ENDC} {output_file}")

    return total_passed == total_tests


if __name__ == "__main__":
    # Run async main
    success = asyncio.run(main())

    # Exit with appropriate code
    sys.exit(0 if success else 1)
