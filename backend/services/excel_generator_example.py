"""
Excel Generator Usage Example

Demonstrates how to use ExcelGenerator to create PT2030-compliant EVF reports.
This example shows the complete workflow from agent outputs to Excel file.
"""

import asyncio
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

# Note: In production, these imports would work with proper package structure
# For this example, we'll create mock data directly

def create_sample_data():
    """Create sample data matching agent output schemas."""

    # Sample Company Info (from InputAgent/SAF-T)
    from agents.input_agent import CompanyInfo, CompanyAddress

    company_info = CompanyInfo(
        nif="123456789",
        name="Tech Innovations Lda",
        fiscal_year=2024,
        currency_code="EUR",
        audit_file_version="1.04_01",
        address=CompanyAddress(
            address_detail="Rua das Flores, 123",
            city="Porto",
            postal_code="4000-001",
            region="Porto",
            country="PT"
        )
    )

    # Sample Cash Flows (from FinancialAgent input)
    from agents.financial_agent import CashFlow

    cash_flows = []

    # Year 0 - Initial investment
    cash_flows.append(
        CashFlow(
            year=0,
            revenue=Decimal("0"),
            operating_costs=Decimal("0"),
            capex=Decimal("500000"),  # €500k initial investment
            depreciation=Decimal("0"),
            working_capital_change=Decimal("0")
        )
    )

    # Years 1-10 - Operations with growth
    for year in range(1, 11):
        revenue = Decimal(str(100000 * year * 1.15))  # 15% YoY growth
        costs = revenue * Decimal("0.60")  # 60% cost ratio
        capex = Decimal("20000") if year in [3, 6, 9] else Decimal("0")
        depreciation = Decimal("50000")

        cash_flows.append(
            CashFlow(
                year=year,
                revenue=revenue,
                operating_costs=costs,
                capex=capex,
                depreciation=depreciation,
                working_capital_change=Decimal("5000")
            )
        )

    # Sample Financial Output (from FinancialAgent)
    from agents.financial_agent import FinancialOutput, FinancialRatios

    financial_output = FinancialOutput(
        valf=Decimal("-45000.50"),  # Negative (good for PT2030)
        trf=Decimal("3.75"),  # 3.75% (below 4% threshold)
        payback_period=Decimal("6.5"),
        total_fcf=Decimal("1200000"),
        average_annual_fcf=Decimal("120000"),
        financial_ratios=FinancialRatios(
            gross_margin=Decimal("0.40"),
            operating_margin=Decimal("0.25"),
            net_margin=Decimal("0.15"),
            roi=Decimal("0.18"),
            roic=Decimal("0.22"),
            asset_turnover=Decimal("1.5"),
            capex_to_revenue=Decimal("0.05"),
            ebitda_coverage=Decimal("2.4"),
            fcf_coverage=Decimal("1.8")
        ),
        pt2030_compliant=True,
        compliance_notes=["VALF < 0: PASS", "TRF < 4%: PASS"],
        calculation_timestamp=datetime.utcnow(),
        input_hash="abc123def456789",
        calculation_method="numpy-financial",
        assumptions={
            "discount_rate": "4%",
            "project_duration": "10 years",
            "calculation_method": "Deterministic (numpy-financial)",
            "inflation_rate": "2%",
            "tax_rate": "21%"
        }
    )

    # Sample Compliance Output (from ComplianceAgent)
    from agents.compliance_agent import (
        ComplianceResult,
        ComplianceCheck,
        CheckSeverity
    )

    compliance_checks = [
        ComplianceCheck(
            check_id="valf_check",
            check_name="VALF < 0 (Negative NPV Required)",
            severity=CheckSeverity.CRITICAL,
            passed=True,
            expected_value="< 0",
            actual_value="-45000.50 EUR",
            message="VALF is negative as required for PT2030 funding eligibility",
            rule_reference="PT2030-FIN-001"
        ),
        ComplianceCheck(
            check_id="trf_check",
            check_name="TRF < Discount Rate (4%)",
            severity=CheckSeverity.CRITICAL,
            passed=True,
            expected_value="< 4%",
            actual_value="3.75%",
            message="TRF is below discount rate threshold, ensuring project needs public funding",
            rule_reference="PT2030-FIN-002"
        ),
        ComplianceCheck(
            check_id="company_size",
            check_name="Company Size Classification",
            severity=CheckSeverity.INFO,
            passed=True,
            expected_value="SME (< 250 employees)",
            actual_value="SMALL (45 employees)",
            message="Company qualifies as SME for higher funding rates",
            rule_reference="PT2030-ELG-001"
        ),
        ComplianceCheck(
            check_id="min_investment",
            check_name="Minimum Investment Amount",
            severity=CheckSeverity.CRITICAL,
            passed=True,
            expected_value=">= 50,000 EUR",
            actual_value="500,000 EUR",
            message="Investment meets minimum threshold for PT2030",
            rule_reference="PT2030-INV-001"
        ),
        ComplianceCheck(
            check_id="green_investment",
            check_name="Green Investment Component",
            severity=CheckSeverity.WARNING,
            passed=True,
            expected_value=">= 30%",
            actual_value="25%",
            message="Consider increasing green investment to 30%+ for higher priority",
            rule_reference="PT2030-ENV-001"
        )
    ]

    compliance_output = ComplianceResult(
        is_compliant=True,
        program="PT2030",
        checks=compliance_checks,
        recommendations=[
            "Proceed with funding application - all critical criteria met",
            "Consider increasing green investment component from 25% to 30%+",
            "Develop sustainability impact assessment for stronger application",
            "Prepare job creation documentation (estimated 12 new positions)"
        ],
        confidence_score=0.95,
        critical_failures=0,
        warnings=1,
        max_funding_rate_percent=Decimal("50"),
        calculated_funding_amount=Decimal("250000"),
        requested_funding_valid=True,
        validation_timestamp=datetime.utcnow(),
        rules_version="1.0.0",
        validator_version="1.0.0"
    )

    # Sample Narrative Output (from NarrativeAgent)
    from agents.narrative_agent import NarrativeOutput

    narrative_output = NarrativeOutput(
        executive_summary=(
            "Tech Innovations Lda proposes a strategic €500,000 investment in digital "
            "transformation for the Portuguese manufacturing sector. This project will "
            "modernize production capabilities through Industry 4.0 technologies, including "
            "IoT sensors, predictive maintenance systems, and AI-powered quality control.\n\n"
            "Financial analysis demonstrates strong viability for public funding support. "
            "The project exhibits a negative VALF of €-45,000.50 and TRF of 3.75%, both "
            "meeting PT2030 eligibility requirements. These metrics confirm that the project "
            "requires and justifies public funding to achieve socioeconomic benefits.\n\n"
            "The initiative will create 12 new highly-skilled positions and maintain 45 "
            "existing jobs over the 10-year project lifecycle. Environmental benefits include "
            "25% reduction in energy consumption and 30% decrease in material waste through "
            "optimized production processes.\n\n"
            "This project aligns with Portugal 2030 objectives for digital transition, "
            "sustainable growth, and territorial cohesion in the Porto region."
        ),
        methodology=(
            "Financial viability analysis followed PT2030 methodological guidelines using "
            "deterministic cash flow modeling. VALF (Net Present Value) calculations employed "
            "the mandated 4% social discount rate over a 10-year analysis period.\n\n"
            "Revenue projections are based on historical SAF-T data (2021-2024) with "
            "conservative 15% annual growth assumptions validated by sector benchmarks. "
            "Operating cost ratios (60% of revenue) reflect industry standards for "
            "manufacturing automation projects.\n\n"
            "TRF (Internal Rate of Return) was calculated using numpy-financial library, "
            "ensuring mathematical precision and reproducibility. All calculations are "
            "deterministic and auditable - no AI models were used for financial projections.\n\n"
            "Compliance validation applied PT2030 regulation criteria systematically, "
            "checking 15 critical requirements across financial, eligibility, environmental, "
            "and state aid dimensions."
        ),
        recommendations=(
            "Based on comprehensive analysis, we recommend:\n\n"
            "1. **Proceed with Application**: All PT2030 critical criteria are met. "
            "Submit application with confidence.\n\n"
            "2. **Enhance Green Component**: Increase green investment from 25% to 35% "
            "through renewable energy integration for higher scoring.\n\n"
            "3. **Develop Impact Metrics**: Prepare detailed KPIs for job creation, "
            "sustainability improvements, and regional economic impact.\n\n"
            "4. **Timeline Optimization**: Front-load green investments in Years 1-2 "
            "to maximize environmental benefits and comply with DNSH principles.\n\n"
            "5. **Stakeholder Engagement**: Coordinate with local authorities and "
            "environmental agencies for letters of support."
        ),
        tokens_used=2845,
        cost_euros=Decimal("0.08"),
        generation_time_seconds=3.2,
        word_count={
            "executive_summary": 142,
            "methodology": 118,
            "recommendations": 98
        },
        model_used="claude-4.5-sonnet-20250929",
        generation_timestamp=datetime.utcnow(),
        input_hash="def789abc456",
        cached=False
    )

    return company_info, cash_flows, financial_output, compliance_output, narrative_output


