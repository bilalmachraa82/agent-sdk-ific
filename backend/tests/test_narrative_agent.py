"""
Tests for NarrativeAgent - AI-powered narrative generation.
"""

import pytest
from decimal import Decimal
from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch

from backend.agents.narrative_agent import (
    NarrativeAgent,
    NarrativeInput,
    NarrativeOutput,
    FinancialContext,
    ComplianceContext,
    TokenUsageTracker,
    NarrativeSection,
)


@pytest.fixture
def financial_context():
    """Sample financial context for testing."""
    return FinancialContext(
        project_name="Modernização Industrial XYZ",
        project_duration_years=5,
        fund_type="PT2030",
        total_investment=Decimal("500000.00"),
        eligible_investment=Decimal("450000.00"),
        funding_requested=Decimal("225000.00"),
        valf=Decimal("-50000.00"),  # Negative for PT2030 compliance
        trf=Decimal("3.5"),  # Below 4% for PT2030 compliance
        payback_period=Decimal("4.2"),
        roi=Decimal("15.5"),
        pt2030_compliant=True,
        compliance_notes=[
            "✅ VALF is negative (-50000.00 EUR) - meets PT2030 requirement.",
            "✅ TRF (3.50%) < discount rate (4.00%) - meets PT2030 requirement.",
        ],
        financial_ratios={
            "gross_margin": 35.5,
            "operating_margin": 22.3,
            "roi": 15.5,
        },
        assumptions={
            "discount_rate": "4%",
            "project_duration": "5 years",
            "calculation_method": "Deterministic (numpy-financial)",
        },
    )


@pytest.fixture
def compliance_context():
    """Sample compliance context for testing."""
    return ComplianceContext(
        status="compliant",
        is_compliant=True,
        errors=[],
        suggestions={},
    )


@pytest.fixture
def narrative_input(financial_context, compliance_context):
    """Sample narrative input for testing."""
    return NarrativeInput(
        financial_context=financial_context,
        compliance_context=compliance_context,
        company_name="Empresa XYZ Lda",
        company_sector="Indústria Transformadora",
        project_description="Modernização de linha de produção",
        strategic_objectives=[
            "Aumentar eficiência produtiva",
            "Reduzir consumo energético",
            "Melhorar qualidade do produto",
        ],
    )


@pytest.fixture
def mock_claude_response():
    """Mock Claude API response."""
    from anthropic.types import TextBlock

    mock_message = Mock()
    mock_text_block = TextBlock(text="Este é um sumário executivo de teste gerado pelo Claude.", type="text")
    mock_message.content = [mock_text_block]
    mock_message.usage = Mock(input_tokens=500, output_tokens=300)
    return mock_message


class TestTokenUsageTracker:
    """Test token usage tracking and cost calculation."""

    def test_initial_state(self):
        """Test tracker initialization."""
        tracker = TokenUsageTracker()
        assert tracker.input_tokens == 0
        assert tracker.output_tokens == 0
        assert tracker.total_tokens == 0
        assert tracker.cost_euros == Decimal("0.00")

    def test_update_tokens(self):
        """Test token count updates."""
        tracker = TokenUsageTracker()
        tracker.update(1000, 500)

        assert tracker.input_tokens == 1000
        assert tracker.output_tokens == 500
        assert tracker.total_tokens == 1500

    def test_cost_calculation(self):
        """Test cost calculation based on tokens."""
        tracker = TokenUsageTracker()

        # Update with 1000 input tokens and 500 output tokens
        tracker.update(1000, 500)

        # Expected cost:
        # Input: 1000 * 0.000003 = 0.003
        # Output: 500 * 0.000015 = 0.0075
        # Total: 0.0105
        expected_cost = Decimal("0.0105")

        assert tracker.cost_euros == expected_cost

    def test_cumulative_updates(self):
        """Test cumulative token tracking."""
        tracker = TokenUsageTracker()

        tracker.update(500, 200)
        tracker.update(300, 150)

        assert tracker.input_tokens == 800
        assert tracker.output_tokens == 350
        assert tracker.total_tokens == 1150


