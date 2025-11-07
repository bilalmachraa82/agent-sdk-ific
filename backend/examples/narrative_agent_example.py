"""
NarrativeAgent Usage Example
Demonstrates how to use NarrativeAgent to generate EVF narrative sections.
"""

import asyncio
from decimal import Decimal
from backend.agents.narrative_agent import (
    NarrativeAgent,
    NarrativeInput,
    FinancialContext,
    ComplianceContext,
)
from backend.core.config import settings


async def example_compliant_project():
    """Example: Generate narrative for a PT2030-compliant project."""

    print("=" * 80)
    print("EXAMPLE 1: PT2030-Compliant Project")
    print("=" * 80)

    # Initialize agent
    agent = NarrativeAgent(
        api_key=settings.claude_api_key,
        model=settings.claude_model,
        temperature=settings.claude_temperature,
        max_tokens=settings.claude_max_tokens,
        cost_limit_daily_euros=settings.claude_daily_limit_euros,
    )

    # Create financial context (from FinancialAgent output)
    financial_context = FinancialContext(
        project_name="Modernização da Linha de Produção ABC",
        project_duration_years=5,
        fund_type="PT2030",
        total_investment=Decimal("750000.00"),
        eligible_investment=Decimal("675000.00"),
        funding_requested=Decimal("337500.00"),  # 50% of eligible
        valf=Decimal("-75000.00"),  # Negative - compliant!
        trf=Decimal("3.2"),  # Below 4% - compliant!
        payback_period=Decimal("4.5"),
        roi=Decimal("18.5"),
        pt2030_compliant=True,
        compliance_notes=[
            "✅ VALF is negative (-75000.00 EUR) - meets PT2030 requirement.",
            "✅ TRF (3.20%) < discount rate (4.00%) - meets PT2030 requirement.",
            "✅ Project meets PT2030 financial eligibility criteria.",
        ],
        financial_ratios={
            "gross_margin": Decimal("38.5"),
            "operating_margin": Decimal("24.2"),
            "roi": Decimal("18.5"),
            "ebitda_coverage": Decimal("1.45"),
        },
        assumptions={
            "discount_rate": "4%",
            "project_duration": "5 years",
            "calculation_method": "Deterministic (numpy-financial)",
            "revenue_growth": "Conservative estimate based on market analysis",
        },
    )

    # Create compliance context (from ComplianceAgent output)
    compliance_context = ComplianceContext(
        status="compliant",
        is_compliant=True,
        errors=[],
        suggestions={},
    )

    # Create narrative input
    narrative_input = NarrativeInput(
        financial_context=financial_context,
        compliance_context=compliance_context,
        company_name="ABC Indústrias Lda",
        company_sector="Indústria Transformadora - Componentes Metálicos",
        project_description=(
            "Modernização da linha de produção com aquisição de novos equipamentos CNC "
            "e implementação de sistema de gestão integrado (ERP), visando aumentar "
            "capacidade produtiva em 40% e reduzir desperdícios em 25%."
        ),
        strategic_objectives=[
            "Aumentar eficiência produtiva em 40%",
            "Reduzir consumo energético em 30%",
            "Melhorar qualidade do produto (redução defeitos em 50%)",
            "Digitalização completa do processo produtivo",
        ],
        language="pt-PT",
        tone="professional",
        include_technical_details=True,
        cache_key="abc-modernization-2024",
    )

    # Generate narrative
    print("\n📝 Generating narrative sections...")
    result = await agent.generate(narrative_input)

    # Display results
    print("\n" + "=" * 80)
    print("SUMÁRIO EXECUTIVO")
    print("=" * 80)
    print(result.executive_summary)

    print("\n" + "=" * 80)
    print("METODOLOGIA E PRESSUPOSTOS")
    print("=" * 80)
    print(result.methodology)

    print("\n" + "=" * 80)
    print("RECOMENDAÇÕES E CONCLUSÕES")
    print("=" * 80)
    print(result.recommendations)

    print("\n" + "=" * 80)
    print("METADATA")
    print("=" * 80)
    print(f"Tokens Used: {result.tokens_used:,}")
    print(f"Cost: €{result.cost_euros:.4f}")
    print(f"Generation Time: {result.generation_time_seconds:.2f}s")
    print(f"Model: {result.model_used}")
    print(f"Word Count:")
    for section, count in result.word_count.items():
        print(f"  - {section}: {count} words")
    print(f"Cached: {result.cached}")

    # Show usage stats
    stats = agent.get_usage_stats()
    print("\n" + "=" * 80)
    print("AGENT USAGE STATISTICS")
    print("=" * 80)
    print(f"Daily Tokens: {stats['daily_tokens']:,}")
    print(f"Daily Cost: €{stats['daily_cost_euros']:.4f}")
    print(f"Cost Limit: €{stats['cost_limit_euros']:.2f}")
    print(f"Usage: {stats['usage_percentage']:.2f}%")
    print(f"Cache Size: {stats['cache_size']} entries")