async def example_generate_report():
    """Example 1: Generate Excel report and save to file."""
    print("\n" + "="*70)
    print("EXAMPLE 1: Generate PT2030 EVF Excel Report")
    print("="*70 + "\n")

    # Import the generator
    from services.excel_generator import ExcelGenerator

    # Create sample data
    company_info, cash_flows, financial_output, compliance_output, narrative_output = create_sample_data()

    # Initialize generator
    generator = ExcelGenerator()

    # Generate report in Portuguese
    print("📊 Generating Portuguese report...")
    project_id = uuid4()

    excel_bytes_pt = await generator.generate_evf_report(
        project_id=project_id,
        financial_output=financial_output,
        compliance_output=compliance_output,
        narrative_output=narrative_output,
        company_info=company_info,
        cash_flows=cash_flows,
        language="pt"
    )

    # Save to file
    output_dir = Path("./output")
    output_dir.mkdir(exist_ok=True)

    pt_filename = output_dir / f"evf_report_pt_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    with open(pt_filename, "wb") as f:
        f.write(excel_bytes_pt)

    print(f"✅ Portuguese report saved: {pt_filename}")
    print(f"   File size: {len(excel_bytes_pt):,} bytes")

    # Generate English version
    print("\n📊 Generating English report...")

    excel_bytes_en = await generator.generate_evf_report(
        project_id=project_id,
        financial_output=financial_output,
        compliance_output=compliance_output,
        narrative_output=narrative_output,
        company_info=company_info,
        cash_flows=cash_flows,
        language="en"
    )

    en_filename = output_dir / f"evf_report_en_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    with open(en_filename, "wb") as f:
        f.write(excel_bytes_en)

    print(f"✅ English report saved: {en_filename}")
    print(f"   File size: {len(excel_bytes_en):,} bytes")

    # Calculate file hash for integrity
    file_hash = ExcelGenerator.calculate_file_hash(excel_bytes_pt)
    print(f"\n🔒 File integrity hash (SHA-256): {file_hash[:32]}...")

    print("\n" + "="*70)
    print("✅ Reports generated successfully!")
    print("="*70)


