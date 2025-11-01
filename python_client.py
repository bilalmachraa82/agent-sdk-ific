"""
FundAI Python Client Example
Simple client for interacting with FundAI API
"""

import httpx
from typing import Dict, Any


class FundAIClient:
    """Simple async client for FundAI API"""

    def __init__(self, base_url: str = "http://localhost:8000", api_key: str | None = None):
        self.base_url = base_url
        self.api_key = api_key
        self.client = httpx.AsyncClient(
            base_url=base_url,
            timeout=300.0,  # 5 minutes for full application processing
        )

    async def health_check(self) -> Dict[str, Any]:
        """Check API health status"""
        response = await self.client.get("/health")
        response.raise_for_status()
        return response.json()

    async def research_company(
        self,
        nome: str,
        nif: str | None = None,
        url: str | None = None,
        cae: str | None = None,
    ) -> Dict[str, Any]:
        """Research company data"""
        response = await self.client.post(
            "/api/v1/research/company",
            json={"nome": nome, "nif": nif, "url": url, "cae": cae},
        )
        response.raise_for_status()
        return response.json()

    async def analyze_stack(
        self,
        existing_stack: list[str],
        industry_cae: str,
        company_size: str,
    ) -> Dict[str, Any]:
        """Analyze tech stack for redundancies"""
        response = await self.client.post(
            "/api/v1/analysis/stack",
            json={
                "existing_stack": existing_stack,
                "industry_cae": industry_cae,
                "company_size": company_size,
            },
        )
        response.raise_for_status()
        return response.json()

    async def simulate_scoring(
        self,
        postos_trabalho: int,
        crescimento_vab: float,
    ) -> Dict[str, Any]:
        """Simulate merit score"""
        response = await self.client.post(
            "/api/v1/scoring/simulate",
            json={
                "postos_trabalho_liquidos": postos_trabalho,
                "crescimento_vab_percent": crescimento_vab,
                "exportacoes_aumento_percent": 0,
                "inovacao_score": 4.0,
            },
        )
        response.raise_for_status()
        return response.json()

    async def create_application(
        self,
        company: Dict[str, Any],
        project: Dict[str, Any],
        budget: Dict[str, Any],
        impact: Dict[str, Any],
        user_id: str | None = None,
    ) -> Dict[str, Any]:
        """Create complete IFIC funding application"""
        response = await self.client.post(
            "/api/v1/applications",
            json={
                "company": company,
                "project": project,
                "budget": budget,
                "impact": impact,
                "user_id": user_id,
            },
        )
        response.raise_for_status()
        return response.json()

    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()


# ============================================================================
# EXAMPLE USAGE
# ============================================================================

async def main():
    """Example usage of FundAI client"""
    client = FundAIClient()

    try:
        # 1. Health check
        print("1. Checking API health...")
        health = await client.health_check()
        print(f"   Status: {health['status']}")
        print()

        # 2. Research company
        print("2. Researching company...")
        company_data = await client.research_company(
            nome="TA Consulting",
            nif="123456789",
            url="https://taconsulting.pt",
            cae="70220",
        )
        print(f"   Found: {company_data['nome']}")
        print(f"   Stack: {company_data.get('tech_stack', [])}")
        print()

        # 3. Analyze stack
        print("3. Analyzing tech stack...")
        stack_analysis = await client.analyze_stack(
            existing_stack=["PHC", "Microsoft 365"],
            industry_cae="70220",
            company_size="pequena",
        )
        print(f"   Blocked tools: {stack_analysis['tools_blocked']}")
        print(f"   Gaps: {stack_analysis['gaps']}")
        print()

        # 4. Simulate scoring
        print("4. Simulating merit score...")
        score = await client.simulate_scoring(
            postos_trabalho=2,
            crescimento_vab=8.0,
        )
        print(f"   Merit Point: {score['merit_point_final']}")
        print(f"   Ranking: {score['ranking']}")
        print()

        # 5. Create full application
        print("5. Creating complete application...")
        application = await client.create_application(
            company={
                "nome": "TechStartup Lda",
                "url": "https://techstartup.pt",
                "nif": "987654321",
                "cae": "62010",
                "nuts_ii": "PT17",
                "certificacao_pme": True,
                "dimensao": "pequena",
            },
            project={
                "objetivos": "Deploy ML forecasting system",
                "processos_alvo": ["Sales", "Operations"],
                "dados_disponiveis": "3 years sales data",
                "inicio_previsto": "2026-01",
                "fim_previsto": "2027-12",
                "departamentos": ["Sales", "IT"],
            },
            budget={
                "teto_max_investimento": 180000,
                "cofinanciamento_disponivel": 45000,
                "preferencias": ["SaaS", "RH"],
            },
            impact={
                "postos_trabalho_liquidos": 2,
                "crescimento_vab_percent": 8.0,
                "exportacoes_aumento_percent": 5.0,
                "inovacao_score": 4.0,
            },
            user_id="demo_user",
        )
        print(f"   Application ID: {application['application_id']}")
        print(f"   Status: {application['status']}")
        print(f"   Merit Score: {application['merit_scoring']['merit_point_final']}")
        print(f"   Artifacts: {len(application['artifacts'])}")
        print()

        print("✅ All examples completed successfully!")

    finally:
        await client.close()


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
