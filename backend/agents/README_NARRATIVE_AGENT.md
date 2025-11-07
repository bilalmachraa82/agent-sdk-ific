# NarrativeAgent Documentation

## Overview

The **NarrativeAgent** is a specialized AI agent responsible for generating professional Portuguese-language narrative sections for Economic Viability Studies (EVF) in PT2030 funding applications.

**Critical**: This is the **ONLY** agent in the system that uses LLM (Claude AI) for content generation. All financial calculations are performed deterministically by the FinancialAgent - the NarrativeAgent only generates explanatory text.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      NarrativeAgent                          │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  Input: FinancialContext + ComplianceContext                 │
│         ↓                                                     │
│  ┌──────────────────────────────────────────────────┐       │
│  │ Section Generation (3 parallel API calls)        │       │
│  ├──────────────────────────────────────────────────┤       │
│  │ 1. Executive Summary (500 words)                 │       │
│  │ 2. Methodology (300 words)                       │       │
│  │ 3. Recommendations (200 words)                   │       │
│  └──────────────────────────────────────────────────┘       │
│         ↓                                                     │
│  Cost Tracking + Token Counting + Audit Trail                │
│         ↓                                                     │
│  Output: NarrativeOutput (text + metadata)                   │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

## Key Features

### ✅ Core Capabilities

1. **Portuguese Language Generation** (PT-PT)
   - Native Portuguese output for EVF documents
   - Professional, technical tone
   - Compliant with PT2030 terminology

2. **Three Narrative Sections**
   - **Executive Summary** (~500 words): Overview, objectives, financial highlights
   - **Methodology** (~300 words): Calculation methods, assumptions, data sources
   - **Recommendations** (~200 words): Next steps, compliance guidance

3. **Financial Data Integration**
   - Uses FinancialAgent calculations (VALF, TRF, ratios)
   - Uses ComplianceAgent validation results
   - Never generates or modifies financial numbers

4. **Cost Control**
   - Hard token limits (10k tokens per EVF max)
   - Real-time cost tracking
   - Daily cost limits with automatic enforcement

5. **Caching System**
   - Cache similar projects to reduce API costs
   - Hash-based cache keys for deduplication
   - Optional caching enable/disable

6. **Error Handling**
   - Automatic retry with exponential backoff (3 attempts)
   - Graceful degradation on API errors
   - Detailed error logging

7. **Audit Trail**
   - SHA-256 input hashing
   - Token usage tracking
   - Generation timestamp and metadata

## Installation

### Dependencies

The NarrativeAgent requires:

```bash
pip install anthropic==0.39.0
pip install tenacity==9.0.0
pip install structlog==24.4.0
```

All dependencies are included in `/backend/requirements.txt`.

### Configuration

Add to your `.env` file:

```bash
# Claude AI Configuration
CLAUDE_API_KEY=sk-ant-xxxxx
CLAUDE_MODEL=claude-3-5-sonnet-20241022
CLAUDE_MAX_TOKENS=4096
CLAUDE_TEMPERATURE=0.7

# Cost Limits
CLAUDE_DAILY_LIMIT=50.0  # EUR
CLAUDE_MONTHLY_LIMIT=1000.0  # EUR
```

## Usage

### Basic Usage

```python
from backend.agents.narrative_agent import (
    NarrativeAgent,
    NarrativeInput,
    FinancialContext,
    ComplianceContext,
)
from backend.core.config import settings

# Initialize agent
agent = NarrativeAgent(
    api_key=settings.claude_api_key,
    model="claude-3-5-sonnet-20241022",
    temperature=0.7,
    max_tokens=4096,
    cost_limit_daily_euros=50.0,
)

# Create financial context (from FinancialAgent)
financial_context = FinancialContext(
    project_name="Modernização Industrial ABC",
    project_duration_years=5,
    total_investment=Decimal("500000.00"),
    eligible_investment=Decimal("450000.00"),
    funding_requested=Decimal("225000.00"),
    valf=Decimal("-50000.00"),  # Negative = needs funding
    trf=Decimal("3.5"),  # Below 4% = compliant
    pt2030_compliant=True,
    compliance_notes=["✅ Meets PT2030 requirements"],
    # ... more fields
)

# Create compliance context (from ComplianceAgent)
compliance_context = ComplianceContext(
    status="compliant",
    is_compliant=True,
    errors=[],
    suggestions={},
)

# Create input
narrative_input = NarrativeInput(
    financial_context=financial_context,
    compliance_context=compliance_context,
    company_name="ABC Indústrias Lda",
    company_sector="Indústria Transformadora",
    cache_key="abc-project-2024",  # Optional caching
)

# Generate narrative (async)
result = await agent.generate(narrative_input)

# Or use synchronous wrapper
result = agent.generate_sync(narrative_input)

# Access results
print(result.executive_summary)
print(result.methodology)
print(result.recommendations)
print(f"Cost: €{result.cost_euros}")
print(f"Tokens: {result.tokens_used}")
```

### Integration with Other Agents

