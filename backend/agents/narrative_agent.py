"""
NarrativeAgent - AI-Powered Narrative Generation for EVF Documents
Generates executive summary, methodology, and recommendations using Claude AI.

CRITICAL: This is the ONLY agent that uses LLM for content generation.
Financial calculations are NEVER done by AI - only narrative text generation.
"""

from typing import Dict, List, Optional, Tuple, ClassVar
from datetime import datetime
from decimal import Decimal
import asyncio
import hashlib
import json
from enum import Enum

from anthropic import Anthropic, AsyncAnthropic
from anthropic.types import Message, TextBlock
from pydantic import BaseModel, Field, field_validator
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type
)
import structlog

logger = structlog.get_logger(__name__)


class NarrativeSection(str, Enum):
    """Sections of the EVF narrative."""
    EXECUTIVE_SUMMARY = "executive_summary"
    METHODOLOGY = "methodology"
    RECOMMENDATIONS = "recommendations"


class FinancialContext(BaseModel):
    """Financial data context for narrative generation."""
    # Project information
    project_name: str
    project_duration_years: int
    fund_type: str = "PT2030"

    # Investment metrics
    total_investment: Decimal
    eligible_investment: Decimal
    funding_requested: Decimal

    # Financial results
    valf: Decimal = Field(..., description="Net Present Value in EUR")
    trf: Decimal = Field(..., description="Internal Rate of Return in %")
    payback_period: Optional[Decimal] = None
    roi: Optional[Decimal] = None

    # Compliance
    pt2030_compliant: bool
    compliance_notes: List[str] = Field(default_factory=list)

    # Additional context
    financial_ratios: Dict = Field(default_factory=dict)
    cash_flow_summary: Dict = Field(default_factory=dict)
    assumptions: Dict = Field(default_factory=dict)


class ComplianceContext(BaseModel):
    """Compliance validation context."""
    status: str
    is_compliant: bool
    errors: List[str] = Field(default_factory=list)
    suggestions: Dict = Field(default_factory=dict)
    validation_timestamp: datetime = Field(default_factory=datetime.utcnow)


class NarrativeInput(BaseModel):
    """Input data for narrative generation."""
    # Required contexts
    financial_context: FinancialContext
    compliance_context: ComplianceContext

    # Optional company/project context
    company_name: Optional[str] = None
    company_sector: Optional[str] = None
    project_description: Optional[str] = None
    strategic_objectives: List[str] = Field(default_factory=list)

    # Generation preferences
    language: str = Field(default="pt-PT", description="Output language (pt-PT or pt-BR)")
    tone: str = Field(default="professional", description="Narrative tone")
    include_technical_details: bool = Field(default=True)

    # Cache key for similar projects
    cache_key: Optional[str] = None


class NarrativeOutput(BaseModel):
    """Output from narrative generation."""
    # Generated sections
    executive_summary: str = Field(..., description="500-word executive summary")
    methodology: str = Field(..., description="300-word methodology section")
    recommendations: str = Field(..., description="200-word recommendations")

    # Metadata
    tokens_used: int = Field(..., description="Total tokens consumed")
    cost_euros: Decimal = Field(..., description="Generation cost in EUR")
    generation_time_seconds: float = Field(..., description="Total generation time")

    # Quality metrics
    word_count: Dict[str, int] = Field(..., description="Word count per section")
    model_used: str = Field(..., description="Claude model version")

    # Audit trail
    generation_timestamp: datetime = Field(default_factory=datetime.utcnow)
    input_hash: str = Field(..., description="SHA-256 hash of input data")
    cached: bool = Field(default=False, description="Whether result was cached")


class TokenUsageTracker(BaseModel):
    """Track token usage for cost control."""
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    cost_euros: Decimal = Decimal("0.00")

    # Pricing (as of claude-3-5-sonnet-20241022)
    INPUT_TOKEN_COST: ClassVar[Decimal] = Decimal("0.000003")  # $3 per 1M tokens = €0.000003 per token
    OUTPUT_TOKEN_COST: ClassVar[Decimal] = Decimal("0.000015")  # $15 per 1M tokens = €0.000015 per token

    def update(self, input_tokens: int, output_tokens: int):
        """Update token counts and calculate cost."""
        self.input_tokens += input_tokens
        self.output_tokens += output_tokens
        self.total_tokens = self.input_tokens + self.output_tokens

        # Calculate cost (USD to EUR approximation)
        input_cost = Decimal(str(self.input_tokens)) * self.INPUT_TOKEN_COST
        output_cost = Decimal(str(self.output_tokens)) * self.OUTPUT_TOKEN_COST
        self.cost_euros = input_cost + output_cost


