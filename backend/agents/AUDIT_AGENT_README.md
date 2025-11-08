# AuditAgent - Comprehensive Logging and Cost Tracking

## Overview

The **AuditAgent** is responsible for comprehensive audit logging, cost tracking, and compliance reporting for the EVF Portugal 2030 platform. It ensures complete traceability of all operations, tracks Claude API costs, and generates compliance reports to meet PT2030's 10-year retention requirement.

## Features

### Core Capabilities

1. **Immutable Audit Logging**
   - Log every operation with full context
   - SHA-256 hashing of input/output data for integrity
   - Timestamps and user/tenant tracking
   - Complete request/response metadata

2. **Cost Tracking**
   - Claude API token consumption and EUR costs
   - Storage cost estimation
   - Compute time tracking
   - Per-agent and per-project cost breakdown

3. **Compliance Reporting**
   - 10-year retention support
   - Audit trail completeness metrics
   - Regulatory compliance reports
   - Error and performance tracking

4. **Multi-Tenant Isolation**
   - All queries respect tenant boundaries
   - Row-level security enforcement
   - Tenant-specific cost limits and alerts

## Architecture

### Database Model

The AuditAgent uses the `AuditLog` model defined in `backend/models/evf.py`:

```python
class AuditLog(Base, BaseTenantModel):
    """Immutable audit log for compliance and traceability."""

    # Operation details
    action: str                      # e.g., 'upload_file', 'calculate_valf'
    resource_type: str               # e.g., 'evf_project', 'financial_model'
    resource_id: UUID

    # Agent information
    agent_name: str                  # Name of agent that performed action

    # Data hashing for integrity
    input_hash: str                  # SHA-256 hash of input
    output_hash: str                 # SHA-256 hash of output
    input_size_bytes: int
    output_size_bytes: int

    # Cost tracking
    tokens_used: int                 # Claude tokens consumed
    cost_euros: Decimal              # Cost in EUR

    # User/client context
    user_id: UUID
    tenant_id: UUID
    ip_address: str
    user_agent: str

    # Request details
    request_method: str              # HTTP method
    request_path: str                # API endpoint
    request_duration_ms: int         # Processing time

    # Project association
    project_id: UUID

    # Status and errors
    status: str                      # 'success', 'error', 'warning'
    error_message: str
    error_stacktrace: str

    # Additional context
    metadata: JSONB                  # Custom metadata
    created_at: DateTime             # Timestamp (immutable)
```

### Pydantic Models

#### AuditLogCreate
Request model for creating audit log entries with validation.

#### AuditLogResponse
Response model for returning audit log entries via API.

#### ProjectCost
Comprehensive cost breakdown for an EVF project:
- Total tokens used and API cost
- Operation counts (successful/failed)
- Cost breakdown by agent
- Processing time metrics
- Storage cost estimation

#### AuditReport
Comprehensive audit report for a tenant:
- Operation statistics
- Cost summaries
- Performance metrics (average, P95, P99)
- Error tracking
- Compliance metrics

## Usage

### Basic Operation Logging

```python
from backend.agents.audit_agent import AuditAgent, AgentType, ResourceType

audit_agent = AuditAgent(db=db_session)

# Log a file upload operation
log = await audit_agent.log_operation(
    action="upload_saft_file",
    resource_type=ResourceType.FILE_UPLOAD.value,
    resource_id=file_id,
    tenant_id=tenant_id,
    user_id=user_id,
    agent_name=AgentType.INPUT_AGENT.value,
    metadata={
        "file_name": "company_saft_2023.xml",
        "file_size_bytes": 2500000,
    },
)
```

### Logging with Cost Tracking

```python
# Log operation with Claude API usage
log = await audit_agent.log_operation(
    action="generate_narrative",
    resource_type=ResourceType.NARRATIVE_GENERATION.value,
    resource_id=narrative_id,
    tenant_id=tenant_id,
    project_id=project_id,
    agent_name=AgentType.NARRATIVE_AGENT.value,
    tokens_used=15000,  # Cost auto-calculated
    metadata={
        "model": "claude-3-5-sonnet-20241022",
        "word_count": 850,
    },
)
```