async def example_non_compliant_project():
    """Example: Generate narrative for a non-compliant project."""

    print("\n\n" + "=" * 80)
    print("EXAMPLE 2: Non-Compliant Project (Needs Adjustments)")
    print("=" * 80)

    agent = NarrativeAgent(
        api_key=settings.claude_api_key,
        model=settings.claude_model,
        temperature=settings.claude_temperature,
    )

    # Create financial context with non-compliant metrics
    financial_context = FinancialContext(
        project_name="Expansão Comercial XYZ",
        project_duration_years=3,
        fund_type="PT2030",
        total_investment=Decimal("300000.00"),
        eligible_investment=Decimal("270000.00"),
        funding_requested=Decimal("135000.00"),
        valf=Decimal("25000.00"),  # POSITIVE - NOT compliant!
        trf=Decimal("6.5"),  # Above 4% - NOT compliant!
        payback_period=Decimal("2.8"),
        roi=Decimal("35.0"),
        pt2030_compliant=False,
        compliance_notes=[
            "⚠️ VALF is positive (25000.00 EUR). PT2030 requires VALF < 0.",
            "⚠️ TRF (6.50%) >= discount rate (4.00%). PT2030 requires TRF < discount rate.",
            "❌ Project does NOT meet PT2030 financial eligibility criteria.",
            "💡 Tip: Adjust revenue projections, costs, or funding amount to achieve compliance.",
        ],
    )

    compliance_context = ComplianceContext(
        status="non_compliant",
        is_compliant=False,
        errors=[
            "VALF positivo - projeto viável sem financiamento público",
            "TRF superior à taxa de desconto de referência",
        ],
        suggestions={
            "valf_adjustment": "Aumentar o montante de financiamento solicitado ou ajustar projeções de receita",
            "trf_adjustment": "Revisar estrutura de custos ou calendário de investimento",
            "alternative": "Considerar outros instrumentos de apoio não-reembolsável",
        },
    )

    narrative_input = NarrativeInput(
        financial_context=financial_context,
        compliance_context=compliance_context,
        company_name="XYZ Comércio Lda",
        company_sector="Comércio e Distribuição",
        project_description="Expansão da rede comercial com abertura de 3 novas lojas",
    )

    print("\n📝 Generating narrative for non-compliant project...")
    result = await agent.generate(narrative_input)

    print("\n" + "=" * 80)
    print("RECOMENDAÇÕES E CONCLUSÕES (Non-Compliant)")
    print("=" * 80)
    print(result.recommendations)

    print(f"\nCost: €{result.cost_euros:.4f} | Tokens: {result.tokens_used:,}")


async def example_sync_generation():
    """Example: Using synchronous wrapper."""

    print("\n\n" + "=" * 80)
    print("EXAMPLE 3: Synchronous Generation")
    print("=" * 80)

    agent = NarrativeAgent(
        api_key=settings.claude_api_key,
        model=settings.claude_model,
    )

    financial_context = FinancialContext(
        project_name="Inovação Tecnológica DEF",
        project_duration_years=4,
        fund_type="PT2030",
        total_investment=Decimal("450000.00"),
        eligible_investment=Decimal("400000.00"),
        funding_requested=Decimal("200000.00"),
        valf=Decimal("-30000.00"),
        trf=Decimal("3.8"),
        pt2030_compliant=True,
        compliance_notes=["✅ Project meets PT2030 requirements"],
    )

    compliance_context = ComplianceContext(
        status="compliant",
        is_compliant=True,
    )

    narrative_input = NarrativeInput(
        financial_context=financial_context,
        compliance_context=compliance_context,
    )

    print("\n📝 Generating narrative (synchronous)...")

    # Use sync wrapper
    result = agent.generate_sync(narrative_input)

    print(f"\n✅ Generated successfully!")
    print(f"Executive Summary length: {len(result.executive_summary)} chars")
    print(f"Total cost: €{result.cost_euros:.4f}")


async def example_cost_limit():
    """Example: Cost limit enforcement."""

    print("\n\n" + "=" * 80)
    print("EXAMPLE 4: Cost Limit Enforcement")
    print("=" * 80)

    # Create agent with very low cost limit
    agent = NarrativeAgent(
        api_key=settings.claude_api_key,
        cost_limit_daily_euros=0.01,  # Very low limit
    )

    # Simulate heavy usage
    agent._daily_usage.cost_euros = Decimal("0.02")

    financial_context = FinancialContext(
        project_name="Test Project",
        project_duration_years=5,
        total_investment=Decimal("100000.00"),
        eligible_investment=Decimal("90000.00"),
        funding_requested=Decimal("45000.00"),
        valf=Decimal("-10000.00"),
        trf=Decimal("3.5"),
        pt2030_compliant=True,
        compliance_notes=[],
    )

    compliance_context = ComplianceContext(
        status="compliant",
        is_compliant=True,
    )

    narrative_input = NarrativeInput(
        financial_context=financial_context,
        compliance_context=compliance_context,
    )

    try:
        result = await agent.generate(narrative_input)
        print("❌ Should have raised cost limit error!")
    except ValueError as e:
        print(f"✅ Cost limit enforced: {e}")


async def main():
    """Run all examples."""

    print("🚀 NarrativeAgent Examples\n")

    # Example 1: Compliant project
    await example_compliant_project()

    # Example 2: Non-compliant project
    await example_non_compliant_project()

    # Example 3: Sync generation
    await example_sync_generation()

    # Example 4: Cost limits
    await example_cost_limit()

    print("\n" + "=" * 80)
    print("✅ All examples completed!")
    print("=" * 80)


if __name__ == "__main__":
    # Ensure API key is configured
    if not settings.claude_api_key:
        print("❌ Error: CLAUDE_API_KEY not configured in .env")
        print("Please set CLAUDE_API_KEY in your .env file")
        exit(1)

    asyncio.run(main())
