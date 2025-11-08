# AuditAgent Quick Reference

## Import

```python
from backend.agents.audit_agent import (
    AuditAgent,
    AgentType,
    OperationStatus,
    ResourceType,
    ProjectCost,
    AuditReport,
)
```

## Initialization

```python
audit_agent = AuditAgent(db=db_session)
```

## Common Operations

### Log Basic Operation

```python
log = await audit_agent.log_operation(
    action="operation_name",
    resource_type=ResourceType.EVF_PROJECT.value,
    resource_id=resource_uuid,
    tenant_id=tenant_uuid,
    user_id=user_uuid,
)
```

### Log with Cost Tracking

```python
log = await audit_agent.log_operation(
    action="generate_narrative",
    resource_type=ResourceType.NARRATIVE_GENERATION.value,
    resource_id=resource_uuid,
    tenant_id=tenant_uuid,
    agent_name=AgentType.NARRATIVE_AGENT.value,
    tokens_used=15000,  # Cost auto-calculated
)
```

### Log with Data Hashing

```python
log = await audit_agent.log_operation(
    action="calculate_valf",
    resource_type=ResourceType.FINANCIAL_MODEL.value,
    resource_id=resource_uuid,
    tenant_id=tenant_uuid,
    agent_name=AgentType.FINANCIAL_AGENT.value,
    input_data={"investment": 500000},
    output_data={"valf": -42000, "trf": 3.5},
)
```

### Log Error

```python
await audit_agent.log_operation(
    action="parse_file",
    resource_type=ResourceType.FILE_UPLOAD.value,
    resource_id=resource_uuid,
    tenant_id=tenant_uuid,
    status=OperationStatus.ERROR.value,
    error_message=str(exception),
    error_stacktrace=traceback.format_exc(),
)
```

### Get Project Audit Trail

```python
logs = await audit_agent.get_project_audit_trail(
    project_id=project_uuid,
    tenant_id=tenant_uuid,
)
```

### Query Logs by Criteria

```python
# Get errors from last 7 days
logs = await audit_agent.get_logs_by_criteria(
    tenant_id=tenant_uuid,
    start_date=datetime.utcnow() - timedelta(days=7),
    status=OperationStatus.ERROR.value,
)

# Get operations by agent
logs = await audit_agent.get_logs_by_criteria(
    tenant_id=tenant_uuid,
    agent_name=AgentType.NARRATIVE_AGENT.value,
)

# Get specific action
logs = await audit_agent.get_logs_by_criteria(
    tenant_id=tenant_uuid,
    action="upload_file",
)
```

### Calculate Project Cost

```python
cost = await audit_agent.calculate_project_cost(
    project_id=project_uuid,
    tenant_id=tenant_uuid,
)

print(f"Total: €{cost.total_cost_euros}")
print(f"Tokens: {cost.total_tokens_used:,}")
print(f"Operations: {cost.operation_count}")
```

### Generate Audit Report

```python
report = await audit_agent.generate_audit_report(
    tenant_id=tenant_uuid,
    start_date=datetime.utcnow() - timedelta(days=30),
    end_date=datetime.utcnow(),
)

print(f"Total ops: {report.total_operations}")
print(f"Total cost: €{report.total_cost_euros}")
print(f"Compliance: {report.compliance_percentage}%")
```

### Check Daily Cost

```python
summary = await audit_agent.get_daily_cost_summary(
    tenant_id=tenant_uuid,
)

if summary['limit_exceeded']:
    # Alert!
    pass
```

## Enums

### AgentType

```python
AgentType.INPUT_AGENT
AgentType.COMPLIANCE_AGENT
AgentType.FINANCIAL_AGENT
AgentType.NARRATIVE_AGENT
AgentType.AUDIT_AGENT
AgentType.ORCHESTRATOR
```

### ResourceType

```python
ResourceType.EVF_PROJECT
ResourceType.FINANCIAL_MODEL
ResourceType.FILE_UPLOAD
ResourceType.COMPLIANCE_CHECK
ResourceType.NARRATIVE_GENERATION
ResourceType.USER
ResourceType.TENANT
```

### OperationStatus

```python
OperationStatus.SUCCESS
OperationStatus.ERROR
OperationStatus.WARNING
OperationStatus.IN_PROGRESS
```

## Cost Calculation

### Token Cost

```python
# Automatic calculation
tokens = 15000
cost = audit_agent._calculate_token_cost(tokens)  # €0.135

# Or specify manually
await audit_agent.log_operation(
    # ...
    tokens_used=15000,
    cost_euros=Decimal("0.135"),  # Override
)
```

### Pricing