### Logging with Data Hashing

```python
# Log financial calculation with input/output hashing
input_data = {
    "total_investment": 500000,
    "cash_flows": [100000, 120000, 140000],
}

output_data = {
    "valf": -45000,
    "trf": 3.2,
}

log = await audit_agent.log_operation(
    action="calculate_financial_model",
    resource_type=ResourceType.FINANCIAL_MODEL.value,
    resource_id=model_id,
    tenant_id=tenant_id,
    project_id=project_id,
    agent_name=AgentType.FINANCIAL_AGENT.value,
    input_data=input_data,
    output_data=output_data,
)

# Data integrity verified via SHA-256 hashes
print(f"Input hash: {log.input_hash}")   # 64-char hex digest
print(f"Output hash: {log.output_hash}")  # 64-char hex digest
```

### Logging Errors

```python
try:
    # Operation that might fail
    result = await process_saft_file(file_path)
except Exception as e:
    import traceback

    # Log the error
    await audit_agent.log_operation(
        action="parse_saft_file",
        resource_type=ResourceType.FILE_UPLOAD.value,
        resource_id=file_id,
        tenant_id=tenant_id,
        user_id=user_id,
        agent_name=AgentType.INPUT_AGENT.value,
        status=OperationStatus.ERROR.value,
        error_message=str(e),
        error_stacktrace=traceback.format_exc(),
    )
```

### Retrieving Audit Trail

```python
# Get complete audit trail for a project
logs = await audit_agent.get_project_audit_trail(
    project_id=project_id,
    tenant_id=tenant_id,
)

for log in logs:
    print(f"{log.created_at}: {log.action} by {log.agent_name}")
```

### Querying Audit Logs

```python
# Get all errors from last 7 days
error_logs = await audit_agent.get_logs_by_criteria(
    tenant_id=tenant_id,
    start_date=datetime.utcnow() - timedelta(days=7),
    end_date=datetime.utcnow(),
    status=OperationStatus.ERROR.value,
)

# Get all operations by specific agent
narrative_logs = await audit_agent.get_logs_by_criteria(
    tenant_id=tenant_id,
    agent_name=AgentType.NARRATIVE_AGENT.value,
    limit=50,
)

# Get all file uploads
upload_logs = await audit_agent.get_logs_by_criteria(
    tenant_id=tenant_id,
    action="upload_saft_file",
)
```

### Calculating Project Costs

```python
# Calculate comprehensive cost breakdown
cost = await audit_agent.calculate_project_cost(
    project_id=project_id,
    tenant_id=tenant_id,
)

print(f"Project: {cost.project_name}")
print(f"Total operations: {cost.operation_count}")
print(f"Total cost: €{cost.total_cost_euros}")
print(f"Total tokens: {cost.total_tokens_used:,}")

# Cost breakdown by agent
for agent, agent_cost in cost.agent_costs.items():
    tokens = cost.agent_tokens[agent]
    print(f"{agent}: €{agent_cost} ({tokens:,} tokens)")
```

### Generating Audit Reports

```python
# Generate monthly audit report
report = await audit_agent.generate_audit_report(
    tenant_id=tenant_id,
    start_date=datetime.utcnow() - timedelta(days=30),
    end_date=datetime.utcnow(),
)

print(f"Total operations: {report.total_operations}")
print(f"Total cost: €{report.total_cost_euros}")
print(f"Total tokens: {report.total_tokens_used:,}")
print(f"Compliance: {report.compliance_percentage}%")

# Operation breakdown
for action, count in report.operations_by_action.items():
    print(f"  {action}: {count}")

# Cost breakdown
for agent, cost in report.cost_by_agent.items():
    print(f"  {agent}: €{cost}")
```

### Checking Daily Costs

