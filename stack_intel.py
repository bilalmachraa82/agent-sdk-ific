"""
Stack Intelligence Agent
Detects tech stack redundancies and recommends integrated solutions
CRITICAL: Prevents suggesting Monday.com to PHC users, etc.
"""

from typing import Any
from anthropic import Anthropic
from loguru import logger

from core.config import settings
from core.schemas import CompanySize


class StackIntelligenceAgent:
    """
    Analyzes existing tech stack and prevents redundant tool recommendations
    
    Key Principles:
    1. Build on existing systems, don't replace
    2. Portuguese ERP systems (PHC, Primavera) have broad functionality
    3. Microsoft 365 includes Teams/Planner/Loop - don't suggest Slack/Notion
    4. Focus on AI augmentation, not wholesale replacement
    """

    # Redundancy rules: If company has X, don't suggest Y
    REDUNDANCY_RULES = {
        "PHC": {
            "blocked": ["Monday.com", "HubSpot CRM", "Salesforce", "NetSuite", "Odoo"],
            "reason": "PHC (Cegid) é ERP completo com CRM integrado",
            "alternatives": ["Power BI integração PHC", "Azure ML para forecasting", "PHC Analytics+"],
        },
        "Primavera": {
            "blocked": ["SAP", "NetSuite", "Odoo"],
            "reason": "Primavera é ERP português com módulos extensivos",
            "alternatives": ["Power BI", "Qlik Sense", "Tableau"],
        },
        "SAP": {
            "blocked": ["NetSuite", "Odoo", "PHC"],
            "reason": "SAP é enterprise ERP - manter e expandir",
            "alternatives": ["SAP Analytics Cloud", "SAP AI Business Services"],
        },
        "Microsoft 365": {
            "blocked": ["Slack", "Notion", "Trello", "Asana"],
            "reason": "M365 tem Teams, Loop, Planner, OneNote",
            "alternatives": ["Microsoft Copilot", "Power Automate", "Power Apps"],
        },
        "Google Workspace": {
            "blocked": ["Microsoft 365", "Slack"],
            "reason": "Google Workspace é suite completa",
            "alternatives": ["Gemini for Workspace", "AppSheet", "Looker"],
        },
        "Salesforce": {
            "blocked": ["HubSpot CRM", "Pipedrive", "Zoho CRM"],
            "reason": "Salesforce é CRM enterprise - expandir com Einstein AI",
            "alternatives": ["Einstein Analytics", "Tableau CRM", "MuleSoft"],
        },
        "HubSpot": {
            "blocked": ["Salesforce", "Pipedrive", "ActiveCampaign"],
            "reason": "HubSpot é marketing+CRM completo",
            "alternatives": ["HubSpot AI", "ChatSpot", "Content Assistant"],
        },
    }

    # Industry-specific recommendations by CAE
    INDUSTRY_TEMPLATES = {
        "70220": {  # Consultoria gestão
            "name": "Consultoria",
            "must_have": ["CRM", "Project Management", "Time Tracking"],
            "nice_to_have": ["Proposal Automation", "Client Portal", "BI Analytics"],
            "typical_stack": ["PHC", "Microsoft 365", "Notion/Monday.com"],
        },
        "62010": {  # Programação informática
            "name": "Software Development",
            "must_have": ["Version Control", "CI/CD", "Project Management"],
            "nice_to_have": ["Code Analysis", "Cloud Platform", "Monitoring"],
            "typical_stack": ["GitHub", "Jira", "AWS/Azure"],
        },
        "47": {  # Comércio retalhista
            "name": "Retail",
            "must_have": ["ERP", "POS", "Inventory Management"],
            "nice_to_have": ["E-commerce", "CRM", "Analytics"],
            "typical_stack": ["PHC", "Shopify", "Google Analytics"],
        },
        "56": {  # Restauração
            "name": "Hospitality",
            "must_have": ["POS", "Reservations", "Inventory"],
            "nice_to_have": ["Delivery Integration", "Analytics", "Marketing"],
            "typical_stack": ["Zomato/Uber Eats", "PHC", "Google/Meta Ads"],
        },
    }

    def __init__(self, client: Anthropic):
        self.client = client

    async def analyze_stack(
        self,
        existing_stack: list[str],
        industry_cae: str,
        company_size: CompanySize,
    ) -> dict[str, Any]:
        """
        Analyze existing tech stack and generate intelligent recommendations
        
        Args:
            existing_stack: List of currently used tools/platforms
            industry_cae: CAE code for industry-specific recommendations
            company_size: Micro/Pequena/Media for budget-appropriate tools
            
        Returns:
            Dict with:
            - redundancias_detectadas: List of conflicts
            - recomendacoes: List of AI tools that complement existing stack
            - gaps: Missing critical functionality
            - integration_opportunities: Ways to connect systems
        """
        logger.info(f"Analyzing stack | tools={len(existing_stack)} | cae={industry_cae}")
        
        # Detect redundancies
        redundancias = []
        blocked_tools = set()
        
        for tool in existing_stack:
            if tool in self.REDUNDANCY_RULES:
                rule = self.REDUNDANCY_RULES[tool]
                blocked_tools.update(rule["blocked"])
                logger.info(f"Tool {tool} blocks: {rule['blocked']}")
        
        # Get industry template
        cae_prefix = industry_cae[:2] if len(industry_cae) >= 2 else "99"
        industry = self.INDUSTRY_TEMPLATES.get(
            industry_cae,
            self.INDUSTRY_TEMPLATES.get(cae_prefix, None)
        )
        
        if not industry:
            industry = {
                "name": "Generic",
                "must_have": ["CRM", "Analytics"],
                "nice_to_have": ["Automation", "BI"],
                "typical_stack": [],
            }
        
        # Identify gaps
        gaps = []
        for must_have in industry["must_have"]:
            if not self._has_capability(existing_stack, must_have):
                gaps.append(must_have)
        
        # Generate AI-specific recommendations (not blocked)
        recomendacoes = await self._generate_ai_recommendations(
            existing_stack=existing_stack,
            blocked_tools=blocked_tools,
            industry=industry,
            company_size=company_size,
            gaps=gaps,
        )
        
        # Identify integration opportunities
        integrations = self._identify_integrations(existing_stack)
        
        return {
            "redundancias_detectadas": redundancias,
            "tools_blocked": list(blocked_tools),
            "recomendacoes": recomendacoes,
            "gaps": gaps,
            "integration_opportunities": integrations,
            "industry_context": industry["name"],
        }

    def _has_capability(self, stack: list[str], capability: str) -> bool:
        """Check if existing stack covers a capability"""
        capability_map = {
            "CRM": ["Salesforce", "HubSpot", "PHC", "Pipedrive", "Zoho"],
            "ERP": ["PHC", "SAP", "Primavera", "NetSuite", "Odoo"],
            "Project Management": ["Monday.com", "Asana", "Jira", "Trello", "Microsoft 365"],
            "Analytics": ["Power BI", "Tableau", "Looker", "Google Analytics"],
            "E-commerce": ["Shopify", "WooCommerce", "Magento", "PrestaShop"],
        }
        
        matching_tools = capability_map.get(capability, [])
        return any(tool in stack for tool in matching_tools)

    async def _generate_ai_recommendations(
        self,
        existing_stack: list[str],
        blocked_tools: set[str],
        industry: dict[str, Any],
        company_size: CompanySize,
        gaps: list[str],
    ) -> list[dict[str, Any]]:
        """
        Generate AI tool recommendations using Claude
        
        Returns list of dicts with:
        - tool_name
        - category
        - justificacao
        - integracao_com (which existing tool it connects to)
        - custo_mensal_aprox
        - roi_esperado
        """
        
        # Build context for Claude
        prompt = f"""Gera recomendações de ferramentas IA para empresa portuguesa no setor {industry['name']} (CAE {industry}).

Stack Tecnológico Existente:
{', '.join(existing_stack) if existing_stack else 'Nenhum identificado'}

Ferramentas BLOQUEADAS (redundantes):
{', '.join(blocked_tools) if blocked_tools else 'Nenhuma'}

Gaps Identificados:
{', '.join(gaps) if gaps else 'Nenhum'}

Dimensão: {company_size.value}

INSTRUÇÕES:
1. Sugere APENAS ferramentas IA que:
   - Complementam o stack existente (não substituem)
   - NÃO estão na lista bloqueada
   - Têm integração com sistemas existentes
   - São adequadas ao orçamento ({company_size.value})

2. Prioriza:
   - Soluções cloud (RGPD compliant)
   - Pricing transparente
   - Suporte PT/PT ou EN
   - ROI demonstrável

3. Para CADA ferramenta, especifica:
   - Nome da ferramenta
   - Categoria (ex: "CRM Intelligence", "Forecasting", "Automation")
   - Justificação (2-3 frases)
   - Integração com (tool existente)
   - Custo mensal aproximado (€)
   - ROI esperado (%)

Responde em formato JSON array com 3-7 recomendações."""

        try:
            response = self.client.messages.create(
                model=settings.claude_model,
                max_tokens=4000,
                temperature=0.3,
                messages=[{"role": "user", "content": prompt}]
            )
            
            # Parse response (simplified - in production, use structured outputs)
            content = response.content[0].text
            
            # For now, return placeholder recommendations
            # In production, parse JSON from Claude response
            return self._get_safe_recommendations(existing_stack, company_size)
            
        except Exception as e:
            logger.error(f"AI recommendation generation failed | error={str(e)}")
            return self._get_safe_recommendations(existing_stack, company_size)

    def _get_safe_recommendations(
        self,
        existing_stack: list[str],
        company_size: CompanySize,
    ) -> list[dict[str, Any]]:
        """Fallback recommendations if AI generation fails"""
        
        base_recommendations = [
            {
                "tool_name": "Microsoft Copilot for M365",
                "category": "Productivity AI",
                "justificacao": "Integração nativa com Microsoft 365 para automação de emails, documentos e resumos de reuniões",
                "integracao_com": "Microsoft 365",
                "custo_mensal_aprox": 25 * 10,  # €25/user, assume 10 users
                "roi_esperado": 35,
                "elegivel_ific": True,
            },
            {
                "tool_name": "Power BI",
                "category": "Business Intelligence",
                "justificacao": "Análise de dados e dashboards com integração direta a ERP português (PHC/Primavera)",
                "integracao_com": "PHC" if "PHC" in existing_stack else "ERP",
                "custo_mensal_aprox": 20 * 5,  # €20/user Pro, assume 5 users
                "roi_esperado": 40,
                "elegivel_ific": True,
            },
            {
                "tool_name": "Azure OpenAI Service",
                "category": "Custom AI Development",
                "justificacao": "Desenvolvimento de soluções IA personalizadas com GPT-4, RGPD compliant em data centers EU",
                "integracao_com": "APIs internas",
                "custo_mensal_aprox": 500,  # Variable, estimate for small usage
                "roi_esperado": 45,
                "elegivel_ific": True,
            },
        ]
        
        # Filter by company size budget
        if company_size == CompanySize.MICRO:
            return base_recommendations[:2]  # Just essential tools
        elif company_size == CompanySize.PEQUENA:
            return base_recommendations
        else:  # MEDIA
            return base_recommendations + [
                {
                    "tool_name": "Salesforce Einstein" if "Salesforce" in existing_stack else "HubSpot AI",
                    "category": "CRM Intelligence",
                    "justificacao": "Previsão de vendas, lead scoring automático e recomendações contextuais",
                    "integracao_com": "Salesforce" if "Salesforce" in existing_stack else "CRM",
                    "custo_mensal_aprox": 150,
                    "roi_esperado": 38,
                    "elegivel_ific": True,
                }
            ]

    def _identify_integrations(self, stack: list[str]) -> list[dict[str, str]]:
        """Identify potential integration opportunities between existing tools"""
        
        integrations = []
        
        # Common integration patterns
        if "PHC" in stack and "Power BI" not in stack:
            integrations.append({
                "from": "PHC",
                "to": "Power BI",
                "benefit": "Dashboards financeiros automáticos com dados em tempo real",
                "complexity": "Média",
            })
        
        if "Microsoft 365" in stack:
            integrations.append({
                "from": "Microsoft 365",
                "to": "Power Automate",
                "benefit": "Automação de workflows entre apps M365",
                "complexity": "Baixa",
            })
        
        if any(crm in stack for crm in ["Salesforce", "HubSpot"]):
            crm = next(c for c in ["Salesforce", "HubSpot"] if c in stack)
            integrations.append({
                "from": crm,
                "to": "Power BI / Tableau",
                "benefit": "Analytics de vendas e pipeline visual",
                "complexity": "Média",
            })
        
        return integrations
