# Excel Generator Service - PT2030 EVF Reports

## Overview

The `ExcelGenerator` service creates professional, PT2030-compliant Excel reports for Economic-Financial Viability (EVF) studies. It transforms data from multiple AI agents into comprehensive, multi-sheet Excel workbooks ready for funding applications.

## Features

### 📊 **7 Comprehensive Sheets**

1. **Executive Summary** - Key metrics, company info, and compliance status
2. **Company Information** - SAF-T company data and address
3. **Financial Projections** - 10-year forecasts with revenue, costs, EBITDA, FCF
4. **Cash Flow Analysis** - Detailed cash flow breakdowns with charts
5. **Financial Ratios** - 30+ profitability, efficiency, and coverage ratios
6. **Compliance Checklist** - PT2030 validation results with color coding
7. **Assumptions & Methodology** - Calculation details and audit trail

### 🎨 **Professional Formatting**

- **PT2030 Color Scheme**: Official blue/green colors for headers and status
- **Conditional Formatting**: Green for pass, red for fail, yellow for warnings
- **Currency Formatting**: EUR formatting with proper decimal places
- **Percentage Display**: Accurate percentage representation for ratios
- **Borders & Alignment**: Clean, professional table structures

### 📈 **Interactive Charts**

- **Revenue vs Costs** - Line chart showing 10-year trends
- **Cash Flow Waterfall** - Bar chart of annual free cash flow
- **VALF Sensitivity** (planned) - Sensitivity analysis visualization

### 🌍 **Multi-Language Support**

- **Portuguese (PT-PT)**: Default language for PT2030 applications
- **English (EN)**: Alternative for international stakeholders
- Extensible translation system for additional languages

### 🔒 **Audit Trail & Metadata**

- SHA-256 hash of input data
- Calculation timestamps
- Model versions used
- Deterministic calculation methods
- File integrity validation

## Usage

### Basic Usage

```python
from services.excel_generator import ExcelGenerator
from agents.financial_agent import FinancialAgent
from agents.compliance_agent import ComplianceAgent
from agents.narrative_agent import NarrativeAgent
from agents.input_agent import InputAgent

# Initialize generator
generator = ExcelGenerator()

# Get data from agents (example)
financial_output = financial_agent.calculate(financial_input)
compliance_output = compliance_agent.validate(compliance_input)
narrative_output = await narrative_agent.generate(narrative_input)
company_info = input_agent.parse_saft(saft_file)

# Generate Excel report
excel_bytes = await generator.generate_evf_report(
    project_id=project_id,
    financial_output=financial_output,
    compliance_output=compliance_output,
    narrative_output=narrative_output,
    company_info=company_info,
    cash_flows=cash_flows,
    language="pt"  # or "en"
)

# Download or save
with open("evf_report.xlsx", "wb") as f:
    f.write(excel_bytes)
```

### With File Storage Integration

```python
from services.excel_generator import ExcelGenerator
from services.file_storage import FileStorageService

# Initialize with file storage
file_storage = FileStorageService()
generator = ExcelGenerator(file_storage=file_storage)

# Generate report
excel_bytes = await generator.generate_evf_report(
    project_id=project_id,
    financial_output=financial_output,
    compliance_output=compliance_output,
    narrative_output=narrative_output,
    company_info=company_info,
    cash_flows=cash_flows,
    language="pt"
)

# Save to storage backend (local or S3)
metadata = await generator.save_to_storage(
    excel_bytes=excel_bytes,
    project_id=project_id,
    tenant_id=tenant_id,
    filename="evf_report_tech_innovations.xlsx"
)

print(f"File saved: {metadata.storage_path}")
print(f"SHA-256: {metadata.sha256_hash}")
```

## Input Data Requirements

### FinancialOutput (from FinancialAgent)

```python
FinancialOutput(
    valf=Decimal("-45000.50"),  # Must be negative for PT2030 compliance
    trf=Decimal("3.75"),         # Must be < 4% for PT2030
    payback_period=Decimal("6.5"),
    total_fcf=Decimal("1200000"),
    average_annual_fcf=Decimal("120000"),
    financial_ratios=FinancialRatios(...),
    pt2030_compliant=True,
    calculation_timestamp=datetime.utcnow(),
    input_hash="abc123...",
    assumptions={...}
)
```

### ComplianceResult (from ComplianceAgent)

```python
ComplianceResult(
    is_compliant=True,
    program="PT2030",
    checks=[...],  # List of ComplianceCheck objects
    recommendations=[...],
    critical_failures=0,
    warnings=0,
    max_funding_rate_percent=Decimal("50"),
    calculated_funding_amount=Decimal("250000")
)
```

### NarrativeOutput (from NarrativeAgent)

