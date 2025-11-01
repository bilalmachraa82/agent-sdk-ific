"""
FundAI REST API
FastAPI application for IFIC funding application processing
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from loguru import logger

from core.config import settings
from core.schemas import (
    CompanyInput,
    ProjectInput,
    BudgetInput,
    ImpactMetrics,
    FundingApplication,
    ApplicationStatus,
)
from agents.orchestrator import IFICOrchestrator


# Lifecycle management
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan - setup and teardown"""
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")
    logger.info(f"Environment: {settings.environment}")
    
    # Startup logic
    yield
    
    # Shutdown logic
    logger.info("Shutting down application")


# FastAPI app
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="AI-powered IFIC funding application system for Portuguese SMEs",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Dependency: Get orchestrator instance
def get_orchestrator() -> IFICOrchestrator:
    """Dependency to get orchestrator instance"""
    return IFICOrchestrator()


# ============================================================================
# HEALTH & STATUS ENDPOINTS
# ============================================================================

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "version": settings.app_version,
        "environment": settings.environment,
    }


@app.get("/api/v1/status")
async def api_status():
    """API status with feature flags"""
    return {
        "api_version": "v1",
        "features": {
            "company_research": settings.enable_company_research,
            "stack_intelligence": settings.enable_stack_intelligence,
            "financial_analysis": settings.enable_financial_analysis,
            "merit_scoring": settings.enable_merit_scoring,
            "compliance_validation": settings.enable_compliance_validation,
        },
        "limits": {
            "min_eligible": settings.ific_min_eligible,
            "max_incentive": settings.ific_max_incentive,
            "max_duration_months": settings.ific_max_duration_months,
        },
    }


# ============================================================================
# APPLICATION PROCESSING ENDPOINTS
# ============================================================================

class ApplicationRequest(BaseModel):
    """Complete application request"""
    company: CompanyInput
    project: ProjectInput
    budget: BudgetInput
    impact: ImpactMetrics
    user_id: str | None = None


@app.post(
    "/api/v1/applications",
    response_model=FundingApplication,
    status_code=201,
)
async def create_application(
    request: ApplicationRequest,
    background_tasks: BackgroundTasks,
    orchestrator: IFICOrchestrator = Depends(get_orchestrator),
):
    """
    Create and process a complete IFIC funding application
    
    This endpoint:
    1. Researches company data (eInforma → Racius → Website)
    2. Analyzes tech stack for redundancies
    3. Validates budget constraints
    4. Generates use cases and training plan
    5. Calculates merit score with scenarios
    6. Validates compliance (RGPD/DNSH)
    7. Generates proposal artifacts (HTML + CSVs)
    
    Returns complete FundingApplication with all artifacts and audit trail
    """
    try:
        logger.info(f"Processing application | company={request.company.nome}")
        
        application = await orchestrator.process_application(
            company_input=request.company,
            project_input=request.project,
            budget_input=request.budget,
            impact_metrics=request.impact,
            user_id=request.user_id,
        )
        
        return application
        
    except ValueError as e:
        logger.warning(f"Validation error | error={str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    
    except Exception as e:
        logger.error(f"Application processing failed | error={str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error during application processing"
        )


@app.get("/api/v1/applications/{application_id}")
async def get_application(application_id: str):
    """Retrieve application by ID (placeholder - requires database)"""
    # In production, retrieve from database
    raise HTTPException(status_code=501, detail="Database integration pending")


@app.get("/api/v1/applications/{application_id}/artifacts/{artifact_id}")
async def get_artifact(application_id: str, artifact_id: str):
    """Download specific artifact (placeholder - requires storage)"""
    # In production, retrieve from file storage
    raise HTTPException(status_code=501, detail="Storage integration pending")


# ============================================================================
# COMPANY RESEARCH ENDPOINTS (Standalone)
# ============================================================================

@app.post("/api/v1/research/company")
async def research_company(company_input: CompanyInput):
    """
    Standalone company research endpoint
    Useful for pre-filling application form
    """
    try:
        orchestrator = IFICOrchestrator()
        company_data = await orchestrator.researcher.fetch_company_data(
            nome=company_input.nome,
            nif=company_input.nif,
            url=str(company_input.url) if company_input.url else None,
            cae=company_input.cae,
        )
        return company_data
        
    except Exception as e:
        logger.error(f"Company research failed | error={str(e)}")
        raise HTTPException(status_code=500, detail="Research failed")


# ============================================================================
# STACK ANALYSIS ENDPOINTS (Standalone)
# ============================================================================

class StackAnalysisRequest(BaseModel):
    """Stack analysis request"""
    existing_stack: list[str]
    industry_cae: str
    company_size: str


@app.post("/api/v1/analysis/stack")
async def analyze_stack(request: StackAnalysisRequest):
    """
    Standalone stack intelligence analysis
    Returns redundancies and recommendations
    """
    try:
        orchestrator = IFICOrchestrator()
        analysis = await orchestrator.stack_intel.analyze_stack(
            existing_stack=request.existing_stack,
            industry_cae=request.industry_cae,
            company_size=request.company_size,
        )
        return analysis
        
    except Exception as e:
        logger.error(f"Stack analysis failed | error={str(e)}")
        raise HTTPException(status_code=500, detail="Analysis failed")


# ============================================================================
# SCORING SIMULATION ENDPOINTS
# ============================================================================

@app.post("/api/v1/scoring/simulate")
async def simulate_scoring(impact: ImpactMetrics):
    """
    Simulate merit score for different impact scenarios
    Useful for interactive calculator in proposals
    """
    try:
        orchestrator = IFICOrchestrator()
        
        # Base quality score (simplified)
        quality_indicators = {
            "financial_health": 4.0,
            "innovation_capacity": 3.8,
            "implementation_readiness": 4.2,
        }
        
        merit_score = await orchestrator.scorer.calculate_merit_score(
            project_quality_indicators=quality_indicators,
            impact_metrics=impact,
        )
        
        return merit_score
        
    except Exception as e:
        logger.error(f"Scoring simulation failed | error={str(e)}")
        raise HTTPException(status_code=500, detail="Simulation failed")


# ============================================================================
# ERROR HANDLERS
# ============================================================================

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Custom HTTP exception handler"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "status_code": exc.status_code,
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Catch-all exception handler"""
    logger.exception("Unhandled exception")
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": str(exc) if settings.debug else "An unexpected error occurred",
        },
    )


# ============================================================================
# STARTUP
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "api.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
    )
