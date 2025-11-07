"""
InputAgent Usage Examples
Demonstrates how to use InputAgent for parsing Portuguese SAF-T XML files

Run this file to see examples:
    python3 agents/input_agent_example.py
"""

from decimal import Decimal
from datetime import date
from pathlib import Path
import json

from input_agent import (
    InputAgent,
    CompanyInfo,
    CompanyAddress,
    Period,
    FinancialStatement,
    SAFTData,
)


def example_1_parse_valid_saft():
    """Example 1: Parse a valid SAF-T PT XML file."""
    print("\n" + "=" * 70)
    print("EXAMPLE 1: Parse Valid SAF-T XML")
    print("=" * 70)

    # Sample SAF-T XML (simplified for demonstration)
    saft_xml = """<?xml version="1.0" encoding="UTF-8"?>
<AuditFile xmlns="urn:OECD:StandardAuditFile-Tax:PT_1.04_01">
    <Header>
        <TaxRegistrationNumber>123456789</TaxRegistrationNumber>
        <CompanyName>Exemplo Empresa Lda</CompanyName>
        <CompanyAddress>
            <AddressDetail>Av. da Liberdade, 100</AddressDetail>
            <City>Lisboa</City>
            <PostalCode>1250-001</PostalCode>
            <Country>PT</Country>
        </CompanyAddress>
        <FiscalYear>2024</FiscalYear>
        <StartDate>2024-01-01</StartDate>
        <EndDate>2024-12-31</EndDate>
        <CurrencyCode>EUR</CurrencyCode>
    </Header>
    <MasterFiles>
        <GeneralLedgerAccounts>
            <Account>
                <AccountID>71</AccountID>
                <AccountDescription>Vendas</AccountDescription>
                <ClosingCreditBalance>1000000.00</ClosingCreditBalance>
            </Account>
            <Account>
                <AccountID>61</AccountID>
                <AccountDescription>CMVMC</AccountDescription>
                <ClosingDebitBalance>600000.00</ClosingDebitBalance>
            </Account>
            <Account>
                <AccountID>63</AccountID>
                <AccountDescription>Gastos com Pessoal</AccountDescription>
                <ClosingDebitBalance>150000.00</ClosingDebitBalance>
            </Account>
            <Account>
                <AccountID>64</AccountID>
                <AccountDescription>Depreciacoes</AccountDescription>
                <ClosingDebitBalance>30000.00</ClosingDebitBalance>
            </Account>
        </GeneralLedgerAccounts>
    </MasterFiles>
</AuditFile>""".encode('utf-8')

    # Create InputAgent and parse
    agent = InputAgent()
    result = agent.parse_xml(saft_xml)

    # Check results
    if result.success:
        print(f"✅ Parsing successful in {result.parse_time_seconds:.3f}s\n")

        # Display company info
        company = result.data.company_info
        print(f"Company Information:")
        print(f"  - NIF: {company.nif}")
        print(f"  - Name: {company.name}")
        print(f"  - Fiscal Year: {company.fiscal_year}")
        print(f"  - Currency: {company.currency_code}")

        if company.address:
            print(f"  - City: {company.address.city}")
            print(f"  - Postal Code: {company.address.postal_code}")

        # Display period
        period = result.data.period
        print(f"\nAccounting Period:")
        print(f"  - FY: {period.fiscal_year}")
        print(f"  - From: {period.start_date}")
        print(f"  - To: {period.end_date}")
        print(f"  - Duration: {period.duration_days} days")

        # Display general ledger
        print(f"\nGeneral Ledger:")
        print(f"  - Total accounts: {len(result.data.general_ledger)}")
        for acc in result.data.general_ledger[:5]:  # Show first 5
            print(f"    • {acc.account_id}: {acc.account_description} = €{acc.closing_balance:,.2f}")

        # Display financial statements
        if result.data.financial_statements:
            stmt = result.data.financial_statements[0]
            print(f"\nFinancial Statement (FY {stmt.fiscal_year}):")
            print(f"  - Revenue: €{stmt.revenue:,.2f}")
            print(f"  - Cost of Sales: €{stmt.cost_of_sales:,.2f}")
            print(f"  - Gross Profit: €{stmt.gross_profit:,.2f}")
            print(f"  - Personnel Costs: €{stmt.personnel_costs:,.2f}")
            print(f"  - Depreciation: €{stmt.depreciation:,.2f}")
            print(f"  - EBITDA: €{stmt.ebitda:,.2f}")
            print(f"  - EBIT: €{stmt.ebit:,.2f}")

        # Display warnings
        if result.warnings:
            print(f"\n⚠️  Warnings ({len(result.warnings)}):")
            for warning in result.warnings:
                print(f"  - {warning}")

    else:
        print(f"❌ Parsing failed with {len(result.errors)} errors:")
        for error in result.errors:
            print(f"  - {error}")

    return result