- **Claude Input**: €3 per 1M tokens
- **Claude Output**: €15 per 1M tokens
- **Average**: €9 per 1M tokens
- **Storage**: €0.023 per GB-month

## Full Example

```python
from backend.agents.audit_agent import AuditAgent, AgentType, ResourceType
from datetime import datetime
from uuid import uuid4

async def process_evf(db, tenant_id, user_id, project_id):
    audit = AuditAgent(db=db)

    # 1. Upload
    await audit.log_operation(
        action="upload_file",
        resource_type=ResourceType.FILE_UPLOAD.value,
        resource_id=uuid4(),
        tenant_id=tenant_id,
        user_id=user_id,
        project_id=project_id,
        agent_name=AgentType.INPUT_AGENT.value,
        metadata={"file_name": "saft.xml"},
    )

    # 2. Parse
    await audit.log_operation(
        action="parse_saft",
        resource_type=ResourceType.FILE_UPLOAD.value,
        resource_id=uuid4(),
        tenant_id=tenant_id,
        project_id=project_id,
        agent_name=AgentType.INPUT_AGENT.value,
        input_data={"hash": "abc123"},
        output_data={"companies": 1, "transactions": 5000},
    )

    # 3. Calculate
    await audit.log_operation(
        action="calculate_valf",
        resource_type=ResourceType.FINANCIAL_MODEL.value,
        resource_id=uuid4(),
        tenant_id=tenant_id,
        project_id=project_id,
        agent_name=AgentType.FINANCIAL_AGENT.value,
        input_data={"investment": 500000},
        output_data={"valf": -42000, "trf": 3.5},
    )

    # 4. Generate (uses Claude)
    await audit.log_operation(
        action="generate_narrative",
        resource_type=ResourceType.NARRATIVE_GENERATION.value,
        resource_id=uuid4(),
        tenant_id=tenant_id,
        project_id=project_id,
        agent_name=AgentType.NARRATIVE_AGENT.value,
        tokens_used=12500,
    )

    # Get cost
    cost = await audit.calculate_project_cost(project_id, tenant_id)
    return cost
```

## FastAPI Integration

```python
from fastapi import Request
from time import time

@app.middleware("http")
async def audit_middleware(request: Request, call_next):
    start_time = time()
    response = await call_next(request)

    audit = AuditAgent(db=request.state.db)
    await audit.log_operation(
        action=f"{request.method}_{request.url.path}",
        resource_type="api_request",
        resource_id=None,
        tenant_id=request.state.tenant_id,
        user_id=request.state.user_id,
        request_method=request.method,
        request_path=str(request.url.path),
        request_duration_ms=int((time() - start_time) * 1000),
        ip_address=request.client.host,
    )

    return response
```

## Error Handling

```python
try:
    result = await risky_operation()

    await audit.log_operation(
        action="risky_operation",
        status=OperationStatus.SUCCESS.value,
        # ...
    )
except Exception as e:
    import traceback

    await audit.log_operation(
        action="risky_operation",
        status=OperationStatus.ERROR.value,
        error_message=str(e),
        error_stacktrace=traceback.format_exc(),
        # ...
    )
    raise
```

## Tips

1. **Always include tenant_id** - Required for multi-tenant isolation
2. **Hash important data** - Use input_data/output_data for compliance
3. **Track tokens** - Essential for cost monitoring
4. **Add metadata** - Helps with debugging and analysis
5. **Log errors** - Include stack traces for troubleshooting
6. **Check daily costs** - Monitor to avoid overages

## Common Queries

```python
# All errors today
errors = await audit.get_logs_by_criteria(
    tenant_id=tenant_id,
    start_date=datetime.utcnow().replace(hour=0, minute=0, second=0),
    status=OperationStatus.ERROR.value,
)

# All operations for a user
user_logs = await audit.get_logs_by_criteria(
    tenant_id=tenant_id,
    user_id=user_id,
)

# All expensive operations (>10k tokens)
# (requires custom query or filter in memory)
all_logs = await audit.get_logs_by_criteria(tenant_id=tenant_id)
expensive = [log for log in all_logs if log.tokens_used > 10000]

# Operations by date range
month_logs = await audit.get_logs_by_criteria(
    tenant_id=tenant_id,
    start_date=datetime(2024, 1, 1),
    end_date=datetime(2024, 1, 31),
)
```

## Files

- **Implementation**: `backend/agents/audit_agent.py`
- **Tests**: `backend/tests/test_audit_agent.py`
- **Examples**: `backend/agents/audit_agent_example.py`
- **Full README**: `backend/agents/AUDIT_AGENT_README.md`
- **Implementation Guide**: `backend/AUDIT_AGENT_IMPLEMENTATION.md`