```python
NarrativeOutput(
    executive_summary="500-word summary...",
    methodology="300-word methodology...",
    recommendations="200-word recommendations...",
    tokens_used=1500,
    cost_euros=Decimal("0.05"),
    model_used="claude-4.5-sonnet"
)
```

### CompanyInfo (from InputAgent/SAF-T)

```python
CompanyInfo(
    nif="123456789",
    name="Tech Innovations Lda",
    fiscal_year=2024,
    currency_code="EUR",
    address=CompanyAddress(...)
)
```

### CashFlows (List[CashFlow])

```python
cash_flows = [
    CashFlow(year=0, capex=Decimal("500000")),  # Year 0: Initial investment
    CashFlow(year=1, revenue=Decimal("110000"), operating_costs=Decimal("66000"), ...),
    CashFlow(year=2, revenue=Decimal("220000"), operating_costs=Decimal("132000"), ...),
    # ... years 3-10
]
```

## Output Structure

### Sheet 1: Executive Summary

- Company name and NIF
- Key financial metrics (VALF, TRF, Investment)
- PT2030 compliance status with color coding
- Executive summary narrative text

### Sheet 2: Company Information

- Legal name and tax ID
- Fiscal year and currency
- Complete address
- SAF-T metadata

### Sheet 3: Financial Projections

- 10-year forecasts (Year 0 - Year 10)
- Revenue, Operating Costs, CAPEX
- Depreciation, EBITDA, EBIT
- Free Cash Flow and Cumulative FCF
- **Chart**: Revenue vs Operating Costs (line chart)

### Sheet 4: Cash Flow Analysis

- Annual cash flow components
- EBITDA breakdown
- Working capital changes
- Free cash flow with conditional formatting
- **Chart**: Free Cash Flow by Year (bar chart)

### Sheet 5: Financial Ratios

| Category | Metric | Value |
|----------|--------|-------|
| Profitability | Gross Margin | 40.00% |
| Profitability | Operating Margin | 25.00% |
| Returns | ROI | 18.00% |
| Efficiency | Asset Turnover | 1.5 |
| Coverage | EBITDA Coverage | 2.4 |

### Sheet 6: Compliance Checklist

| Check ID | Check Name | Severity | Status | Message |
|----------|------------|----------|--------|---------|
| valf_check | VALF < 0 | CRITICAL | PASS ✅ | VALF is negative as required |
| trf_check | TRF < 4% | CRITICAL | PASS ✅ | TRF below threshold |

- Color-coded status cells (green=pass, red=fail, yellow=warning)
- Summary section with overall compliance

### Sheet 7: Assumptions & Methodology

- Financial assumptions (discount rate, duration, etc.)
- Methodology narrative
- Calculation details (timestamp, hash, method)
- Audit trail information

## PT2030 Color Scheme

```python
PT2030_COLORS = {
    "primary_blue": "1E3A8A",      # Dark blue - Headers
    "secondary_blue": "3B82F6",    # Medium blue - Subheaders
    "accent_green": "10B981",      # Green - Positive/Pass
    "warning_yellow": "F59E0B",    # Yellow - Warnings
    "error_red": "EF4444",         # Red - Errors/Fail
    "light_gray": "F3F4F6",        # Light gray - Alternating rows
}
```

## Translations

### Portuguese (pt)

- "Sumário Executivo"
- "Informação da Empresa"
- "Projeções Financeiras"
- "Análise de Cash Flow"
- "Rácios Financeiros"
- "Checklist de Conformidade"
- "Pressupostos e Metodologia"

### English (en)

- "Executive Summary"
- "Company Information"
- "Financial Projections (10 Years)"
- "Cash Flow Analysis"
- "Financial Ratios"
- "Compliance Checklist"
- "Assumptions & Methodology"

## Error Handling

### Common Errors

**ValueError: Unsupported language**
```python
# Solution: Use "pt" or "en" only
excel_bytes = await generator.generate_evf_report(..., language="pt")
```

**RuntimeError: FileStorageService not configured**
```python
# Solution: Initialize generator with file storage service
generator = ExcelGenerator(file_storage=file_storage_service)
```

**Import errors**
```python
# Solution: Ensure all dependencies are installed
pip install openpyxl==3.1.5
```

## Performance

### Benchmarks

- **Generation Time**: < 5 seconds for 10-year projections
- **File Size**: ~50-200KB depending on data volume
- **Memory Usage**: < 50MB during generation

### Optimization Tips

1. **Reuse Generator Instance**: Create once, use multiple times
2. **Batch Operations**: Generate multiple reports asynchronously
3. **Cache Results**: Store generated files to avoid regeneration

```python
# Good: Reuse instance
generator = ExcelGenerator()
for project in projects:
    excel_bytes = await generator.generate_evf_report(...)

# Bad: Create new instance each time
for project in projects:
    generator = ExcelGenerator()  # ❌ Wasteful
    excel_bytes = await generator.generate_evf_report(...)
```