```python
# Check daily cost and limits
summary = await audit_agent.get_daily_cost_summary(
    tenant_id=tenant_id,
)

print(f"Daily cost: €{summary['total_cost_euros']:.4f}")
print(f"Daily limit: €{summary['daily_limit_euros']:.2f}")
print(f"Limit usage: {summary['limit_percentage']:.1f}%")

if summary['limit_exceeded']:
    print("⚠️  WARNING: Daily limit exceeded!")
```

## Cost Calculation

### Claude API Pricing

The AuditAgent uses the following pricing for Claude 3.5 Sonnet:

- **Input tokens**: €3 per 1M tokens
- **Output tokens**: €15 per 1M tokens
- **Average**: €9 per 1M tokens (when input/output split unknown)

### Storage Cost Estimation

Storage costs use S3-like pricing:
- **€0.023 per GB-month**

### Example Cost Calculation

```python
# 15,000 tokens used
tokens = 15000
cost = (tokens / 1_000_000) * 9  # €0.135

# Storage: 100 MB for 1 month
storage_gb = 0.1
storage_cost = storage_gb * 0.023  # €0.0023

# Total cost
total = cost + storage_cost  # €0.1373
```

## Integration with FastAPI

### Automatic Request Logging

```python
from fastapi import FastAPI, Request
from time import time

app = FastAPI()

@app.middleware("http")
async def audit_middleware(request: Request, call_next):
    """Automatically log all API requests."""
    start_time = time()

    try:
        response = await call_next(request)
        duration_ms = int((time() - start_time) * 1000)

        # Log successful request
        audit_agent = AuditAgent(db=request.state.db)
        await audit_agent.log_operation(
            action=f"{request.method}_{request.url.path}",
            resource_type="api_request",
            resource_id=None,
            tenant_id=request.state.tenant_id,
            user_id=request.state.user_id,
            request_method=request.method,
            request_path=str(request.url.path),
            request_duration_ms=duration_ms,
            ip_address=request.client.host,
            user_agent=request.headers.get("user-agent"),
            status="success",
        )

        return response

    except Exception as e:
        # Log failed request
        # ... (similar to above but with error status)
        raise
```

## Compliance Requirements

### PT2030 10-Year Retention

All audit logs are:
1. **Immutable** - Once created, logs cannot be modified
2. **Permanent** - Stored for 10 years minimum
3. **Complete** - Every operation is logged
4. **Traceable** - Full input/output hashing for verification
5. **Timestamped** - Exact timestamp of every operation

### Data Integrity

The AuditAgent ensures data integrity through:
- **SHA-256 hashing** of all input/output data
- **Deterministic hashing** (same data = same hash)
- **Size tracking** for storage cost calculation
- **Immutable records** (no updates, only inserts)

### Audit Trail Completeness

The `generate_audit_report()` method calculates compliance percentage:

```python
compliance_percentage = (
    operations_with_audit_trail / total_operations * 100
)
```

An operation has a complete audit trail if both `input_hash` and `output_hash` are present.

## Performance Considerations

### Database Indexes

The `AuditLog` model includes optimized indexes:
- `idx_audit_tenant_created` (tenant_id, created_at) - For time-range queries
- `idx_audit_resource` (resource_type, resource_id) - For resource lookups
- `idx_audit_user` (user_id) - For user activity tracking
- `idx_audit_action` (action) - For action filtering
- `idx_audit_cost` (cost_euros) - For cost analysis

### Query Optimization

All queries include:
- **Limit parameters** to prevent unbounded result sets
- **Tenant filtering** enforced via RLS and explicit WHERE clauses
- **Index usage** for efficient filtering and sorting
- **Pagination support** via limit/offset

### Cost Aggregation

The `calculate_project_cost()` and `generate_audit_report()` methods use efficient aggregation:
- Single query per metric where possible
- In-memory aggregation for complex breakdowns
- Decimal precision for financial accuracy

## Testing

The test suite (`backend/tests/test_audit_agent.py`) includes:

1. **Basic Logging Tests**
   - Simple operation logging
   - Data hashing verification
   - Token/cost tracking
   - Custom metadata
   - Error logging

