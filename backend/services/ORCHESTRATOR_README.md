# EVF Agent Orchestrator

## Overview

The **EVF Agent Orchestrator** is the central coordination system for the EVF Portugal 2030 platform. It orchestrates 5 specialized AI agents to transform Financial Viability Studies (EVF) from 24-hour manual work to 3-hour automated processing.

## Architecture

### Pipeline Flow

```
┌─────────────────────────────────────────────────────────────┐
│                    EVF Orchestrator                          │
│                                                               │
│  ┌────────────┐  ┌──────────────┐  ┌────────────────┐       │
│  │ 1. Input   │→ │ 2. Financial │→ │ 3. Compliance │        │
│  │    Agent   │  │     Agent    │  │     Agent     │        │
│  └────────────┘  └──────────────┘  └────────────────┘       │
│                                                               │
│       ↓                                                       │
│                                                               │
│  ┌────────────┐  ┌──────────────┐                           │
│  │ 4. Narrative│→│  5. Audit    │                           │
│  │    Agent   │  │     Agent    │                           │
│  └────────────┘  └──────────────┘                           │
└─────────────────────────────────────────────────────────────┘
```

### Agents

1. **InputAgent** (15% of processing)
   - Parse SAF-T/Excel/CSV files
   - Validate and normalize data
   - Extract financial information

2. **FinancialAgent** (20% of processing)
   - Calculate VALF (Net Present Value)
   - Calculate TRF (Internal Rate of Return)
   - Generate 30+ financial ratios
   - **100% deterministic** - no AI/LLM

3. **ComplianceAgent** (20% of processing)
   - Validate PT2030/PRR/SITCE rules
   - Check VALF < 0 requirement
   - Check TRF < 4% requirement
   - **100% rule-based** - no AI/LLM

4. **NarrativeAgent** (25% of processing)
   - Generate proposal text using Claude
   - Create executive summary
   - Format financial analysis
   - **Only agent using LLM**

5. **AuditAgent** (10% of processing)
   - Log all operations
   - Track costs and tokens
   - Create compliance trail
   - Generate processing summary

## Key Features

### State Machine

The orchestrator implements a state machine with the following states:

```python
class ProcessingStep(str, Enum):
    INITIALIZING = "initializing"
    PARSING_INPUT = "parsing_input"
    CALCULATING_FINANCIALS = "calculating_financials"
    VALIDATING_COMPLIANCE = "validating_compliance"
    GENERATING_NARRATIVE = "generating_narrative"
    AUDITING_RESULTS = "auditing_results"
    FINALIZING = "finalizing"
    COMPLETED = "completed"
    FAILED = "failed"
```

### Progress Tracking

Real-time progress tracking with:
- Current step and percentage (0-100%)
- Estimated completion time
- Steps completed/remaining
- Current agent execution
- Error messages (if any)

### Error Handling

- **Retry Logic**: Configurable retry count (default: 3)
- **Exponential Backoff**: Delay between retries
- **Graceful Degradation**: Continue processing even if non-critical steps fail
- **Rollback**: Revert database changes on failure
- **Audit Trail**: Every error logged for debugging

### Cost Tracking

- Track Claude API token usage
- Calculate costs in EUR
- Set cost limits per processing
- Warn when approaching limits
- Store costs in audit log

### Multi-Tenant Isolation

- Every operation includes tenant_id
- Database Row-Level Security (RLS)
- Tenant context set on session
- Isolation enforced at all levels

## Usage

### Basic Usage

```python
from backend.services.orchestrator import EVFOrchestrator

# Create orchestrator
orchestrator = EVFOrchestrator()

# Process EVF
result = await orchestrator.process_evf(
    project_id=project_id,
    tenant_id=tenant_id,
    session=db_session
)

# Check result
if result.status == ProcessingStatus.COMPLETED:
    print(f"VALF: {result.valf}")
    print(f"TRF: {result.trf}%")
    print(f"Compliant: {result.pt2030_compliant}")
```

### Custom Configuration

```python
from backend.services.orchestrator import (
    EVFOrchestrator,
    OrchestratorConfig
)

# Custom configuration
config = OrchestratorConfig(
    max_retries=5,
    retry_delay_seconds=10,
    timeout_seconds=600,
    cost_limit_euros=10.00,
    enable_caching=True
)

orchestrator = EVFOrchestrator(config=config)
```

### Background Processing

