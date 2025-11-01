"""
Company Research Agent
Fetches company data from eInforma, Racius, and public sources
"""

from datetime import datetime
from typing import Any
from anthropic import Anthropic
from loguru import logger
import httpx
from bs4 import BeautifulSoup

from core.config import settings
from core.schemas import CompanyData, CompanySize, NUTSII


class CompanyResearchAgent:
    """
    Automated company research using multiple sources
    Priority: eInforma (API) → Racius (scraping) → Website (playwright)
    """

    def __init__(self, client: Anthropic):
        self.client = client
        self.httpx_client = httpx.AsyncClient(timeout=30.0)

    async def fetch_company_data(
        self,
        nome: str,
        nif: str | None = None,
        url: str | None = None,
        cae: str | None = None,
    ) -> CompanyData:
        """
        Fetch complete company data from all available sources
        
        Args:
            nome: Company name
            nif: Portuguese tax ID (9 digits)
            url: Company website URL
            cae: Economic activity code (5 digits)
            
        Returns:
            CompanyData with all gathered information
        """
        logger.info(f"Researching company | nome={nome} | nif={nif}")
        
        data_sources = {}
        company_info: dict[str, Any] = {
            "nome": nome,
            "nif": nif or "",
            "cae": cae or "",
            "tech_stack": [],
            "data_sources": {},
        }

        # ================================================================
        # SOURCE 1: eInforma (preferred)
        # ================================================================
        if settings.einforma_api_key and nif:
            try:
                einforma_data = await self._fetch_einforma(nif)
                if einforma_data:
                    company_info.update(einforma_data)
                    data_sources["einforma"] = f"API call on {datetime.utcnow().date()}"
                    logger.info("eInforma data fetched successfully")
            except Exception as e:
                logger.warning(f"eInforma fetch failed | error={str(e)}")

        # ================================================================
        # SOURCE 2: Racius (cross-check)
        # ================================================================
        if not company_info.get("volume_negocios") or not company_info.get("nif"):
            try:
                racius_data = await self._fetch_racius(nome, nif)
                if racius_data:
                    # Merge data, preferring existing values
                    for key, value in racius_data.items():
                        if key not in company_info or not company_info[key]:
                            company_info[key] = value
                    data_sources["racius"] = f"Scraped on {datetime.utcnow().date()}"
                    logger.info("Racius data fetched successfully")
            except Exception as e:
                logger.warning(f"Racius fetch failed | error={str(e)}")

        # ================================================================
        # SOURCE 3: Website (tech stack detection)
        # ================================================================
        if url:
            try:
                website_data = await self._analyze_website(url)
                company_info["tech_stack"] = website_data.get("tech_stack", [])
                company_info["erp_sistema"] = website_data.get("erp", None)
                company_info["crm_sistema"] = website_data.get("crm", None)
                data_sources["website"] = url
                logger.info(f"Website analyzed | stack_size={len(company_info['tech_stack'])}")
            except Exception as e:
                logger.warning(f"Website analysis failed | error={str(e)}")

        # ================================================================
        # DATA ENRICHMENT & DEFAULTS
        # ================================================================
        
        # Infer NUTS II from location (simplified)
        nuts_map = {
            "lisboa": NUTSII.PT17,
            "porto": NUTSII.PT11,
            "coimbra": NUTSII.PT16,
            "faro": NUTSII.PT15,
            "évora": NUTSII.PT18,
            "beja": NUTSII.PT18,
        }
        
        morada = company_info.get("morada_completa", "").lower()
        company_info["nuts_ii"] = next(
            (nuts for city, nuts in nuts_map.items() if city in morada),
            NUTSII.PT17  # Default to Lisboa if unknown
        )
        
        # Infer company size from headcount/revenue
        headcount = company_info.get("headcount", 0)
        revenue = company_info.get("volume_negocios", 0)
        
        if headcount < 10 and revenue < 2_000_000:
            dimensao = CompanySize.MICRO
        elif headcount < 50 and revenue < 10_000_000:
            dimensao = CompanySize.PEQUENA
        else:
            dimensao = CompanySize.MEDIA
        
        company_info["dimensao"] = dimensao
        company_info["data_sources"] = data_sources
        
        # Build final CompanyData object
        return CompanyData(**company_info)

    async def _fetch_einforma(self, nif: str) -> dict[str, Any]:
        """
        Fetch data from eInforma API
        
        Note: This is a placeholder. Actual implementation depends on eInforma API structure.
        Current approach: use their free report if available, or API with key
        """
        if not settings.einforma_api_key:
            logger.debug("eInforma API key not configured, skipping")
            return {}
        
        # Placeholder for eInforma API integration
        # In production, this would call their actual API endpoint
        url = f"https://www.einforma.pt/api/v1/companies/{nif}"
        headers = {"Authorization": f"Bearer {settings.einforma_api_key}"}
        
        try:
            response = await self.httpx_client.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()
            
            return {
                "denominacao_legal": data.get("legal_name"),
                "nif": data.get("nif"),
                "cae": data.get("cae"),
                "morada_completa": data.get("address"),
                "capital_social": data.get("share_capital"),
                "volume_negocios": data.get("revenue"),
                "resultado_liquido": data.get("net_income"),
                "ano_fiscal": data.get("fiscal_year"),
                "headcount": data.get("employees"),
            }
        except httpx.HTTPError as e:
            logger.error(f"eInforma API error | status={e.response.status_code if e.response else 'N/A'}")
            return {}

    async def _fetch_racius(self, nome: str, nif: str | None) -> dict[str, Any]:
        """
        Fetch data from Racius via web scraping (respecting robots.txt)
        
        Note: Actual implementation should check robots.txt and rate limit properly
        """
        search_term = nif if nif else nome.replace(" ", "+")
        url = f"https://www.racius.com/pesquisa?q={search_term}"
        
        try:
            response = await self.httpx_client.get(
                url,
                headers={"User-Agent": "FundAI/0.1 (Research Bot)"}
            )
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, "lxml")
            
            # Parse company page (simplified example)
            data = {}
            
            # Extract NIF if not provided
            nif_elem = soup.find("span", {"class": "nif"})
            if nif_elem and not nif:
                data["nif"] = nif_elem.text.strip()
            
            # Extract CAE
            cae_elem = soup.find("span", {"class": "cae"})
            if cae_elem:
                data["cae"] = cae_elem.text.strip()[:5]
            
            # Extract financial data
            revenue_elem = soup.find("div", {"data-field": "revenue"})
            if revenue_elem:
                # Parse value like "€ 1.234.567"
                revenue_str = revenue_elem.text.strip().replace("€", "").replace(".", "").strip()
                try:
                    data["volume_negocios"] = float(revenue_str)
                except ValueError:
                    pass
            
            return data
            
        except Exception as e:
            logger.error(f"Racius scraping error | error={str(e)}")
            return {}

    async def _analyze_website(self, url: str) -> dict[str, Any]:
        """
        Analyze company website to detect tech stack
        Uses simple heuristics + header analysis
        
        For production, consider using:
        - Wappalyzer API
        - BuiltWith API
        - Playwright for JS-heavy sites
        """
        try:
            response = await self.httpx_client.get(url)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, "lxml")
            html = response.text.lower()
            
            tech_stack = []
            
            # Detect common technologies
            if "wordpress" in html or "wp-content" in html:
                tech_stack.append("WordPress")
            
            if "shopify" in html or "cdn.shopify.com" in html:
                tech_stack.append("Shopify")
            
            if "wix.com" in html:
                tech_stack.append("Wix")
            
            # Check for analytics
            if "google-analytics" in html or "gtag" in html:
                tech_stack.append("Google Analytics")
            
            # Check for CRM/Marketing tools
            if "hubspot" in html:
                tech_stack.append("HubSpot")
            
            if "salesforce" in html:
                tech_stack.append("Salesforce")
            
            # Check meta tags for more info
            generator = soup.find("meta", {"name": "generator"})
            if generator:
                tech_stack.append(generator.get("content", "Unknown"))
            
            # Detect ERP systems (harder, usually requires login)
            erp = None
            if "phc" in html or "phcsoftware" in html:
                erp = "PHC"
            elif "sap" in html:
                erp = "SAP"
            elif "primavera" in html:
                erp = "Primavera"
            
            return {
                "tech_stack": list(set(tech_stack)),
                "erp": erp,
                "crm": "HubSpot" if "HubSpot" in tech_stack else (
                    "Salesforce" if "Salesforce" in tech_stack else None
                ),
            }
            
        except Exception as e:
            logger.error(f"Website analysis error | url={url} | error={str(e)}")
            return {"tech_stack": []}

    async def close(self):
        """Close HTTP client"""
        await self.httpx_client.aclose()