async def example_with_file_storage():
    """Example 2: Generate and save to file storage service."""
    print("\n" + "="*70)
    print("EXAMPLE 2: Generate Report with File Storage Integration")
    print("="*70 + "\n")

    # Note: This would require actual FileStorageService setup
    # For demonstration, we'll show the pattern

    print("📦 Initializing file storage service...")
    # from services.file_storage import FileStorageService
    # file_storage = FileStorageService()

    # For this example, we'll simulate
    print("⚠️  Note: Using mock storage service for demonstration")

    from unittest.mock import AsyncMock, Mock
    from services.excel_generator import ExcelGenerator
    from models.file import File

    # Mock storage service
    mock_storage = AsyncMock()
    mock_file = Mock(spec=File)
    mock_file.id = uuid4()
    mock_file.tenant_id = uuid4()
    mock_file.file_name = "evf_report_tech_innovations.xlsx"
    mock_file.file_size_bytes = 75000
    mock_file.sha256_hash = "abc123def456..."
    mock_file.storage_path = "/storage/tenant_123/evf_report_tech_innovations.xlsx"
    mock_file.upload_timestamp = datetime.utcnow()

    mock_storage.save_file = AsyncMock(return_value=mock_file)

    # Create generator with storage
    generator = ExcelGenerator(file_storage=mock_storage)

    # Create sample data
    company_info, cash_flows, financial_output, compliance_output, narrative_output = create_sample_data()

    # Generate report
    print("📊 Generating report...")
    project_id = uuid4()

    excel_bytes = await generator.generate_evf_report(
        project_id=project_id,
        financial_output=financial_output,
        compliance_output=compliance_output,
        narrative_output=narrative_output,
        company_info=company_info,
        cash_flows=cash_flows,
        language="pt"
    )

    print(f"✅ Report generated: {len(excel_bytes):,} bytes")

    # Save to storage
    print("\n💾 Saving to file storage...")
    metadata = await generator.save_to_storage(
        excel_bytes=excel_bytes,
        project_id=project_id,
        tenant_id=mock_file.tenant_id,
        filename=mock_file.file_name
    )

    print(f"✅ File saved successfully!")
    print(f"   File ID: {metadata.id}")
    print(f"   Storage path: {metadata.storage_path}")
    print(f"   SHA-256: {metadata.sha256_hash}")
    print(f"   Size: {metadata.file_size_bytes:,} bytes")

    print("\n" + "="*70)
    print("✅ Report saved to storage successfully!")
    print("="*70)