class TestNarrativeAgent:
    """Test NarrativeAgent initialization and configuration."""

    def test_initialization(self):
        """Test agent initialization with default parameters."""
        agent = NarrativeAgent(api_key="test-api-key")

        assert agent.model == "claude-3-5-sonnet-20241022"
        assert agent.temperature == 0.7
        assert agent.max_tokens == 4096
        assert agent.cache_enabled is True
        assert agent.cost_limit_daily_euros == 50.0

    def test_initialization_with_custom_params(self):
        """Test agent initialization with custom parameters."""
        agent = NarrativeAgent(
            api_key="test-api-key",
            model="claude-3-opus-20240229",
            temperature=0.5,
            max_tokens=2048,
            cache_enabled=False,
            cost_limit_daily_euros=100.0,
        )

        assert agent.model == "claude-3-opus-20240229"
        assert agent.temperature == 0.5
        assert agent.max_tokens == 2048
        assert agent.cache_enabled is False
        assert agent.cost_limit_daily_euros == 100.0

    def test_max_tokens_capping(self):
        """Test that max_tokens is capped at MAX_TOKENS_PER_SECTION."""
        agent = NarrativeAgent(
            api_key="test-api-key",
            max_tokens=10000,  # Exceeds MAX_TOKENS_PER_SECTION
        )

        assert agent.max_tokens == NarrativeAgent.MAX_TOKENS_PER_SECTION


class TestNarrativeGeneration:
    """Test narrative generation functionality."""

    @pytest.mark.asyncio
    @patch('backend.agents.narrative_agent.AsyncAnthropic')
    async def test_generate_executive_summary(
        self,
        mock_anthropic,
        narrative_input,
        mock_claude_response
    ):
        """Test executive summary generation."""

        # Setup mock
        mock_client = AsyncMock()
        mock_client.messages.create.return_value = mock_claude_response
        mock_anthropic.return_value = mock_client

        agent = NarrativeAgent(api_key="test-api-key")
        agent.async_client = mock_client

        tracker = TokenUsageTracker()
        result = await agent._generate_executive_summary(narrative_input, tracker)

        # Assertions
        assert isinstance(result, str)
        assert len(result) > 0
        assert tracker.input_tokens == 500
        assert tracker.output_tokens == 300
        assert tracker.total_tokens == 800

    @pytest.mark.asyncio
    @patch('backend.agents.narrative_agent.AsyncAnthropic')
    async def test_generate_methodology(
        self,
        mock_anthropic,
        narrative_input,
        mock_claude_response
    ):
        """Test methodology section generation."""

        mock_client = AsyncMock()
        mock_client.messages.create.return_value = mock_claude_response
        mock_anthropic.return_value = mock_client

        agent = NarrativeAgent(api_key="test-api-key")
        agent.async_client = mock_client

        tracker = TokenUsageTracker()
        result = await agent._generate_methodology(narrative_input, tracker)

        assert isinstance(result, str)
        assert len(result) > 0

    @pytest.mark.asyncio
    @patch('backend.agents.narrative_agent.AsyncAnthropic')
    async def test_generate_recommendations(
        self,
        mock_anthropic,
        narrative_input,
        mock_claude_response
    ):
        """Test recommendations section generation."""

        mock_client = AsyncMock()
        mock_client.messages.create.return_value = mock_claude_response
        mock_anthropic.return_value = mock_client

        agent = NarrativeAgent(api_key="test-api-key")
        agent.async_client = mock_client

        tracker = TokenUsageTracker()
        result = await agent._generate_recommendations(narrative_input, tracker)

        assert isinstance(result, str)
        assert len(result) > 0

    @pytest.mark.asyncio
    @patch('backend.agents.narrative_agent.AsyncAnthropic')
    async def test_full_narrative_generation(
        self,
        mock_anthropic,
        narrative_input,
    ):
        """Test complete narrative generation workflow."""
        from anthropic.types import TextBlock

        # Create mock responses for all three sections
        mock_exec_summary = Mock()
        mock_exec_summary.content = [TextBlock(text="Sumário executivo de teste.", type="text")]
        mock_exec_summary.usage = Mock(input_tokens=500, output_tokens=600)

        mock_methodology = Mock()
        mock_methodology.content = [TextBlock(text="Metodologia de teste.", type="text")]
        mock_methodology.usage = Mock(input_tokens=400, output_tokens=400)

        mock_recommendations = Mock()
        mock_recommendations.content = [TextBlock(text="Recomendações de teste.", type="text")]
        mock_recommendations.usage = Mock(input_tokens=300, output_tokens=250)

        mock_client = AsyncMock()
        mock_client.messages.create.side_effect = [
            mock_exec_summary,
            mock_methodology,
            mock_recommendations,
        ]
        mock_anthropic.return_value = mock_client

        agent = NarrativeAgent(api_key="test-api-key")
        agent.async_client = mock_client

        result = await agent.generate(narrative_input)

        # Assertions
        assert isinstance(result, NarrativeOutput)
        assert result.executive_summary == "Sumário executivo de teste."
        assert result.methodology == "Metodologia de teste."
        assert result.recommendations == "Recomendações de teste."
        assert result.tokens_used == 2450  # 1200 input + 1250 output
        assert result.cost_euros > Decimal("0")
        assert result.generation_time_seconds > 0
        assert result.model_used == "claude-3-5-sonnet-20241022"
        assert not result.cached