```python
# 1. Calculate financials
financial_agent = FinancialAgent()
financial_output = financial_agent.calculate(financial_input)

# 2. Validate compliance
compliance_agent = ComplianceAgent()
compliance_output = compliance_agent.validate(project_data)

# 3. Generate narrative
narrative_agent = NarrativeAgent(api_key=settings.claude_api_key)

narrative_input = NarrativeInput(
    financial_context=FinancialContext(
        # Map from FinancialAgent output
        valf=financial_output.valf,
        trf=financial_output.trf,
        # ...
    ),
    compliance_context=ComplianceContext(
        # Map from ComplianceAgent output
        is_compliant=compliance_output.is_compliant,
        # ...
    ),
)

narrative_output = await narrative_agent.generate(narrative_input)
```

## API Reference

### NarrativeAgent

#### Constructor

```python
NarrativeAgent(
    api_key: str,
    model: str = "claude-3-5-sonnet-20241022",
    temperature: float = 0.7,
    max_tokens: int = 4096,
    cache_enabled: bool = True,
    cost_limit_daily_euros: float = 50.0,
)
```

**Parameters:**
- `api_key`: Anthropic API key
- `model`: Claude model version
- `temperature`: Generation temperature (0.0-1.0)
- `max_tokens`: Max tokens per API request
- `cache_enabled`: Enable result caching
- `cost_limit_daily_euros`: Daily cost limit in EUR

#### Methods

##### `async generate(input_data: NarrativeInput) -> NarrativeOutput`

Generate complete narrative asynchronously.

**Raises:**
- `ValueError`: If cost limits exceeded
- `RuntimeError`: If API calls fail after retries

##### `generate_sync(input_data: NarrativeInput) -> NarrativeOutput`

Synchronous wrapper for `generate()`.

##### `get_usage_stats() -> Dict`

Get current usage statistics.

**Returns:**
```python
{
    "daily_tokens": 15000,
    "daily_cost_euros": 0.25,
    "cache_size": 5,
    "cost_limit_euros": 50.0,
    "usage_percentage": 0.5,
}
```

##### `reset_daily_usage()`

Reset daily usage counters (call at midnight UTC).

##### `clear_cache()`

Clear narrative cache.

### Data Models

#### NarrativeInput

```python
class NarrativeInput(BaseModel):
    financial_context: FinancialContext  # Required
    compliance_context: ComplianceContext  # Required
    company_name: Optional[str] = None
    company_sector: Optional[str] = None
    project_description: Optional[str] = None
    strategic_objectives: List[str] = []
    language: str = "pt-PT"
    tone: str = "professional"
    include_technical_details: bool = True
    cache_key: Optional[str] = None
```

#### NarrativeOutput

```python
class NarrativeOutput(BaseModel):
    executive_summary: str
    methodology: str
    recommendations: str
    tokens_used: int
    cost_euros: Decimal
    generation_time_seconds: float
    word_count: Dict[str, int]
    model_used: str
    generation_timestamp: datetime
    input_hash: str
    cached: bool
```

## Cost Management

### Token Pricing (Claude 3.5 Sonnet)

- **Input tokens**: €0.000003 per token (~€3 per 1M tokens)
- **Output tokens**: €0.000015 per token (~€15 per 1M tokens)

### Typical Costs per EVF

- **Average tokens**: 2,000-4,000 total
- **Average cost**: €0.05-€0.10 per EVF
- **Daily capacity**: 500-1000 EVFs at €50/day limit

### Cost Control Best Practices

1. **Enable Caching**
   ```python
   agent = NarrativeAgent(cache_enabled=True)
   narrative_input.cache_key = f"{company_id}-{project_hash}"
   ```

2. **Set Daily Limits**
   ```python
   agent = NarrativeAgent(cost_limit_daily_euros=50.0)
   ```

3. **Monitor Usage**
   ```python
   stats = agent.get_usage_stats()
   if stats["usage_percentage"] > 80:
       alert_admin("High API usage")
   ```

4. **Batch Processing**
   - Process EVFs during off-peak hours
   - Use async generation for parallel processing

## Token Limits

### Hard Limits (Enforced)

- **Per EVF**: 10,000 tokens max
- **Per section**: 4,096 tokens max
- **Daily**: Based on `cost_limit_daily_euros`

### Soft Targets (Word Count)

- **Executive Summary**: ~500 words
- **Methodology**: ~300 words
- **Recommendations**: ~200 words
- **Total**: ~1,000 words

## Error Handling

### Automatic Retry

The agent automatically retries failed API calls with exponential backoff:

```python
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
)
async def _generate_section(...):
    # API call
```

### Error Types

1. **Cost Limit Exceeded**
   ```python
   ValueError: Daily cost limit exceeded: €50.05 / €50.00
   ```

2. **API Errors**
   ```python
   RuntimeError: Claude API error after 3 retries
   ```

3. **Token Limit Exceeded**
   ```python
   ValueError: Token limit exceeded for section
   ```

## Caching Strategy

