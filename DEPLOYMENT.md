# FundAI Production Deployment Guide

Este guia cobre o deployment de FundAI em ambiente de produção.

## 📋 Pré-requisitos

- Servidor Linux (Ubuntu 22.04+ recomendado)
- Docker & Docker Compose
- PostgreSQL 16 (managed ou self-hosted)
- Redis 7
- Domain name com SSL certificate
- Anthropic API key

## 🔐 Security Checklist

Antes de deploy, garante que:

- [ ] `SECRET_KEY` é único e tem >32 caracteres
- [ ] `DEBUG=false` em produção
- [ ] Database passwords são fortes e únicos
- [ ] CORS origins estão limitados aos teus domains
- [ ] API rate limiting está ativo
- [ ] Logs não incluem dados sensíveis
- [ ] Backups automáticos configurados
- [ ] SSL/TLS configurado (Let's Encrypt)

## 🚀 Deployment Options

### Option 1: Docker Compose (Simples)

**Best for:** Small-medium deployments, single server

```bash
# 1. Clone repo no servidor
git clone https://github.com/aiparati/fundai.git
cd fundai

# 2. Configure produção
cp .env.example .env.production
nano .env.production
# Set:
#   ENVIRONMENT=production
#   DEBUG=false
#   SECRET_KEY=<generated-key>
#   ANTHROPIC_API_KEY=<your-key>
#   DATABASE_URL=<postgres-url>
#   REDIS_URL=<redis-url>

# 3. Build image
docker build -t fundai:production .

# 4. Deploy
docker-compose -f docker-compose.prod.yml up -d

# 5. Verify
curl https://yourdomain.com/health
```

### Option 2: Kubernetes (Escalável)

**Best for:** High availability, auto-scaling

```bash
# 1. Build & push image
docker build -t registry.aiparati.pt/fundai:v1.0 .
docker push registry.aiparati.pt/fundai:v1.0

# 2. Deploy to k8s
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/secrets.yaml
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml
kubectl apply -f k8s/ingress.yaml

# 3. Scale
kubectl scale deployment fundai-api --replicas=3
```

### Option 3: Cloud Platforms

**AWS ECS:**
```bash
# Use AWS Copilot
copilot init --app fundai --name api --type "Load Balanced Web Service"
copilot deploy
```

**Google Cloud Run:**
```bash
gcloud run deploy fundai \
  --image gcr.io/aiparati/fundai:latest \
  --platform managed \
  --region europe-west1
```

**Azure Container Apps:**
```bash
az containerapp create \
  --name fundai-api \
  --resource-group aiparati-rg \
  --image aiparati.azurecr.io/fundai:latest
```

## 🗄️ Database Setup

### PostgreSQL (Managed)

**Digital Ocean:**
```bash
# Create managed PostgreSQL cluster
doctl databases create fundai-db --engine pg --version 16 --region fra1

# Get connection string
doctl databases connection fundai-db

# Set in .env
DATABASE_URL=postgresql://user:pass@host:25060/fundai?sslmode=require
```

**AWS RDS:**
```bash
aws rds create-db-instance \
  --db-instance-identifier fundai-db \
  --engine postgres \
  --engine-version 16.0 \
  --db-instance-class db.t3.micro \
  --allocated-storage 20
```

### Redis (Managed)

**Redis Cloud:**
```bash
# Create via dashboard: https://redis.com/cloud
# Get connection string

REDIS_URL=redis://default:pass@endpoint:port
```

## 🔧 Configuration

### Environment Variables (Production)

```bash
# Application
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=WARNING

# API
API_HOST=0.0.0.0
API_PORT=8000
CORS_ORIGINS=["https://app.aiparati.pt","https://www.aiparati.pt"]

# Security
SECRET_KEY=<generate-with-openssl-rand-hex-32>
JWT_ALGORITHM=HS256

# Database (managed PostgreSQL)
DATABASE_URL=postgresql://user:pass@host:5432/fundai?sslmode=require

# Redis (managed)
REDIS_URL=redis://user:pass@host:6379/0

# Anthropic
ANTHROPIC_API_KEY=sk-ant-api03-...
CLAUDE_MODEL=claude-sonnet-4-20250514
CLAUDE_MAX_TOKENS=8000

# Data Sources (optional)
EINFORMA_API_KEY=your-key
RACIUS_API_KEY=your-key

# Monitoring
SENTRY_DSN=https://xxx@sentry.io/xxx
ENABLE_METRICS=true

# Storage (S3/GCS)
AWS_S3_BUCKET=fundai-artifacts
AWS_ACCESS_KEY_ID=xxx
AWS_SECRET_ACCESS_KEY=xxx
```

## 📊 Monitoring

### Logging (Loguru + Sentry)

```python
# core/config.py já configurado para Sentry
# Apenas adicionar SENTRY_DSN em .env

# Ver logs
docker-compose logs -f api
```

### Metrics (Prometheus)

```yaml
# docker-compose.prod.yml
prometheus:
  image: prom/prometheus
  volumes:
    - ./prometheus.yml:/etc/prometheus/prometheus.yml
  ports:
    - "9090:9090"

grafana:
  image: grafana/grafana
  ports:
    - "3000:3000"
```

### Health Checks

```bash
# Kubernetes liveness probe
livenessProbe:
  httpGet:
    path: /health
    port: 8000
  initialDelaySeconds: 30
  periodSeconds: 10

# External monitoring
curl -f https://api.aiparati.pt/health || alert
```

## 🔄 CI/CD Pipeline

### GitHub Actions

```yaml
# .github/workflows/deploy.yml
name: Deploy to Production

on:
  push:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - run: |
          pip install poetry
          poetry install
          poetry run pytest
  
  build:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: docker/build-push-action@v4
        with:
          push: true
          tags: registry.aiparati.pt/fundai:${{ github.sha }}
  
  deploy:
    needs: build
    runs-on: ubuntu-latest
    steps:
      - name: Deploy to production
        run: |
          kubectl set image deployment/fundai-api \
            api=registry.aiparati.pt/fundai:${{ github.sha }}
```

## 🔒 SSL/TLS Setup

### Let's Encrypt (Certbot)

```bash
# Install certbot
sudo apt install certbot python3-certbot-nginx

# Get certificate
sudo certbot --nginx -d api.aiparati.pt

# Auto-renewal (crontab)
0 0 * * * certbot renew --quiet
```

### Nginx Reverse Proxy

```nginx
# /etc/nginx/sites-available/fundai
server {
    listen 443 ssl http2;
    server_name api.aiparati.pt;

    ssl_certificate /etc/letsencrypt/live/api.aiparati.pt/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.aiparati.pt/privkey.pem;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## 📦 Backups

### PostgreSQL Backups

```bash
# Daily backup script
#!/bin/bash
pg_dump $DATABASE_URL | gzip > /backups/fundai-$(date +%Y%m%d).sql.gz

# Retention: keep 30 days
find /backups -name "fundai-*.sql.gz" -mtime +30 -delete

# S3 upload
aws s3 cp /backups/fundai-$(date +%Y%m%d).sql.gz s3://fundai-backups/
```

### Automated with cron

```cron
# /etc/cron.d/fundai-backup
0 2 * * * root /opt/fundai/backup.sh
```

## 🚨 Disaster Recovery

### Recovery Procedure

1. **Database Restore:**
```bash
gunzip -c backup.sql.gz | psql $DATABASE_URL
```

2. **Redeploy Application:**
```bash
docker-compose -f docker-compose.prod.yml up -d
```

3. **Verify:**
```bash
curl https://api.aiparati.pt/health
```

## 📈 Scaling

### Horizontal Scaling (Kubernetes)

```bash
# Auto-scaling
kubectl autoscale deployment fundai-api \
  --cpu-percent=70 \
  --min=2 \
  --max=10

# Manual scaling
kubectl scale deployment fundai-api --replicas=5
```

### Vertical Scaling (Resources)

```yaml
# k8s/deployment.yaml
resources:
  requests:
    memory: "512Mi"
    cpu: "500m"
  limits:
    memory: "2Gi"
    cpu: "2000m"
```

## 🔍 Troubleshooting

### Common Issues

**High CPU usage:**
```bash
# Check Celery workers
docker-compose logs celery-worker

# Scale workers
docker-compose up -d --scale celery-worker=3
```

**Database connections:**
```bash
# Check active connections
psql $DATABASE_URL -c "SELECT count(*) FROM pg_stat_activity;"

# Adjust pool size in config
SQLALCHEMY_POOL_SIZE=20
SQLALCHEMY_MAX_OVERFLOW=10
```

**Memory leaks:**
```bash
# Restart API gracefully
docker-compose restart api

# Monitor memory
docker stats fundai-api
```

## ✅ Post-Deployment Checklist

- [ ] Health endpoint responds (200 OK)
- [ ] Database migrations applied
- [ ] SSL certificate valid
- [ ] Monitoring dashboards show metrics
- [ ] Logs are flowing to centralized logging
- [ ] Backups running successfully
- [ ] API rate limiting working
- [ ] Error tracking (Sentry) receiving events
- [ ] Documentation updated with new endpoints
- [ ] Team notified of deployment

## 📞 Support

- **Emergency Contact:** bilal@aiparati.pt
- **Status Page:** https://status.aiparati.pt
- **Runbook:** https://wiki.aiparati.pt/fundai/runbook

---

**Last Updated:** 2025-11-01  
**Version:** 1.0