class TestCaching:
    """Test narrative caching functionality."""

    @pytest.mark.asyncio
    @patch('backend.agents.narrative_agent.AsyncAnthropic')
    async def test_cache_hit(self, mock_anthropic, narrative_input):
        """Test that cached results are returned on second call."""
        from anthropic.types import TextBlock

        # Create mock response
        mock_response = Mock()
        mock_response.content = [TextBlock(text="Cached response", type="text")]
        mock_response.usage = Mock(input_tokens=100, output_tokens=100)

        mock_client = AsyncMock()
        mock_client.messages.create.return_value = mock_response
        mock_anthropic.return_value = mock_client

        agent = NarrativeAgent(api_key="test-api-key", cache_enabled=True)
        agent.async_client = mock_client

        # Set cache key
        narrative_input.cache_key = "test-project-123"

        # First call - should hit API
        result1 = await agent.generate(narrative_input)
        assert not result1.cached

        # Second call - should hit cache
        result2 = await agent.generate(narrative_input)
        assert result2 == result1

        # API should only be called 3 times (once per section for first call)
        assert mock_client.messages.create.call_count == 3

    @pytest.mark.asyncio
    async def test_cache_disabled(self, narrative_input):
        """Test that caching can be disabled."""

        agent = NarrativeAgent(api_key="test-api-key", cache_enabled=False)

        # Even with cache_key set, caching should not occur
        narrative_input.cache_key = "test-project-123"

        # Manually add to cache
        cached_output = NarrativeOutput(
            executive_summary="Cached",
            methodology="Cached",
            recommendations="Cached",
            tokens_used=100,
            cost_euros=Decimal("0.01"),
            generation_time_seconds=1.0,
            word_count={"executive_summary": 1, "methodology": 1, "recommendations": 1},
            model_used="test",
            input_hash="test-hash",
        )
        agent._cache["test-project-123"] = cached_output

        # _get_cached should still return the cached item (it's in the dict)
        # but generate() won't use it when cache_enabled=False
        result = agent._get_cached("test-project-123")
        assert result is not None  # Item is in cache dict

        # But cache_enabled flag prevents usage in generate()
        assert agent.cache_enabled is False


class TestCostControl:
    """Test cost control and limits."""

    def test_cost_limit_check(self):
        """Test that cost limit is enforced."""
        agent = NarrativeAgent(
            api_key="test-api-key",
            cost_limit_daily_euros=10.0
        )

        # Simulate high usage
        agent._daily_usage.cost_euros = Decimal("15.00")

        with pytest.raises(ValueError, match="Daily cost limit exceeded"):
            agent._check_cost_limits()

    def test_cost_limit_not_exceeded(self):
        """Test that generation proceeds when under cost limit."""
        agent = NarrativeAgent(
            api_key="test-api-key",
            cost_limit_daily_euros=50.0
        )

        # Simulate low usage
        agent._daily_usage.cost_euros = Decimal("5.00")

        # Should not raise
        agent._check_cost_limits()

    def test_usage_stats(self):
        """Test usage statistics reporting."""
        agent = NarrativeAgent(
            api_key="test-api-key",
            cost_limit_daily_euros=50.0
        )

        # Simulate some usage
        agent._daily_usage.update(5000, 3000)

        stats = agent.get_usage_stats()

        assert stats["daily_tokens"] == 8000
        assert stats["daily_cost_euros"] > 0
        assert stats["cost_limit_euros"] == 50.0
        assert 0 <= stats["usage_percentage"] <= 100

    def test_reset_daily_usage(self):
        """Test daily usage reset."""
        agent = NarrativeAgent(api_key="test-api-key")

        # Simulate usage
        agent._daily_usage.update(10000, 5000)
        assert agent._daily_usage.total_tokens == 15000

        # Reset
        agent.reset_daily_usage()

        assert agent._daily_usage.total_tokens == 0
        assert agent._daily_usage.cost_euros == Decimal("0.00")