2. **Query Tests**
   - Audit trail retrieval
   - Pagination
   - Date range filtering
   - Action/agent/status filtering
   - Multi-tenant isolation

3. **Cost Calculation Tests**
   - Project cost breakdown
   - Agent-level costs
   - Processing time metrics
   - Storage estimation

4. **Reporting Tests**
   - Audit report generation
   - Operation breakdowns
   - Error tracking
   - Compliance metrics

5. **Helper Tests**
   - Data hashing consistency
   - Token cost calculation
   - Daily cost summaries

Run tests with:
```bash
pytest backend/tests/test_audit_agent.py -v
```

## Error Handling

The AuditAgent includes comprehensive error handling:

```python
try:
    log = await audit_agent.log_operation(...)
except Exception as e:
    logger.error(f"Failed to log operation: {e}")
    # Rollback transaction
    await db.rollback()
    raise
```

All methods include:
- Try/except blocks with proper rollback
- Detailed error logging
- Exception re-raising for upstream handling

## Best Practices

### 1. Always Log Operations

Every significant operation should be logged:
```python
# Before
result = await process_file(file_path)

# After
result = await process_file(file_path)
await audit_agent.log_operation(
    action="process_file",
    resource_id=file_id,
    # ... other params
)
```

### 2. Include Metadata

Add contextual metadata for debugging and analysis:
```python
await audit_agent.log_operation(
    action="calculate_valf",
    # ...
    metadata={
        "model_version": "1.0.0",
        "discount_rate": 0.04,
        "project_duration_years": 5,
    },
)
```

### 3. Hash Critical Data

For financial calculations, always hash input/output:
```python
await audit_agent.log_operation(
    action="calculate_financial_model",
    input_data=financial_input,
    output_data=financial_output,
    # Hashes auto-generated
)
```

### 4. Track Request Duration

Include processing time for performance monitoring:
```python
start_time = time()
result = await expensive_operation()
duration_ms = int((time() - start_time) * 1000)

await audit_agent.log_operation(
    # ...
    request_duration_ms=duration_ms,
)
```

### 5. Monitor Daily Costs

Check daily costs regularly to avoid overages:
```python
summary = await audit_agent.get_daily_cost_summary(tenant_id)
if summary['limit_percentage'] > 80:
    # Alert tenant
    send_alert(f"Daily cost limit at {summary['limit_percentage']:.1f}%")
```

## Configuration

The AuditAgent uses settings from `backend/core/config.py`:

```python
# Cost Control
claude_daily_limit_euros = 50.0      # Daily spending limit
claude_monthly_limit_euros = 1000.0  # Monthly spending limit

# Audit Configuration
audit_retention_years = 10           # PT2030 requirement
audit_immutable_log = True           # No updates allowed
audit_hash_algorithm = "sha256"      # SHA-256 for hashing

# Claude Pricing
claude_model = "claude-3-5-sonnet-20241022"
```

## Future Enhancements

Potential improvements for v2:

1. **Real-time Alerts**
   - WebSocket notifications for cost limit breaches
   - Slack/email alerts for errors
   - Daily/weekly cost summaries

2. **Advanced Analytics**
   - Cost forecasting based on usage trends
   - Agent performance benchmarking
   - Anomaly detection for unusual costs

3. **Export Functionality**
   - CSV/Excel export of audit logs
   - PDF compliance reports
   - JSON export for external systems

4. **Cost Optimization**
   - Token usage optimization recommendations
   - Agent efficiency scoring
   - Cost reduction suggestions

5. **Enhanced Security**
   - Encrypted audit log storage
   - Digital signatures for tamper detection
   - Blockchain-based immutability proof

## Support and Documentation

- **Implementation**: `backend/agents/audit_agent.py`
- **Tests**: `backend/tests/test_audit_agent.py`
- **Examples**: `backend/agents/audit_agent_example.py`
- **Models**: `backend/models/evf.py` (AuditLog model)

For questions or issues, refer to the main project documentation or contact the development team.