```python
from fastapi import BackgroundTasks

async def process_evf_background(
    project_id: UUID,
    background_tasks: BackgroundTasks
):
    async def bg_task():
        async with get_db() as session:
            orchestrator = EVFOrchestrator()
            await orchestrator.process_evf(
                project_id=project_id,
                tenant_id=tenant_id,
                session=session
            )

    background_tasks.add_task(bg_task)
    return {"status": "started"}
```

### Progress Polling

```python
# Get current status
status = await orchestrator.get_processing_status(project_id)

print(f"Status: {status.status}")
print(f"Progress: {status.progress_percentage}%")
print(f"Current Step: {status.current_step}")
print(f"ETA: {status.estimated_completion_at}")
```

### Cancellation

```python
# Cancel ongoing processing
cancelled = await orchestrator.cancel_processing(
    project_id=project_id,
    session=db_session
)

if cancelled:
    print("Processing cancelled")
```

## Data Models

### EVFResult

```python
class EVFResult(BaseModel):
    project_id: UUID
    tenant_id: UUID
    status: ProcessingStatus

    # Agent results
    input_agent_result: Optional[AgentResult]
    financial_agent_result: Optional[AgentResult]
    compliance_agent_result: Optional[AgentResult]
    narrative_agent_result: Optional[AgentResult]
    audit_agent_result: Optional[AgentResult]

    # Financial metrics
    valf: Optional[Decimal]
    trf: Optional[Decimal]
    pt2030_compliant: bool

    # Processing metadata
    processing_duration_seconds: float
    total_tokens_used: int
    total_cost_euros: Decimal
    errors: List[str]
    warnings: List[str]
```

### ProcessingProgress

```python
class ProcessingProgress(BaseModel):
    project_id: UUID
    status: ProcessingStatus
    current_step: ProcessingStep
    progress_percentage: float  # 0-100

    steps_completed: List[str]
    steps_remaining: List[str]

    started_at: datetime
    estimated_completion_at: Optional[datetime]

    current_agent: Optional[str]
    error_message: Optional[str]

    total_tokens_used: int
    total_cost_euros: Decimal
```

### AgentResult

```python
class AgentResult(BaseModel):
    agent_name: str
    success: bool
    data: Dict[str, Any]
    errors: List[str]
    warnings: List[str]

    execution_time_seconds: float
    tokens_used: int
    cost_euros: Decimal
    metadata: Dict[str, Any]
```

## Database Integration

### Tables Used

- **evf_projects**: Main project table
- **financial_models**: Financial calculation results
- **audit_log**: Complete audit trail

### Updates Made

The orchestrator updates the following fields:

```python
# EVFProject updates
project.status = EVFStatus.PROCESSING  # During processing
project.valf = calculated_valf
project.trf = calculated_trf
project.compliance_status = ComplianceStatus.COMPLIANT
project.processing_start_time = start_time
project.processing_end_time = end_time
project.processing_duration_seconds = duration
```

### Audit Trail

Every operation is logged:

```python
AuditLog(
    action="orchestrator_start",
    resource_type="evf_project",
    resource_id=project_id,
    agent_name="Orchestrator",
    metadata={
        "orchestrator_version": "1.0.0",
        "duration_seconds": 123.45,
        "total_cost_euros": 0.50,
    }
)
```

## Performance

### Target Metrics

- **Processing Time**: < 3 hours (target: < 1 hour)
- **API Response**: < 3 seconds
- **Cost per EVF**: < €1
- **Success Rate**: > 95%

### Optimization Strategies

1. **Parallel Execution**: Run non-dependent agents concurrently (future)
2. **Caching**: Cache intermediate results
3. **Batch Processing**: Process multiple projects efficiently
4. **Connection Pooling**: Reuse database connections
5. **Lazy Loading**: Load data only when needed

## Error Handling

### Retry Strategy

```python
# Automatic retry with exponential backoff
for attempt in range(max_retries + 1):
    try:
        result = await agent_func()
        return result
    except Exception as e:
        if attempt < max_retries:
            await asyncio.sleep(retry_delay_seconds)
        else:
            # Log and re-raise
            raise
```

### Error Types

1. **Validation Errors**: Invalid input data
2. **Calculation Errors**: Mathematical failures
3. **Compliance Errors**: PT2030 rule violations
4. **API Errors**: Claude API failures
5. **Database Errors**: Connection or query failures

