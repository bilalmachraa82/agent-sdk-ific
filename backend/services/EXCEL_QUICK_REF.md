# Excel Generator - Quick Reference

## 🚀 Quick Start

```python
from services.excel_generator import ExcelGenerator

generator = ExcelGenerator()
excel_bytes = await generator.generate_evf_report(
    project_id=project_id,
    financial_output=financial_output,
    compliance_output=compliance_output,
    narrative_output=narrative_output,
    company_info=company_info,
    cash_flows=cash_flows,
    language="pt"  # or "en"
)
```

## 📊 Sheet Structure

| # | Sheet Name (PT) | Sheet Name (EN) | Content |
|---|----------------|-----------------|---------|
| 1 | Sumário Executivo | Executive Summary | Company info, key metrics, compliance status |
| 2 | Informação da Empresa | Company Information | Legal details, address, SAF-T metadata |
| 3 | Projeções Financeiras | Financial Projections | 10-year forecasts, revenue, costs, charts |
| 4 | Análise de Cash Flow | Cash Flow Analysis | FCF components, working capital, charts |
| 5 | Rácios Financeiros | Financial Ratios | Profitability, returns, efficiency ratios |
| 6 | Checklist de Conformidade | Compliance Checklist | PT2030 checks, color-coded status |
| 7 | Pressupostos e Metodologia | Assumptions & Methodology | Assumptions, methodology, audit trail |

## 🎨 PT2030 Colors

```python
"primary_blue": "1E3A8A"      # Headers
"secondary_blue": "3B82F6"    # Subheaders
"accent_green": "10B981"      # Pass/Positive
"warning_yellow": "F59E0B"    # Warnings
"error_red": "EF4444"         # Fail/Errors
"light_gray": "F3F4F6"        # Alternating rows
```

## 💾 Save to Storage

```python
from services.excel_generator import ExcelGenerator
from services.file_storage import FileStorageService

generator = ExcelGenerator(file_storage=FileStorageService())

metadata = await generator.save_to_storage(
    excel_bytes=excel_bytes,
    project_id=project_id,
    tenant_id=tenant_id,
    filename="evf_report.xlsx"
)
```

## 🌍 Languages

| Code | Language | Example Sheet |
|------|----------|---------------|
| `pt` | Portuguese (PT-PT) | "Sumário Executivo" |
| `en` | English | "Executive Summary" |

## 📈 Charts Included

1. **Revenue vs Costs** - Line chart on Financial Projections sheet
2. **Free Cash Flow** - Bar chart on Cash Flow Analysis sheet

## ✅ Compliance Color Coding

- 🟢 **Green** (`accent_green`): PASS, Compliant, VALF < 0
- 🔴 **Red** (`error_red`): FAIL, Critical issues
- 🟡 **Yellow** (`warning_yellow`): Warnings

## 🔧 Common Patterns

### Batch Generation

```python
generator = ExcelGenerator()  # Reuse!

tasks = [
    generator.generate_evf_report(...)
    for project in projects
]

results = await asyncio.gather(*tasks)
```

### Error Handling

```python
try:
    excel_bytes = await generator.generate_evf_report(...)
except ValueError as e:
    # Invalid language or data
    logger.error(f"Generation failed: {e}")
except Exception as e:
    # Unexpected error
    logger.error(f"Unexpected error: {e}")
```

### File Download Response

```python
from fastapi.responses import StreamingResponse
import io

return StreamingResponse(
    io.BytesIO(excel_bytes),
    media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    headers={"Content-Disposition": "attachment; filename=evf_report.xlsx"}
)
```

## 📏 Data Requirements

### Minimum Cash Flows
```python
cash_flows = [
    CashFlow(year=0, capex=Decimal("100000")),  # Year 0
    CashFlow(year=1, revenue=Decimal("50000"), ...)  # Year 1+
]
```

### PT2030 Compliance
```python
# VALF must be < 0 (negative)
financial_output.valf = Decimal("-45000.50")  # ✅

# TRF must be < 4%
financial_output.trf = Decimal("3.75")  # ✅
```

## 🧪 Testing

```bash
# Simple tests (no dependencies)
python3 backend/tests/test_excel_simple.py

# Full tests (requires pytest)
pytest backend/tests/test_excel_generator.py -v
```

## 🔒 Security Checklist

- ✅ Local processing (no external APIs)
- ✅ Input validation (Pydantic)
- ✅ SHA-256 file hashing
- ✅ Tenant isolation
- ✅ Encryption support (via FileStorageService)

## 📊 Performance

- **Generation**: < 5 seconds
- **File Size**: 50-200 KB
- **Memory**: < 50 MB
- **Concurrent**: 5+ reports

## 🐛 Troubleshooting

| Issue | Solution |
|-------|----------|
| `ValueError: Unsupported language` | Use `language="pt"` or `language="en"` |
| `RuntimeError: FileStorageService not configured` | Initialize: `ExcelGenerator(file_storage=service)` |
| Charts not appearing | Ensure `openpyxl >= 3.1.5` |
| Import errors | Check relative imports and `sys.path` |

## 📚 Resources

- **Full README**: `services/EXCEL_GENERATOR_README.md`
- **Examples**: `services/excel_generator_example.py`
- **Tests**: `tests/test_excel_generator.py`
- **Summary**: `EXCEL_GENERATOR_SUMMARY.md`

## 🎯 Key Methods

```python
# Generate report
excel_bytes = await generator.generate_evf_report(
    project_id, financial_output, compliance_output,
    narrative_output, company_info, cash_flows, language
)

# Save to storage
metadata = await generator.save_to_storage(
    excel_bytes, project_id, tenant_id, filename
)

# Calculate hash
hash_value = ExcelGenerator.calculate_file_hash(excel_bytes)
```

## ✨ Best Practices

1. **Reuse Generator**: Create once, use multiple times
2. **Validate Inputs**: Use Pydantic models
3. **Handle Errors**: Wrap in try/except
4. **Hash Files**: Store SHA-256 for integrity
5. **Async Operations**: Use `await` and `asyncio.gather()`

---

**Quick Reference v1.0.0** | Last Updated: 2024-11-07