class NarrativeAgent:
    """
    AI-powered narrative generation agent using Claude.

    Generates professional Portuguese-language narratives for EVF documents
    based on financial calculations and compliance validation results.

    IMPORTANT: This agent generates TEXT ONLY, never numbers or calculations.
    """

    VERSION = "1.0.0"
    AGENT_NAME = "NarrativeAgent"

    # Token limits (hard caps)
    MAX_TOKENS_PER_EVF = 10000
    MAX_TOKENS_PER_SECTION = 4096

    # Section word targets
    WORD_TARGETS = {
        NarrativeSection.EXECUTIVE_SUMMARY: 500,
        NarrativeSection.METHODOLOGY: 300,
        NarrativeSection.RECOMMENDATIONS: 200,
    }

    def __init__(
        self,
        api_key: str,
        model: str = "claude-3-5-sonnet-20241022",
        temperature: float = 0.7,
        max_tokens: int = 4096,
        cache_enabled: bool = True,
        cost_limit_daily_euros: float = 50.0,
    ):
        """
        Initialize NarrativeAgent.

        Args:
            api_key: Anthropic API key
            model: Claude model to use
            temperature: Generation temperature (0.0-1.0)
            max_tokens: Max tokens per request
            cache_enabled: Enable caching for similar projects
            cost_limit_daily_euros: Daily cost limit in EUR
        """
        self.model = model
        self.temperature = temperature
        self.max_tokens = min(max_tokens, self.MAX_TOKENS_PER_SECTION)
        self.cache_enabled = cache_enabled
        self.cost_limit_daily_euros = cost_limit_daily_euros

        # Initialize Anthropic client
        self.client = Anthropic(api_key=api_key)
        self.async_client = AsyncAnthropic(api_key=api_key)

        # In-memory cache (in production, use Redis)
        self._cache: Dict[str, NarrativeOutput] = {}

        # Daily usage tracking (in production, use Redis with TTL)
        self._daily_usage = TokenUsageTracker()

        logger.info(
            "narrative_agent_initialized",
            model=model,
            temperature=temperature,
            max_tokens=max_tokens
        )

    async def generate(self, input_data: NarrativeInput) -> NarrativeOutput:
        """
        Generate complete EVF narrative asynchronously.

        Args:
            input_data: Financial and compliance context

        Returns:
            NarrativeOutput with all sections and metadata

        Raises:
            ValueError: If cost limits are exceeded
            RuntimeError: If API calls fail after retries
        """
        start_time = datetime.utcnow()

        # Check cost limits
        self._check_cost_limits()

        # Calculate input hash for caching
        input_hash = self._hash_input(input_data)

        # Check cache if enabled
        if self.cache_enabled and input_data.cache_key:
            cached_result = self._get_cached(input_data.cache_key)
            if cached_result:
                logger.info("narrative_cache_hit", cache_key=input_data.cache_key)
                return cached_result

        # Track token usage for this generation
        usage_tracker = TokenUsageTracker()

        # Generate all sections
        executive_summary = await self._generate_executive_summary(
            input_data, usage_tracker
        )
        methodology = await self._generate_methodology(
            input_data, usage_tracker
        )
        recommendations = await self._generate_recommendations(
            input_data, usage_tracker
        )

        # Calculate generation time
        end_time = datetime.utcnow()
        generation_time = (end_time - start_time).total_seconds()

        # Count words
        word_count = {
            "executive_summary": len(executive_summary.split()),
            "methodology": len(methodology.split()),
            "recommendations": len(recommendations.split()),
        }

        # Create output
        output = NarrativeOutput(
            executive_summary=executive_summary,
            methodology=methodology,
            recommendations=recommendations,
            tokens_used=usage_tracker.total_tokens,
            cost_euros=usage_tracker.cost_euros,
            generation_time_seconds=generation_time,
            word_count=word_count,
            model_used=self.model,
            input_hash=input_hash,
        )

        # Update daily usage
        self._daily_usage.update(usage_tracker.input_tokens, usage_tracker.output_tokens)

        # Cache result if enabled
        if self.cache_enabled and input_data.cache_key:
            self._cache[input_data.cache_key] = output

        logger.info(
            "narrative_generated",
            tokens_used=usage_tracker.total_tokens,
            cost_euros=float(usage_tracker.cost_euros),
            generation_time=generation_time,
            word_count=word_count,
        )

        return output

    def generate_sync(self, input_data: NarrativeInput) -> NarrativeOutput:
        """
        Synchronous wrapper for generate().

        Useful for non-async contexts.
        """
        return asyncio.run(self.generate(input_data))

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(Exception)
    )
    async def _generate_executive_summary(
        self,
        input_data: NarrativeInput,
        usage_tracker: TokenUsageTracker
    ) -> str:
        """Generate executive summary section (500 words)."""

        prompt = self._build_executive_summary_prompt(input_data)

        try:
            message = await self.async_client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )

            # Extract text
            text = self._extract_text_from_message(message)

            # Update usage
            usage_tracker.update(message.usage.input_tokens, message.usage.output_tokens)

            logger.debug(
                "section_generated",
                section="executive_summary",
                input_tokens=message.usage.input_tokens,
                output_tokens=message.usage.output_tokens
            )

            return text

        except Exception as e:
            logger.error(
                "executive_summary_generation_failed",
                error=str(e),
                exc_info=True
            )
            raise

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(Exception)
    )
    async def _generate_methodology(
        self,
        input_data: NarrativeInput,
        usage_tracker: TokenUsageTracker
    ) -> str:
        """Generate methodology section (300 words)."""

        prompt = self._build_methodology_prompt(input_data)

        try:
            message = await self.async_client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )

            text = self._extract_text_from_message(message)
            usage_tracker.update(message.usage.input_tokens, message.usage.output_tokens)

            logger.debug(
                "section_generated",
                section="methodology",
                input_tokens=message.usage.input_tokens,
                output_tokens=message.usage.output_tokens
            )

            return text

        except Exception as e:
            logger.error("methodology_generation_failed", error=str(e), exc_info=True)
            raise

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(Exception)
    )
    async def _generate_recommendations(
        self,
        input_data: NarrativeInput,
        usage_tracker: TokenUsageTracker
    ) -> str:
        """Generate recommendations section (200 words)."""

        prompt = self._build_recommendations_prompt(input_data)

        try:
            message = await self.async_client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )

            text = self._extract_text_from_message(message)
            usage_tracker.update(message.usage.input_tokens, message.usage.output_tokens)

            logger.debug(
                "section_generated",
                section="recommendations",
                input_tokens=message.usage.input_tokens,
                output_tokens=message.usage.output_tokens
            )

            return text

        except Exception as e:
            logger.error("recommendations_generation_failed", error=str(e), exc_info=True)
            raise

    def _build_executive_summary_prompt(self, input_data: NarrativeInput) -> str:
        """Build prompt for executive summary generation."""

        fc = input_data.financial_context
        cc = input_data.compliance_context

        compliance_status = "CONFORME" if cc.is_compliant else "NÃO CONFORME"

        prompt = f"""Você é um consultor especializado em candidaturas ao Portugal 2030.

Gere um Sumário Executivo profissional para um Estudo de Viabilidade Económica e Financeira (EVF).

## DADOS DO PROJETO
- Nome: {fc.project_name}
- Tipo de Fundo: {fc.fund_type}
- Duração: {fc.project_duration_years} anos
- Investimento Total: {fc.total_investment:,.2f} EUR
- Investimento Elegível: {fc.eligible_investment:,.2f} EUR
- Financiamento Solicitado: {fc.funding_requested:,.2f} EUR

## RESULTADOS FINANCEIROS (CALCULADOS)
- VALF (Valor Atual Líquido Financeiro): {fc.valf:,.2f} EUR
- TRF (Taxa de Rentabilidade Financeira): {fc.trf:.2f}%
- Período de Retorno: {fc.payback_period or 'N/A'} anos
- Conformidade PT2030: {compliance_status}

## NOTAS DE CONFORMIDADE
{chr(10).join(f"- {note}" for note in fc.compliance_notes)}

## INSTRUÇÕES
Escreva um Sumário Executivo em Português de Portugal (pt-PT) com aproximadamente 500 palavras que:

1. Apresente o projeto e seus objetivos estratégicos
2. Destaque o enquadramento no Portugal 2030
3. Resuma os principais indicadores financeiros (VALF, TRF, período de retorno)
4. Explique a necessidade de financiamento público (baseado no VALF negativo)
5. Destaque o impacto económico e social esperado
6. Conclua com a viabilidade do projeto

IMPORTANTE:
- Use linguagem profissional mas acessível
- Não invente números - use apenas os fornecidos
- Foque no "porquê" o projeto merece financiamento
- Mantenha tom objetivo e baseado em factos
- Evite jargão técnico excessivo

Escreva apenas o texto do Sumário Executivo, sem títulos ou formatação adicional."""

        return prompt

    def _build_methodology_prompt(self, input_data: NarrativeInput) -> str:
        """Build prompt for methodology section."""

        fc = input_data.financial_context

        assumptions_text = "\n".join(
            f"- {key}: {value}" for key, value in fc.assumptions.items()
        )

        prompt = f"""Você é um consultor especializado em estudos de viabilidade económica.

Gere a secção "Metodologia e Pressupostos" para um EVF de candidatura ao Portugal 2030.

## CONTEXTO DO PROJETO
- Nome: {fc.project_name}
- Duração: {fc.project_duration_years} anos
- Investimento Total: {fc.total_investment:,.2f} EUR

## PRESSUPOSTOS UTILIZADOS
{assumptions_text}

## DADOS TÉCNICOS
- Taxa de Desconto: 4% (critério Portugal 2030)
- Método de Cálculo: NPV e IRR determinísticos
- Horizonte Temporal: {fc.project_duration_years} anos

## INSTRUÇÕES
Escreva a secção "Metodologia e Pressupostos" em Português de Portugal (pt-PT) com aproximadamente 300 palavras que:

1. Explique a metodologia de cálculo do VALF e TRF
2. Justifique os principais pressupostos utilizados
3. Descreva as fontes de dados (SAF-T, projeções, mercado)
4. Explique a conformidade com critérios Portugal 2030
5. Destaque o rigor técnico e auditabilidade dos cálculos

IMPORTANTE:
- Use linguagem técnica mas clara
- Explique metodologia sem entrar em fórmulas complexas
- Justifique pressupostos com base em dados reais
- Demonstre conformidade com normativos

Escreva apenas o texto da secção, sem títulos ou formatação adicional."""

        return prompt

    def _build_recommendations_prompt(self, input_data: NarrativeInput) -> str:
        """Build prompt for recommendations section."""

        fc = input_data.financial_context
        cc = input_data.compliance_context

        if cc.is_compliant:
            context = "O projeto CUMPRE os critérios de elegibilidade financeira do Portugal 2030."
        else:
            context = "O projeto NÃO CUMPRE os critérios de elegibilidade financeira. Ajustes são necessários."
            context += f"\n\nSugestões: {json.dumps(cc.suggestions, indent=2)}"

        prompt = f"""Você é um consultor especializado em candidaturas ao Portugal 2030.

Gere a secção "Recomendações e Conclusões" para um EVF.

## CONTEXTO
{context}

## RESULTADOS FINANCEIROS
- VALF: {fc.valf:,.2f} EUR
- TRF: {fc.trf:.2f}%
- Conformidade: {'SIM' if cc.is_compliant else 'NÃO'}

## INSTRUÇÕES
Escreva a secção "Recomendações e Conclusões" em Português de Portugal (pt-PT) com aproximadamente 200 palavras que:

1. Apresente conclusões sobre a viabilidade financeira
2. Forneça recomendações específicas para o promotor
3. Se conforme: destaque pontos fortes e próximos passos
4. Se não conforme: sugira ajustes concretos para alcançar conformidade
5. Conclua com perspetiva global sobre o projeto

IMPORTANTE:
- Seja específico e acionável nas recomendações
- Base conclusões nos números apresentados
- Mantenha tom profissional e construtivo
- Forneça próximos passos claros

Escreva apenas o texto da secção, sem títulos ou formatação adicional."""

        return prompt

    def _extract_text_from_message(self, message: Message) -> str:
        """Extract text content from Claude API response."""

        for block in message.content:
            if isinstance(block, TextBlock):
                return block.text

        return ""

    def _hash_input(self, input_data: NarrativeInput) -> str:
        """Calculate SHA-256 hash of input data for audit trail."""

        input_json = input_data.model_dump_json(indent=None)
        hash_obj = hashlib.sha256(input_json.encode('utf-8'))
        return hash_obj.hexdigest()

    def _check_cost_limits(self):
        """Check if daily cost limits are exceeded."""

        if self._daily_usage.cost_euros >= Decimal(str(self.cost_limit_daily_euros)):
            raise ValueError(
                f"Daily cost limit exceeded: {self._daily_usage.cost_euros} EUR / "
                f"{self.cost_limit_daily_euros} EUR"
            )

    def _get_cached(self, cache_key: str) -> Optional[NarrativeOutput]:
        """Get cached narrative if available."""
        return self._cache.get(cache_key)

    def get_usage_stats(self) -> Dict:
        """Get current usage statistics."""
        return {
            "daily_tokens": self._daily_usage.total_tokens,
            "daily_cost_euros": float(self._daily_usage.cost_euros),
            "cache_size": len(self._cache),
            "cost_limit_euros": self.cost_limit_daily_euros,
            "usage_percentage": float(
                (self._daily_usage.cost_euros / Decimal(str(self.cost_limit_daily_euros))) * 100
            ),
        }

    def reset_daily_usage(self):
        """Reset daily usage counters (call at midnight UTC)."""
        self._daily_usage = TokenUsageTracker()
        logger.info("daily_usage_reset")

    def clear_cache(self):
        """Clear narrative cache."""
        cache_size = len(self._cache)
        self._cache.clear()
        logger.info("cache_cleared", entries_removed=cache_size)