async def example_batch_generation():
    """Example 3: Generate multiple reports in batch."""
    print("\n" + "="*70)
    print("EXAMPLE 3: Batch Report Generation")
    print("="*70 + "\n")

    from services.excel_generator import ExcelGenerator

    # Create generator (reuse instance for efficiency)
    generator = ExcelGenerator()

    # Simulate multiple projects
    num_projects = 5
    print(f"📊 Generating {num_projects} EVF reports...\n")

    tasks = []
    for i in range(num_projects):
        company_info, cash_flows, financial_output, compliance_output, narrative_output = create_sample_data()

        # Modify data slightly for variety
        company_info.name = f"Company {i+1} Lda"
        company_info.nif = f"{123456789 + i}"

        task = generator.generate_evf_report(
            project_id=uuid4(),
            financial_output=financial_output,
            compliance_output=compliance_output,
            narrative_output=narrative_output,
            company_info=company_info,
            cash_flows=cash_flows,
            language="pt"
        )
        tasks.append(task)

    # Generate all reports concurrently
    import time
    start_time = time.time()

    results = await asyncio.gather(*tasks)

    duration = time.time() - start_time

    print(f"✅ Generated {len(results)} reports in {duration:.2f} seconds")
    print(f"   Average: {duration/len(results):.2f} seconds per report")
    print(f"   Total size: {sum(len(r) for r in results):,} bytes")

    print("\n" + "="*70)
    print("✅ Batch generation complete!")
    print("="*70)


async def main():
    """Run all examples."""
    print("\n" + "="*70)
    print(" Excel Generator Examples - PT2030 EVF Reports")
    print("="*70)

    # Example 1: Basic report generation
    await example_generate_report()

    # Example 2: With file storage
    await example_with_file_storage()

    # Example 3: Batch generation
    await example_batch_generation()

    print("\n" + "="*70)
    print(" All Examples Completed Successfully!")
    print("="*70 + "\n")


if __name__ == "__main__":
    # Run examples
    asyncio.run(main())