class TestPromptGeneration:
    """Test prompt building functionality."""

    def test_executive_summary_prompt(self, narrative_input):
        """Test executive summary prompt generation."""
        agent = NarrativeAgent(api_key="test-api-key")

        prompt = agent._build_executive_summary_prompt(narrative_input)

        # Check that prompt contains key information
        assert "Modernização Industrial XYZ" in prompt
        assert "PT2030" in prompt
        assert "500,000.00" in prompt  # Total investment (with comma formatting)
        assert "-50,000.00" in prompt  # VALF (with comma formatting)
        assert "3.50" in prompt  # TRF
        assert "500 palavras" in prompt  # Word target
        assert "Português de Portugal" in prompt

    def test_methodology_prompt(self, narrative_input):
        """Test methodology prompt generation."""
        agent = NarrativeAgent(api_key="test-api-key")

        prompt = agent._build_methodology_prompt(narrative_input)

        assert "Metodologia e Pressupostos" in prompt
        assert "300 palavras" in prompt
        assert "4%" in prompt  # Discount rate
        assert "Deterministic" in prompt

    def test_recommendations_prompt_compliant(self, narrative_input):
        """Test recommendations prompt for compliant project."""
        agent = NarrativeAgent(api_key="test-api-key")

        prompt = agent._build_recommendations_prompt(narrative_input)

        assert "Recomendações e Conclusões" in prompt
        assert "200 palavras" in prompt
        assert "CUMPRE" in prompt
        assert "SIM" in prompt  # Conformidade

    def test_recommendations_prompt_non_compliant(self, narrative_input):
        """Test recommendations prompt for non-compliant project."""
        agent = NarrativeAgent(api_key="test-api-key")

        # Make project non-compliant
        narrative_input.compliance_context.is_compliant = False
        narrative_input.compliance_context.suggestions = {
            "valf": "Reduza custos operacionais ou aumente receitas projetadas"
        }

        prompt = agent._build_recommendations_prompt(narrative_input)

        assert "NÃO CUMPRE" in prompt
        assert "NÃO" in prompt  # Conformidade
        assert "Sugestões" in prompt


class TestInputHashing:
    """Test input data hashing for audit trail."""

    def test_input_hash_consistency(self, narrative_input):
        """Test that same input produces same hash."""
        agent = NarrativeAgent(api_key="test-api-key")

        hash1 = agent._hash_input(narrative_input)
        hash2 = agent._hash_input(narrative_input)

        assert hash1 == hash2
        assert len(hash1) == 64  # SHA-256 produces 64-char hex string

    def test_input_hash_uniqueness(self, narrative_input, financial_context):
        """Test that different inputs produce different hashes."""
        agent = NarrativeAgent(api_key="test-api-key")

        hash1 = agent._hash_input(narrative_input)

        # Modify input
        narrative_input.financial_context.total_investment = Decimal("600000.00")

        hash2 = agent._hash_input(narrative_input)

        assert hash1 != hash2


class TestErrorHandling:
    """Test error handling and retries."""

    @pytest.mark.asyncio
    @patch('backend.agents.narrative_agent.AsyncAnthropic')
    async def test_retry_on_api_error(self, mock_anthropic, narrative_input):
        """Test that API errors trigger retries."""
        from anthropic.types import TextBlock

        mock_client = AsyncMock()

        # First two calls fail, third succeeds
        mock_success = Mock()
        mock_success.content = [TextBlock(text="Success after retry", type="text")]
        mock_success.usage = Mock(input_tokens=100, output_tokens=100)

        mock_client.messages.create.side_effect = [
            Exception("API Error 1"),
            Exception("API Error 2"),
            mock_success,
        ]
        mock_anthropic.return_value = mock_client

        agent = NarrativeAgent(api_key="test-api-key")
        agent.async_client = mock_client

        tracker = TokenUsageTracker()
        result = await agent._generate_executive_summary(narrative_input, tracker)

        assert result == "Success after retry"
        assert mock_client.messages.create.call_count == 3

    @pytest.mark.asyncio
    @patch('backend.agents.narrative_agent.AsyncAnthropic')
    async def test_max_retries_exceeded(self, mock_anthropic, narrative_input):
        """Test that max retries causes failure."""
        from tenacity import RetryError

        mock_client = AsyncMock()
        mock_client.messages.create.side_effect = Exception("Persistent API Error")
        mock_anthropic.return_value = mock_client

        agent = NarrativeAgent(api_key="test-api-key")
        agent.async_client = mock_client

        tracker = TokenUsageTracker()

        # Tenacity wraps the exception in RetryError
        with pytest.raises(RetryError):
            await agent._generate_executive_summary(narrative_input, tracker)


class TestSyncWrapper:
    """Test synchronous wrapper for async methods."""

    @patch('backend.agents.narrative_agent.AsyncAnthropic')
    def test_generate_sync(self, mock_anthropic, narrative_input):
        """Test synchronous generation wrapper."""
        from anthropic.types import TextBlock

        # Create mock responses
        mock_response = Mock()
        mock_response.content = [TextBlock(text="Sync test", type="text")]
        mock_response.usage = Mock(input_tokens=100, output_tokens=100)

        mock_client = AsyncMock()
        mock_client.messages.create.return_value = mock_response
        mock_anthropic.return_value = mock_client

        agent = NarrativeAgent(api_key="test-api-key")
        agent.async_client = mock_client

        result = agent.generate_sync(narrative_input)

        assert isinstance(result, NarrativeOutput)
        assert result.executive_summary == "Sync test"