def example_2_validate_data():
    """Example 2: Validate extracted SAF-T data."""
    print("\n" + "=" * 70)
    print("EXAMPLE 2: Data Validation")
    print("=" * 70)

    # Create sample SAFT data programmatically
    saft_data = SAFTData(
        company_info=CompanyInfo(
            nif="987654321",
            name="Validação Empresa Lda",
            fiscal_year=2024,
            currency_code="EUR"
        ),
        period=Period(
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
            fiscal_year=2024
        ),
        financial_statements=[
            FinancialStatement(
                fiscal_year=2024,
                revenue=Decimal("2000000"),
                cost_of_sales=Decimal("1200000"),
                personnel_costs=Decimal("300000"),
                depreciation=Decimal("50000"),
                total_assets=Decimal("1500000"),
                current_assets=Decimal("800000"),
                fixed_assets=Decimal("700000"),
                total_liabilities=Decimal("600000"),
                current_liabilities=Decimal("400000"),
                equity=Decimal("900000")
            )
        ]
    )

    # Validate
    agent = InputAgent()
    is_valid, errors = agent.validate_extracted_data(saft_data)

    print(f"\nValidation Result: {'✅ VALID' if is_valid else '❌ INVALID'}")

    if not is_valid:
        print(f"\nValidation Errors:")
        for error in errors:
            print(f"  - {error}")
    else:
        print(f"\n✅ All validation checks passed")
        print(f"\nFinancial Metrics:")
        stmt = saft_data.financial_statements[0]
        print(f"  - Revenue: €{stmt.revenue:,.2f}")
        print(f"  - Gross Margin: {(stmt.gross_profit / stmt.revenue * 100):.1f}%")
        print(f"  - EBITDA: €{stmt.ebitda:,.2f}")
        print(f"  - Total Assets: €{stmt.total_assets:,.2f}")
        print(f"  - Equity: €{stmt.equity:,.2f}")

    return is_valid, errors


def example_3_error_handling():
    """Example 3: Error handling for malformed XML."""
    print("\n" + "=" * 70)
    print("EXAMPLE 3: Error Handling")
    print("=" * 70)

    # Case 1: Malformed XML
    print("\nCase 1: Malformed XML")
    malformed_xml = b"""<?xml version="1.0" encoding="UTF-8"?>
<AuditFile>
    <Header>
        <CompanyName>Test Company
        <!-- Missing closing tag -->
    </Header>
</AuditFile>"""

    agent = InputAgent()
    result = agent.parse_xml(malformed_xml)

    print(f"  Result: {'✅ Success' if result.success else '❌ Failed (as expected)'}")
    if result.errors:
        print(f"  Error: {result.errors[0]}")

    # Case 2: Missing required fields
    print("\nCase 2: Missing Required Fields")
    missing_fields_xml = b"""<?xml version="1.0" encoding="UTF-8"?>
<AuditFile xmlns="urn:OECD:StandardAuditFile-Tax:PT_1.04_01">
    <Header>
        <!-- Missing TaxRegistrationNumber -->
        <CompanyName>Test Company</CompanyName>
        <!-- Missing FiscalYear -->
    </Header>
</AuditFile>"""

    result2 = agent.parse_xml(missing_fields_xml)
    print(f"  Result: {'✅ Success' if result2.success else '❌ Failed (as expected)'}")
    if result2.errors:
        print(f"  Error: {result2.errors[0]}")

    # Case 3: Invalid NIF
    print("\nCase 3: Invalid NIF Format")
    try:
        invalid_company = CompanyInfo(
            nif="12345",  # Invalid: should be 9 digits
            name="Test",
            fiscal_year=2024
        )
        print(f"  Result: ❌ Should have failed")
    except ValueError as e:
        print(f"  Result: ✅ Validation failed (as expected)")
        print(f"  Error: {str(e)}")