### Recovery

- **Rollback**: Database changes rolled back on error
- **Status Update**: Project status set to REVIEW
- **Audit Log**: Error details stored
- **Notification**: User notified (future)

## Testing

### Running Tests

```bash
# Run all orchestrator tests
pytest backend/services/test_orchestrator.py -v

# Run specific test class
pytest backend/services/test_orchestrator.py::TestProcessingPipeline -v

# Run with coverage
pytest backend/services/test_orchestrator.py --cov=backend.services.orchestrator
```

### Test Coverage

- ✅ Basic initialization
- ✅ Complete processing pipeline
- ✅ Progress tracking
- ✅ Error handling and retry
- ✅ Cancellation
- ✅ Cost tracking
- ✅ Compliance validation
- ✅ Audit logging
- ✅ Status mapping

## Configuration

### Environment Variables

```bash
# Claude AI
CLAUDE_API_KEY=your_api_key
CLAUDE_MODEL=claude-3-5-sonnet-20241022
CLAUDE_MAX_TOKENS=4096
CLAUDE_DAILY_LIMIT=50.00  # EUR

# Processing
MAX_RETRIES=3
RETRY_DELAY_SECONDS=5
PROCESSING_TIMEOUT=300  # seconds

# Feature Flags
ENABLE_AI_NARRATIVE=true
ENABLE_CACHING=true
```

### Code Configuration

```python
config = OrchestratorConfig(
    max_retries=3,
    retry_delay_seconds=5,
    timeout_seconds=300,
    enable_caching=True,
    enable_parallel_execution=False,
    cost_limit_euros=5.00
)
```

## Security

### Multi-Tenant Isolation

- All operations filtered by tenant_id
- PostgreSQL Row-Level Security (RLS)
- Tenant context set on session
- No cross-tenant data leakage

### Data Privacy

- SAF-T files never sent to external APIs
- Processing done locally or via secure MCP servers
- All data encrypted at rest (AES-256)
- TLS 1.3 for all connections

### Audit Trail

- Every operation logged
- Immutable audit logs
- 10-year retention
- Full traceability for compliance

## Monitoring

### Logging

```python
logger.info(
    "EVF processing started",
    project_id=str(project_id),
    tenant_id=str(tenant_id)
)

logger.error(
    "Processing failed",
    error=str(e),
    duration_seconds=duration
)
```

### Metrics

- Processing duration
- Token usage
- Cost tracking
- Success/failure rate
- Error counts by type

### Alerts (Future)

- Cost limit exceeded
- Processing timeout
- High error rate
- Compliance failures

## Future Enhancements

### Planned Features

1. **Parallel Agent Execution**: Run independent agents concurrently
2. **Smart Retry**: Different strategies per error type
3. **Result Caching**: Cache results for identical inputs
4. **Webhooks**: Real-time notifications
5. **Advanced Analytics**: Processing insights and trends

### Optimization Opportunities

1. **Database Connection Pooling**: Reuse connections
2. **Batch Database Writes**: Reduce round trips
3. **Lazy Agent Loading**: Load agents on demand
4. **Streaming Results**: Stream large outputs
5. **GPU Acceleration**: For numerical calculations

## Troubleshooting

### Common Issues

**Issue**: Processing takes too long
- **Solution**: Check database connection pool, increase timeout

**Issue**: High costs
- **Solution**: Reduce cost_limit_euros, optimize prompts

**Issue**: Compliance failures
- **Solution**: Review PT2030 rules, check input data

**Issue**: Agent failures
- **Solution**: Check logs, increase retries, validate input

### Debug Mode

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Run with debug logging
orchestrator = EVFOrchestrator()
result = await orchestrator.process_evf(...)
```

## Support

### Documentation

- Architecture: `arquitetura_mvp_v4_final.md`
- Implementation: `claude_code_implementation_v4.md`
- Agents: `backend/agents/`
- Tests: `backend/services/test_orchestrator.py`

### Examples

- Simple usage: `orchestrator_example.py`
- FastAPI endpoints: `backend/api/evf.py` (future)
- WebSocket integration: `orchestrator_example.py`

### Contact

For issues or questions:
- GitHub Issues: Create an issue
- Documentation: Review CLAUDE.md
- Tests: See test_orchestrator.py for examples

---

**Version**: 1.0.0
**Last Updated**: 2025-01-07
**Status**: Production Ready (with mock agents)