## Testing

### Unit Tests

```bash
# Run all Excel generator tests
pytest tests/test_excel_generator.py -v

# Run specific test
pytest tests/test_excel_generator.py::test_generate_evf_report_basic -v

# Run simple tests (no import dependencies)
python tests/test_excel_simple.py
```

### Test Coverage

- ✅ Basic report generation (PT and EN)
- ✅ All 7 sheets created correctly
- ✅ Data accuracy in all sheets
- ✅ Currency and percentage formatting
- ✅ Color coding for compliance
- ✅ Chart generation
- ✅ File storage integration
- ✅ Edge cases (minimal data, missing fields)
- ✅ Non-compliant projects
- ✅ Performance benchmarks

## Security Considerations

### Data Protection

1. **No External APIs**: All processing is local - no data sent to external services
2. **Encryption**: Files can be encrypted at rest using FileStorageService
3. **Tenant Isolation**: Multi-tenant file storage with RLS
4. **Audit Trail**: SHA-256 hashing for file integrity

### Input Validation

- All inputs validated via Pydantic models
- Cash flow consistency checks
- NIF format validation
- Currency and percentage bounds checking

## Integration with EVF Pipeline

```python
# Complete EVF processing workflow
async def process_evf_application(tenant_id: UUID, project_id: UUID, saft_file: bytes):
    # 1. Parse SAF-T
    input_agent = InputAgent()
    company_info, financials = input_agent.parse(saft_file)

    # 2. Calculate financial metrics
    financial_agent = FinancialAgent()
    financial_output = financial_agent.calculate(financial_input)

    # 3. Validate compliance
    compliance_agent = ComplianceAgent()
    compliance_output = compliance_agent.validate(compliance_input)

    # 4. Generate narrative
    narrative_agent = NarrativeAgent()
    narrative_output = await narrative_agent.generate(narrative_input)

    # 5. Generate Excel report
    excel_generator = ExcelGenerator(file_storage=file_storage)
    excel_bytes = await excel_generator.generate_evf_report(
        project_id=project_id,
        financial_output=financial_output,
        compliance_output=compliance_output,
        narrative_output=narrative_output,
        company_info=company_info,
        cash_flows=cash_flows,
        language="pt"
    )

    # 6. Save to storage
    metadata = await excel_generator.save_to_storage(
        excel_bytes=excel_bytes,
        project_id=project_id,
        tenant_id=tenant_id,
        filename=f"evf_{company_info.name}_{datetime.now().strftime('%Y%m%d')}.xlsx"
    )

    return metadata
```

## Future Enhancements

### Planned Features

- [ ] **VALF Sensitivity Analysis Chart**: Interactive sensitivity table and chart
- [ ] **Multi-Scenario Comparison**: Compare optimistic/realistic/pessimistic scenarios
- [ ] **PDF Export**: Convert Excel to PDF for final submission
- [ ] **Custom Templates**: Allow users to customize sheet layouts
- [ ] **Data Validation**: Add Excel data validation rules
- [ ] **Macros** (if needed): VBA for interactive elements
- [ ] **Additional Languages**: Spanish, French for international applications

### Enhancement Ideas

```python
# Scenario comparison
await generator.generate_multi_scenario_report(
    scenarios=["optimistic", "realistic", "pessimistic"],
    financial_outputs=[opt_output, real_output, pess_output],
    ...
)

# Custom branding
await generator.generate_evf_report(
    ...,
    branding={
        "logo_path": "/path/to/logo.png",
        "primary_color": "1E3A8A",
        "company_name": "Consulting Firm Ltd"
    }
)
```

## Support

### Common Questions

**Q: Can I add custom sheets?**
A: Yes, extend the `ExcelGenerator` class and override `_create_custom_sheet()` method.

**Q: How do I change colors?**
A: Modify the `PT2030_COLORS` dictionary or pass custom colors via configuration.

**Q: Can I export to PDF?**
A: Not yet, but planned for future release. Use external PDF converter for now.

**Q: Is chart generation required?**
A: Charts are generated by default. You can skip by modifying the sheet creation methods.

### Troubleshooting

**Charts not appearing**: Ensure openpyxl version >= 3.1.5
**Formatting issues**: Check Excel version (tested on Excel 2019+)
**Large file sizes**: Reduce number of years or optimize image compression

## License

Part of EVF Portugal 2030 Platform - Proprietary Software

## Changelog

### v1.0.0 (2024-11-07)
- ✅ Initial release
- ✅ 7 comprehensive sheets
- ✅ PT2030 color scheme
- ✅ Multi-language support (PT, EN)
- ✅ Chart generation
- ✅ File storage integration
- ✅ Comprehensive test suite

---

**Generated by**: ExcelGenerator v1.0.0
**Last Updated**: 2024-11-07
**Author**: EVF Portugal 2030 Platform Team
