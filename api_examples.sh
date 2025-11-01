# FundAI API Examples
# Quick reference for API endpoints

# Base URL (local development)
API_URL=http://localhost:8000

# ============================================================================
# HEALTH & STATUS
# ============================================================================

# Health check
curl ${API_URL}/health

# API status with feature flags
curl ${API_URL}/api/v1/status

# ============================================================================
# COMPANY RESEARCH (Standalone)
# ============================================================================

# Research Portuguese company
curl -X POST ${API_URL}/api/v1/research/company \
  -H "Content-Type: application/json" \
  -d '{
    "nome": "TA Consulting",
    "url": "https://taconsulting.pt",
    "nif": "123456789",
    "cae": "70220"
  }'

# ============================================================================
# STACK ANALYSIS (Standalone)
# ============================================================================

# Analyze tech stack for redundancies
curl -X POST ${API_URL}/api/v1/analysis/stack \
  -H "Content-Type: application/json" \
  -d '{
    "existing_stack": ["PHC", "Microsoft 365", "Google Analytics"],
    "industry_cae": "70220",
    "company_size": "pequena"
  }'

# ============================================================================
# MERIT SCORING SIMULATION
# ============================================================================

# Simulate merit score
curl -X POST ${API_URL}/api/v1/scoring/simulate \
  -H "Content-Type: application/json" \
  -d '{
    "postos_trabalho_liquidos": 2,
    "crescimento_vab_percent": 8.0,
    "exportacoes_aumento_percent": 5.0,
    "inovacao_score": 4.0
  }'

# ============================================================================
# COMPLETE APPLICATION PROCESSING
# ============================================================================

# Create full IFIC application
curl -X POST ${API_URL}/api/v1/applications \
  -H "Content-Type: application/json" \
  -d '{
    "company": {
      "nome": "TechStartup Lda",
      "url": "https://techstartup.pt",
      "nif": "123456789",
      "cae": "62010",
      "nuts_ii": "PT17",
      "certificacao_pme": true,
      "dimensao": "pequena"
    },
    "project": {
      "objetivos": "Deploy AI-powered sales forecasting system integrated with existing ERP to reduce stock costs by 20% and improve forecast accuracy to >85%",
      "processos_alvo": ["Sales", "Operations", "Inventory Management"],
      "dados_disponiveis": "3 years historical sales data in PHC, seasonal patterns, promotional calendar",
      "inicio_previsto": "2026-01",
      "fim_previsto": "2027-12",
      "departamentos": ["Sales", "IT", "Operations"]
    },
    "budget": {
      "teto_max_investimento": 180000,
      "cofinanciamento_disponivel": 45000,
      "preferencias": ["SaaS", "RH", "Consultoria", "Formacao"]
    },
    "impact": {
      "postos_trabalho_liquidos": 2,
      "crescimento_vab_percent": 8.0,
      "exportacoes_aumento_percent": 5.0,
      "inovacao_score": 4.0
    },
    "user_id": "user123"
  }'

# ============================================================================
# HTTPIE EXAMPLES (cleaner syntax)
# ============================================================================

# Install httpie: pip install httpie

# Health check
http GET ${API_URL}/health

# Company research
http POST ${API_URL}/api/v1/research/company \
  nome="TA Consulting" \
  url="https://taconsulting.pt" \
  nif="123456789" \
  cae="70220"

# Stack analysis
http POST ${API_URL}/api/v1/analysis/stack \
  existing_stack:='["PHC", "Microsoft 365"]' \
  industry_cae="70220" \
  company_size="pequena"

# Merit scoring
http POST ${API_URL}/api/v1/scoring/simulate \
  postos_trabalho_liquidos:=2 \
  crescimento_vab_percent:=8.0

# Complete application
http POST ${API_URL}/api/v1/applications < examples/sample_application.json

# ============================================================================
# PYTHON REQUESTS EXAMPLES
# ============================================================================

# See examples/python_client.py for complete Python client examples

# ============================================================================
# NOTES
# ============================================================================

# 1. Replace ${API_URL} with your actual API URL
# 2. For production, add authentication headers
# 3. Check response status codes:
#    - 200/201: Success
#    - 400: Validation error (check request body)
#    - 500: Server error (check logs)
# 4. Full API documentation: http://localhost:8000/docs (Swagger UI)