def example_4_integration_workflow():
    """Example 4: Complete workflow for EVF processing."""
    print("\n" + "=" * 70)
    print("EXAMPLE 4: EVF Processing Workflow")
    print("=" * 70)

    # Step 1: Parse SAF-T file
    print("\nStep 1: Parse SAF-T XML file")
    saft_xml = """<?xml version="1.0" encoding="UTF-8"?>
<AuditFile xmlns="urn:OECD:StandardAuditFile-Tax:PT_1.04_01">
    <Header>
        <TaxRegistrationNumber>111222333</TaxRegistrationNumber>
        <CompanyName>Projeto Inovacao Lda</CompanyName>
        <FiscalYear>2024</FiscalYear>
        <StartDate>2024-01-01</StartDate>
        <EndDate>2024-12-31</EndDate>
        <CurrencyCode>EUR</CurrencyCode>
    </Header>
    <MasterFiles>
        <GeneralLedgerAccounts>
            <Account>
                <AccountID>71</AccountID>
                <AccountDescription>Vendas</AccountDescription>
                <ClosingCreditBalance>3500000.00</ClosingCreditBalance>
            </Account>
            <Account>
                <AccountID>61</AccountID>
                <AccountDescription>CMVMC</AccountDescription>
                <ClosingDebitBalance>2100000.00</ClosingDebitBalance>
            </Account>
        </GeneralLedgerAccounts>
    </MasterFiles>
</AuditFile>""".encode('utf-8')

    agent = InputAgent()
    parse_result = agent.parse_xml(saft_xml)

    if not parse_result.success:
        print("❌ Parsing failed, cannot continue workflow")
        return

    print(f"✅ Parsed successfully: {parse_result.data.company_info.name}")

    # Step 2: Extract historical financial data
    print("\nStep 2: Extract Historical Financial Data")
    stmt = parse_result.data.financial_statements[0]
    print(f"  - Historical Revenue: €{stmt.revenue:,.2f}")
    print(f"  - Historical Costs: €{stmt.cost_of_sales:,.2f}")
    print(f"  - Historical EBITDA: €{stmt.ebitda:,.2f}")

    # Step 3: Use data for projections (would go to FinancialAgent)
    print("\nStep 3: Prepare Data for Financial Projections")
    print("  - Historical data can be used to:")
    print("    • Project future revenues (with growth rate)")
    print("    • Estimate operating costs")
    print("    • Calculate VALF and TRF via FinancialAgent")
    print("    • Validate PT2030 compliance")

    # Step 4: Audit trail
    print("\nStep 4: Audit Trail")
    print(f"  - Parse timestamp: {parse_result.data.parsed_at}")
    print(f"  - Parse duration: {parse_result.parse_time_seconds:.3f}s")
    if parse_result.data.file_hash:
        print(f"  - File hash: {parse_result.data.file_hash[:16]}...")

    print("\n✅ Workflow complete - ready for EVF generation")


def main():
    """Run all examples."""
    print("\n" + "=" * 70)
    print("INPUTAGENT - PORTUGUESE SAF-T XML PARSER")
    print("Examples and Usage Demonstrations")
    print("=" * 70)

    try:
        # Run examples
        example_1_parse_valid_saft()
        example_2_validate_data()
        example_3_error_handling()
        example_4_integration_workflow()

        print("\n" + "=" * 70)
        print("All examples completed successfully!")
        print("=" * 70 + "\n")

    except Exception as e:
        print(f"\n❌ Error running examples: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