### Cache Key Generation

```python
# Recommended: Use stable project identifiers
cache_key = f"{tenant_id}-{project_id}-{financial_hash[:8]}"

# Example
narrative_input.cache_key = "tenant-abc-proj-123-a1b2c3d4"
```

### Cache Behavior

- **Hit**: Return cached result immediately (0 cost)
- **Miss**: Generate new result, cache for future use
- **TTL**: Manual cache clearing (or Redis TTL in production)

### Production Cache (Redis)

```python
# In production, replace in-memory cache with Redis
import redis

redis_client = redis.from_url(settings.redis_url)

def _get_cached(cache_key: str) -> Optional[NarrativeOutput]:
    cached = redis_client.get(f"narrative:{cache_key}")
    if cached:
        return NarrativeOutput.model_validate_json(cached)
    return None
```

## Multi-Tenant Considerations

### Tenant Isolation

- Each tenant has separate cost tracking
- Cache keys include `tenant_id` for isolation
- Audit logs include `tenant_id` for traceability

### Tenant-Specific Limits

```python
class TenantConfig(BaseModel):
    tenant_id: UUID
    daily_cost_limit: Decimal
    monthly_cost_limit: Decimal
    cache_enabled: bool

# Load tenant config
tenant_config = get_tenant_config(tenant_id)

agent = NarrativeAgent(
    api_key=settings.claude_api_key,
    cost_limit_daily_euros=float(tenant_config.daily_cost_limit),
    cache_enabled=tenant_config.cache_enabled,
)
```

## Testing

### Run Tests

```bash
# All narrative agent tests
pytest backend/tests/test_narrative_agent.py -v

# Specific test
pytest backend/tests/test_narrative_agent.py::TestNarrativeGeneration -v

# With coverage
pytest backend/tests/test_narrative_agent.py --cov=backend.agents.narrative_agent
```

### Mock API for Testing

```python
from unittest.mock import AsyncMock, Mock

mock_message = Mock()
mock_message.content = [Mock(text="Test narrative")]
mock_message.usage = Mock(input_tokens=500, output_tokens=300)

mock_client = AsyncMock()
mock_client.messages.create.return_value = mock_message

agent.async_client = mock_client
```

## Examples

See `/backend/examples/narrative_agent_example.py` for complete examples:

1. **Compliant Project**: Generate narrative for PT2030-compliant project
2. **Non-Compliant Project**: Generate with compliance suggestions
3. **Synchronous Generation**: Use sync wrapper
4. **Cost Limits**: Demonstrate cost enforcement

Run examples:
```bash
cd backend
python examples/narrative_agent_example.py
```

## Production Checklist

- [ ] Set `CLAUDE_API_KEY` in production environment
- [ ] Configure daily/monthly cost limits
- [ ] Implement Redis caching (replace in-memory cache)
- [ ] Set up daily usage reset (cron job at midnight UTC)
- [ ] Configure monitoring/alerts for high usage
- [ ] Implement tenant-specific cost tracking
- [ ] Set up audit logging for all generations
- [ ] Test retry logic with API failures
- [ ] Validate Portuguese language output quality
- [ ] Monitor token usage and costs
- [ ] Set up rate limiting per tenant

## Performance Metrics

### Target Metrics

- **Generation Time**: < 10 seconds per EVF
- **Token Usage**: 2,000-4,000 tokens per EVF
- **Cost**: €0.05-€0.10 per EVF
- **Cache Hit Rate**: > 30% for similar projects
- **Error Rate**: < 1% (after retries)

### Monitoring

```python
# Log generation metrics
logger.info(
    "narrative_generated",
    project_id=project_id,
    tokens_used=result.tokens_used,
    cost_euros=float(result.cost_euros),
    generation_time=result.generation_time_seconds,
    cached=result.cached,
)
```

## Troubleshooting

### Issue: High API Costs

**Solution**: Enable caching, reduce max_tokens, batch process

### Issue: Slow Generation

**Solution**: Use async generation, reduce temperature, cache common sections

### Issue: Poor Quality Output

**Solution**: Adjust prompts, increase temperature, provide more context

### Issue: API Rate Limits

**Solution**: Implement exponential backoff, reduce concurrent requests

### Issue: Token Limit Exceeded

**Solution**: Reduce max_tokens, simplify input context, split sections

## Future Enhancements

1. **Multi-Language Support**: Add pt-BR, English, Spanish
2. **Custom Templates**: Allow tenant-specific narrative templates
3. **Quality Scoring**: Implement automated quality checks
4. **A/B Testing**: Test different prompts for better output
5. **Streaming**: Stream output for real-time display
6. **Fine-Tuning**: Fine-tune model on PT2030 documents
7. **Structured Output**: Use Claude's structured output mode

## License

Part of EVF Portugal 2030 - Proprietary

## Support

For issues or questions, contact the development team or refer to:
- `/backend/ARCHITECTURE.md`
- `/backend/IMPLEMENTATION_GUIDE.md`
- `/CLAUDE.md`
