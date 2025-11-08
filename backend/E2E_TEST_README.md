# EVF Portugal 2030 - End-to-End Workflow Test

## Overview

Complete end-to-end test of the EVF (Estudo de Viabilidade Económica e Financeira) processing workflow.

Tests the complete pipeline:
1. **InputAgent** - Parse SAF-T XML files
2. **FinancialAgent** - Calculate VALF/TRF (NPV/IRR)
3. **ComplianceAgent** - Validate PT2030 rules
4. **NarrativeAgent** - Generate Portuguese narrative (optional)
5. **ExcelGenerator** - Create final Excel report

## Usage

### Basic Test (without AI narrative)

```bash
cd backend
python test_e2e_workflow.py
```

### Full Test (with Claude AI narrative)

```bash
export ANTHROPIC_API_KEY="your-api-key-here"
cd backend
python test_e2e_workflow.py
```

## Test Scenarios

The script runs two scenarios:

1. **Compliant Scenario**
   - VALF < 0 (negative NPV)
   - TRF < 4% (IRR below discount rate)
   - Meets PT2030 eligibility criteria

2. **Non-Compliant Scenario**
   - VALF > 0 (positive NPV - too profitable)
   - TRF > 4% (IRR above discount rate)
   - Does NOT meet PT2030 criteria

## Output

### Console Output

Detailed colored output showing:
- Step-by-step progress
- Financial metrics (VALF, TRF, payback period)
- Compliance status
- Processing time
- Cost tracking (Claude API tokens/EUR)

### Generated Files

1. **SAF-T XML** (temporary): `/tmp/evf_test/saft_*.xml`
2. **Excel Reports**: `/tmp/evf_test/reports/evf_report_*.xlsx`
3. **JSON Results**: `/tmp/evf_test/e2e_test_results.json`

### Sample Output

```
================================================================================
                    EVF Portugal 2030 - End-to-End Workflow Test                    
================================================================================

Test Configuration:
  Date: 2025-01-07 15:30:45 UTC
  Python: 3.11.0
  Backend Path: /path/to/backend
✓ Claude API Key: Found ✓

================================================================================
                         E2E Test: COMPLIANT Scenario                          
================================================================================

ℹ Step 1: Creating tenant and user...
✓ Created tenant: 12345678-1234-1234-1234-123456789012
✓ Created user: 87654321-4321-4321-4321-210987654321
✓ Created project: abcdef12-3456-7890-abcd-ef1234567890

ℹ Step 2: Parsing SAF-T file with InputAgent...
✓ Parsed SAF-T file: Empresa Teste EVF Portugal 2030
✓ NIF: 123456789
✓ Revenue: €150,000.00
✓ Parse time: 0.15s

ℹ Step 3: Calculating VALF/TRF with FinancialAgent...
✓ VALF: €-45,234.56
✓ TRF: 2.34%
✓ Payback Period: 4.2 years
✓ PT2030 Compliant

ℹ Step 4: Validating compliance with ComplianceAgent...
✓ Compliance check complete
✓ Status: COMPLIANT
✓ Critical failures: 0
✓ Warnings: 0
✓ Max funding rate: 55.0%

ℹ Step 5: Generating narrative with NarrativeAgent...
✓ Generated narrative
✓ Tokens used: 2,345
✓ Cost: €0.0235
✓ Executive summary: 487 words

ℹ Step 6: Generating Excel report...
✓ Generated Excel report: /tmp/evf_test/reports/evf_report_compliant_1704643845.xlsx
✓ File size: 45.67 KB

ℹ Step 7: Calculating final metrics...
✓ Test completed successfully!

================================================================================
                           Test Results Summary                            
================================================================================

Scenario: COMPLIANT
Overall Status: ✓ PASSED

Timing:
  Total Duration: 3.45 seconds
  tenant_creation: 0.01s
  input_agent: 0.15s
  financial_agent: 0.02s
  compliance_agent: 0.08s
  narrative_agent: 2.89s
  excel_generator: 0.30s

Costs:
  Total Cost: €0.0235
  Tokens Used: 2,345

Performance Targets:
✓ Processing time: 3.45s < 10800s (3 hours) ✓
✓ Cost per EVF: €0.0235 < €1.0 ✓
```

## Performance Targets

- **Processing Time**: < 3 hours (simulated workflow)
- **Cost per EVF**: < €1.00
- **Success Rate**: 100% for valid inputs

## Requirements

### Python Dependencies

```bash
pip install lxml numpy numpy-financial pydantic anthropic openpyxl
```

### Environment Variables

- `ANTHROPIC_API_KEY` (optional) - For NarrativeAgent testing

### Files Required

- `backend/regulations/pt2030_rules.json` - Compliance rules
- All agent modules in `backend/agents/`
- Excel generator in `backend/services/`

## Extending the Test

### Add New Scenarios

Edit the `create_sample_financial_projections()` function:

```python
if scenario == "my_scenario":
    total_investment = Decimal("300000")
    annual_revenue = [...]
    operating_costs = [...]
```

### Test Different Companies

Edit the `create_sample_saft_xml()` function to change company data.

### Add Custom Validations

Add checks in the main test function after each agent step.

## Troubleshooting

### ImportError for agents

Ensure you're running from the `backend/` directory:
```bash
cd backend
python test_e2e_workflow.py
```

### Rules file not found

Create the rules file:
```bash
mkdir -p backend/regulations
# Copy sample rules from documentation
```

### Claude API errors

Check your API key:
```bash
echo $ANTHROPIC_API_KEY
```

### Permission denied

Make script executable:
```bash
chmod +x backend/test_e2e_workflow.py
```

## CI/CD Integration

Run in CI pipeline:

```yaml
test-e2e:
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v3
    - uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    - run: pip install -r requirements.txt
    - run: python backend/test_e2e_workflow.py
      env:
        ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
```

## License

Copyright © 2025 EVF Portugal 2030. All rights reserved.
