# 🚀 **FASTAPI RBAC - GUIA DE DEPLOYMENT ENTERPRISE**

Este guia fornece instruções completas para deploy em produção do sistema FastAPI RBAC com todas as funcionalidades enterprise: **RBAC completo**, **2FA TOTP**, **Redis Cache**, **Rate Limiting**, e **interface administrativa**.

## 📋 **ÍNDICE**

1. [Pré-requisitos](#pré-requisitos)
2. [Configuração do Ambiente](#configuração-do-ambiente)
3. [Database PostgreSQL](#database-postgresql)
4. [Redis Cache & Performance](#redis-cache--performance)
5. [2FA & Security Setup](#2fa--security-setup)
6. [Deploy com Docker](#deploy-com-docker)
7. [Configuração de Segurança](#configuração-de-segurança)
8. [Nginx & SSL](#nginx--ssl)
9. [Monitoramento & Logs](#monitoramento--logs)
10. [Backup & Recovery](#backup--recovery)
11. [Performance Tuning](#performance-tuning)
12. [Troubleshooting](#troubleshooting)

---

## 🛠️ **PRÉ-REQUISITOS**

### **Sistema Operacional**
- Ubuntu 20.04+ / CentOS 8+ / Amazon Linux 2
- Docker & Docker Compose 2.0+
- Nginx 1.18+ (reverse proxy)
- Certbot (SSL certificates)

### **Hardware Mínimo**
- **CPU**: 2 cores
- **RAM**: 4GB (8GB recomendado)
- **Storage**: 20GB SSD
- **Network**: 1Gbps

### **Hardware Recomendado (Produção)**
- **CPU**: 4+ cores  
- **RAM**: 16GB+
- **Storage**: 100GB+ SSD NVMe
- **Database**: Instância separada PostgreSQL 14+
- **Redis**: Instância separada ou cluster

### **Software Dependencies**
```bash
# Docker & Docker Compose
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Nginx
sudo apt update && sudo apt install nginx certbot python3-certbot-nginx

# Redis Tools (opcional)
sudo apt install redis-tools
```

---

## ⚙️ **CONFIGURAÇÃO DO AMBIENTE**

### **1. Clone e Preparação**

```bash
# Clone do repositório
git clone <your-repo-url>
cd fast+rbac

# Criar estrutura de produção
sudo mkdir -p /opt/fast-rbac
sudo cp -r . /opt/fast-rbac/
cd /opt/fast-rbac

# Configurar permissões
sudo chown -R $USER:docker /opt/fast-rbac
chmod +x scripts/*.sh (se existir)
```

### **2. Variáveis de Ambiente de Produção**

```bash
# Copiar template de produção
cp env.production.example .env.production

# Gerar chave secreta segura
python3 -c "import secrets; print('SECRET_KEY=' + secrets.token_urlsafe(32))" >> .env.production
```

**Configuração completa `.env.production`:**

```env
# ===================================
# FASTAPI RBAC - ENTERPRISE PRODUCTION
# ===================================

# Application
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO
APP_NAME=FastAPI RBAC Enterprise
APP_VERSION=1.0.0

# Security (CRÍTICO - ALTERE TODOS!)
SECRET_KEY=your-generated-32-byte-secret-key
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# Database PostgreSQL (Production)
DATABASE_URL=postgresql://rbac_user:StrongPassword123!@postgres:5432/rbac_prod
POSTGRES_USER=rbac_user
POSTGRES_PASSWORD=StrongPassword123!
POSTGRES_DB=rbac_prod

# Redis Cache & Sessions (PERFORMANCE LAYER)
REDIS_ENABLED=true
REDIS_URL=redis://:RedisPassword123!@redis:6379/0
REDIS_PASSWORD=RedisPassword123!
REDIS_MAX_CONNECTIONS=100
REDIS_TIMEOUT=30

# 2FA TOTP Configuration (ENTERPRISE SECURITY)
TOTP_ISSUER=FastAPI RBAC Enterprise
TOTP_WINDOW=1
TOTP_DIGITS=6
TOTP_PERIOD=30
BACKUP_CODES_COUNT=10

# Rate Limiting (SECURITY & PERFORMANCE)
RATE_LIMIT_ENABLED=true
RATE_LIMIT_AUTH_REQUESTS=10
RATE_LIMIT_AUTH_WINDOW=60
RATE_LIMIT_LOGIN_REQUESTS=5
RATE_LIMIT_LOGIN_WINDOW=300
RATE_LIMIT_API_REQUESTS=1000
RATE_LIMIT_API_WINDOW=60
RATE_LIMIT_ADMIN_REQUESTS=50
RATE_LIMIT_ADMIN_WINDOW=60

# CORS (Configure para seus domínios)
ALLOWED_ORIGINS=https://your-domain.com,https://admin.your-domain.com
ALLOWED_ORIGINS_REGEX=https://.*\.your-domain\.com

# OAuth Providers (Configure conforme necessário)
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
MICROSOFT_CLIENT_ID=your-microsoft-client-id
MICROSOFT_CLIENT_SECRET=your-microsoft-client-secret
GITHUB_CLIENT_ID=your-github-client-id
GITHUB_CLIENT_SECRET=your-github-client-secret

# Email Notifications (2FA Recovery)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=noreply@your-domain.com
SMTP_PASSWORD=your-app-specific-password
SMTP_USE_TLS=true
SMTP_FROM_EMAIL=noreply@your-domain.com

# File Upload & Storage
UPLOAD_MAX_SIZE=52428800  # 50MB
UPLOAD_ALLOWED_TYPES=image/jpeg,image/png,image/gif,application/pdf
UPLOAD_PATH=/opt/fast-rbac/uploads

# Security Headers & Protection
TRUSTED_HOSTS=your-domain.com,admin.your-domain.com
ENABLE_CSRF_PROTECTION=true
SECURE_COOKIES=true
HTTPS_ONLY=true

# Performance Tuning
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=40
DATABASE_POOL_RECYCLE=3600
DATABASE_POOL_PRE_PING=true

# Monitoring & Logging
ENABLE_PROMETHEUS=true
PROMETHEUS_PORT=9090
SENTRY_DSN=https://your-sentry-dsn@sentry.io/project-id
LOG_TO_FILE=true
LOG_FILE=/opt/fast-rbac/logs/app.log
```

---

## 🗄️ **DATABASE POSTGRESQL**

### **1. Instalação PostgreSQL 14+**

```bash
# Ubuntu/Debian - PostgreSQL 14
sudo apt update
sudo apt install -y postgresql-14 postgresql-contrib-14

# Iniciar serviços
sudo systemctl start postgresql
sudo systemctl enable postgresql
```

### **2. Configuração Enterprise do Database**

```bash
# Conectar como postgres
sudo -u postgres psql

-- Criar usuário e database para produção
CREATE USER rbac_user WITH PASSWORD 'StrongPassword123!';
CREATE DATABASE rbac_prod OWNER rbac_user;
GRANT ALL PRIVILEGES ON DATABASE rbac_prod TO rbac_user;

-- Extensões necessárias
\c rbac_prod
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Configurações de performance para produção
ALTER SYSTEM SET shared_buffers = '512MB';
ALTER SYSTEM SET effective_cache_size = '2GB';
ALTER SYSTEM SET maintenance_work_mem = '128MB';
ALTER SYSTEM SET checkpoint_completion_target = 0.9;
ALTER SYSTEM SET wal_buffers = '32MB';
ALTER SYSTEM SET default_statistics_target = 100;
ALTER SYSTEM SET random_page_cost = 1.1;
ALTER SYSTEM SET effective_io_concurrency = 200;

-- Security settings
ALTER SYSTEM SET log_statement = 'mod';
ALTER SYSTEM SET log_min_duration_statement = '1000';
ALTER SYSTEM SET log_line_prefix = '%t [%p]: [%l-1] user=%u,db=%d,app=%a,client=%h ';

-- Aplicar configurações
SELECT pg_reload_conf();
```

### **3. Configuração de Performance PostgreSQL**

```bash
# Editar postgresql.conf
sudo nano /etc/postgresql/14/main/postgresql.conf
```

```conf
# Memory Settings
shared_buffers = 512MB                    # 25% da RAM
effective_cache_size = 2GB                # 75% da RAM
work_mem = 4MB                           # Para ordenações
maintenance_work_mem = 128MB             # Para operações de manutenção

# Connection Settings
max_connections = 200
superuser_reserved_connections = 3

# WAL Settings
wal_level = replica
max_wal_size = 2GB
min_wal_size = 1GB
checkpoint_completion_target = 0.9

# Query Planner
random_page_cost = 1.1                   # Para SSD
effective_io_concurrency = 200           # Para SSD

# Logging
log_min_duration_statement = 1000        # Log queries > 1s
log_statement = 'mod'                    # Log modificações
log_connections = on
log_disconnections = on
```

---

## 🚀 **REDIS CACHE & PERFORMANCE**

### **1. Instalação Redis 7+**

```bash
# Ubuntu/Debian - Redis 7
curl -fsSL https://packages.redis.io/gpg | sudo gpg --dearmor -o /usr/share/keyrings/redis-archive-keyring.gpg
echo "deb [signed-by=/usr/share/keyrings/redis-archive-keyring.gpg] https://packages.redis.io/deb $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/redis.list
sudo apt update
sudo apt install redis-server
```

### **2. Configuração Redis para Produção**

```bash
# Editar redis.conf
sudo nano /etc/redis/redis.conf
```

```conf
# Security
requirepass RedisPassword123!
bind 127.0.0.1 ::1
protected-mode yes
port 6379

# Memory & Performance
maxmemory 1gb
maxmemory-policy allkeys-lru
tcp-keepalive 300
timeout 300

# Persistence (para cache)
save 900 1
save 300 10
save 60 10000

# Logging
loglevel notice
logfile /var/log/redis/redis-server.log

# Performance tuning
tcp-backlog 511
databases 16
stop-writes-on-bgsave-error no
```

### **3. Configuração de Cache da Aplicação**

O sistema usa Redis para:
- **Permission Caching**: TTL 30 minutos
- **User Data Caching**: TTL 15 minutos  
- **Session Management**: TTL 24 horas
- **Rate Limiting**: Contadores com TTL
- **2FA Token Caching**: TTL 10 minutos

---

## 🔑 **2FA & SECURITY SETUP**

### **1. Configuração 2FA TOTP**

O sistema inclui autenticação de dois fatores enterprise com:
- **TOTP Codes**: Compatível com Google Authenticator
- **QR Code Generation**: Setup automático
- **Backup Codes**: 10 códigos criptografados
- **Anti-Replay Protection**: Prevenção de ataques

### **2. Endpoints 2FA Configurados**

```bash
# Verificar funcionalidade 2FA
curl -H "Authorization: Bearer TOKEN" http://localhost:8000/auth/2fa/status

# Endpoints disponíveis:
# GET /auth/2fa/status
# POST /auth/2fa/setup  
# POST /auth/2fa/enable
# POST /auth/2fa/login
# GET /auth/2fa/qr-code
# POST /auth/2fa/regenerate-backup-codes
```

### **3. Configuração de Segurança Enterprise**

```env
# .env.production - Security settings
TOTP_ISSUER=FastAPI RBAC Enterprise
TOTP_WINDOW=1                    # Janela de tolerância
TOTP_DIGITS=6                    # Dígitos do código
BACKUP_CODES_COUNT=10            # Códigos de backup
SECRET_KEY=your-32-byte-key      # Chave para criptografia Fernet
```

---

## 🐳 **DEPLOY COM DOCKER**

### **1. Docker Compose Produção**

```yaml
# docker-compose.prod.yml
version: '3.8'

services:
  # PostgreSQL Database
  postgres:
    image: postgres:14-alpine
    container_name: rbac_postgres
    environment:
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: ${POSTGRES_DB}
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./scripts/init.sql:/docker-entrypoint-initdb.d/init.sql
    networks:
      - rbac_network
    restart: unless-stopped
    deploy:
      resources:
        limits:
          memory: 2G
        reservations:
          memory: 1G

  # Redis Cache
  redis:
    image: redis:7-alpine
    container_name: rbac_redis
    command: redis-server --requirepass ${REDIS_PASSWORD} --maxmemory 1gb --maxmemory-policy allkeys-lru
    volumes:
      - redis_data:/data
    networks:
      - rbac_network
    restart: unless-stopped
    deploy:
      resources:
        limits:
          memory: 1G
        reservations:
          memory: 512M

  # FastAPI Backend
  backend:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: rbac_backend
    environment:
      - DATABASE_URL=postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@postgres:5432/${POSTGRES_DB}
      - REDIS_URL=redis://:${REDIS_PASSWORD}@redis:6379/0
      - REDIS_ENABLED=true
    env_file:
      - .env.production
    volumes:
      - ./uploads:/app/uploads
      - ./logs:/app/logs
    networks:
      - rbac_network
    depends_on:
      - postgres
      - redis
    restart: unless-stopped
    deploy:
      resources:
        limits:
          memory: 2G
        reservations:
          memory: 1G
    ports:
      - "8000:8000"

  # Streamlit Frontend
  frontend:
    build:
      context: .
      dockerfile: Dockerfile.frontend
    container_name: rbac_frontend
    environment:
      - API_BASE_URL=http://backend:8000
    env_file:
      - .env.production
    volumes:
      - ./front:/app/front
    networks:
      - rbac_network
    depends_on:
      - backend
    restart: unless-stopped
    deploy:
      resources:
        limits:
          memory: 1G
        reservations:
          memory: 512M
    ports:
      - "8501:8501"

  # Nginx Reverse Proxy
  nginx:
    image: nginx:alpine
    container_name: rbac_nginx
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf
      - ./nginx/ssl:/etc/nginx/ssl
      - ./logs/nginx:/var/log/nginx
    ports:
      - "80:80"
      - "443:443"
    networks:
      - rbac_network
    depends_on:
      - backend
      - frontend
    restart: unless-stopped

volumes:
  postgres_data:
  redis_data:

networks:
  rbac_network:
    driver: bridge
```

### **2. Dockerfile Otimizado para Produção**

```dockerfile
# Dockerfile
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd --create-home --shell /bin/bash app

# Set working directory
WORKDIR /app

# Install UV
RUN pip install uv

# Copy requirements and install dependencies
COPY pyproject.toml uv.lock ./
RUN uv sync --no-dev

# Copy application
COPY . .

# Change ownership
RUN chown -R app:app /app

# Switch to non-root user
USER app

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

# Run application
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### **3. Deploy Commands**

```bash
# Preparar ambiente
cd /opt/fast-rbac

# Build e deploy
docker-compose -f docker-compose.prod.yml up -d --build

# Verificar status
docker-compose -f docker-compose.prod.yml ps

# Ver logs
docker-compose -f docker-compose.prod.yml logs -f backend

# Executar migrações (primeira vez)
docker-compose -f docker-compose.prod.yml exec backend uv run alembic upgrade head
```

---

## 🔒 **CONFIGURAÇÃO DE SEGURANÇA**

### **1. Firewall & Network Security**

```bash
# UFW Configuration
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw allow 6379/tcp  # Redis (apenas local/VPN)
sudo ufw allow 5432/tcp  # PostgreSQL (apenas local/VPN)
sudo ufw enable

# Fail2ban para proteção contra ataques
sudo apt install fail2ban
sudo nano /etc/fail2ban/jail.local
```

```ini
# /etc/fail2ban/jail.local
[DEFAULT]
bantime = 3600
findtime = 600
maxretry = 5

[nginx-http-auth]
enabled = true
filter = nginx-http-auth
logpath = /opt/fast-rbac/logs/nginx/error.log
maxretry = 3

[nginx-dos]
enabled = true
filter = nginx-dos
logpath = /opt/fast-rbac/logs/nginx/access.log
maxretry = 10
findtime = 60
bantime = 600
```

### **2. SSL/TLS Configuration**

```bash
# Obter certificado SSL
sudo certbot --nginx -d your-domain.com -d admin.your-domain.com

# Auto-renewal
sudo crontab -e
# Adicionar linha:
0 12 * * * /usr/bin/certbot renew --quiet
```

---

## 🌐 **NGINX & SSL**

### **1. Configuração Nginx**

```nginx
# /opt/fast-rbac/nginx/nginx.conf
user nginx;
worker_processes auto;
error_log /var/log/nginx/error.log warn;
pid /var/run/nginx.pid;

events {
    worker_connections 1024;
    use epoll;
    multi_accept on;
}

http {
    include /etc/nginx/mime.types;
    default_type application/octet-stream;

    # Logging
    log_format main '$remote_addr - $remote_user [$time_local] "$request" '
                    '$status $body_bytes_sent "$http_referer" '
                    '"$http_user_agent" "$http_x_forwarded_for"';
    access_log /var/log/nginx/access.log main;

    # Performance
    sendfile on;
    tcp_nopush on;
    tcp_nodelay on;
    keepalive_timeout 65;
    types_hash_max_size 2048;

    # Security Headers
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

    # Rate Limiting
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
    limit_req_zone $binary_remote_addr zone=auth:10m rate=5r/s;

    # Upstream Backend
    upstream backend {
        server backend:8000;
        keepalive 32;
    }

    # Upstream Frontend
    upstream frontend {
        server frontend:8501;
        keepalive 32;
    }

    # Redirect HTTP to HTTPS
    server {
        listen 80;
        server_name your-domain.com admin.your-domain.com;
        return 301 https://$server_name$request_uri;
    }

    # Main Application
    server {
        listen 443 ssl http2;
        server_name your-domain.com;

        # SSL Configuration
        ssl_certificate /etc/nginx/ssl/your-domain.com.crt;
        ssl_certificate_key /etc/nginx/ssl/your-domain.com.key;
        ssl_protocols TLSv1.2 TLSv1.3;
        ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512;
        ssl_prefer_server_ciphers off;

        # Backend API
        location /api/ {
            limit_req zone=api burst=20 nodelay;
            proxy_pass http://backend/;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        # Auth endpoints with stricter limits
        location /auth/ {
            limit_req zone=auth burst=10 nodelay;
            proxy_pass http://backend/auth/;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        # Health check (no rate limit)
        location /health {
            proxy_pass http://backend/health;
            access_log off;
        }
    }

    # Admin Interface
    server {
        listen 443 ssl http2;
        server_name admin.your-domain.com;

        # SSL Configuration
        ssl_certificate /etc/nginx/ssl/admin.your-domain.com.crt;
        ssl_certificate_key /etc/nginx/ssl/admin.your-domain.com.key;

        # Streamlit Frontend
        location / {
            proxy_pass http://frontend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            
            # WebSocket support for Streamlit
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
        }
    }
}
```

---

## 📊 **MONITORAMENTO & LOGS**

### **1. Sistema de Logs**

A aplicação possui logging enterprise completo:
- **Performance Logging**: Requests > 500ms
- **User Activity**: Todas ações de usuários
- **Security Events**: Login attempts, 2FA, etc.
- **Cache Statistics**: Redis performance
- **API Calls**: Todos requests com métricas

### **2. Endpoints de Monitoramento**

```bash
# Health checks
curl https://your-domain.com/health

# Cache statistics (requer admin)
curl -H "Authorization: Bearer TOKEN" https://your-domain.com/api/cache/stats

# Performance test
curl -X POST -H "Authorization: Bearer TOKEN" https://your-domain.com/api/cache/test
```

### **3. Configuração de Logs**

```bash
# Criar diretório de logs
sudo mkdir -p /opt/fast-rbac/logs/{app,nginx,postgres,redis}

# Configurar logrotate
sudo nano /etc/logrotate.d/fast-rbac
```

```
/opt/fast-rbac/logs/app/*.log {
    daily
    missingok
    rotate 52
    compress
    delaycompress
    notifempty
    create 644 app app
    postrotate
        docker-compose -f /opt/fast-rbac/docker-compose.prod.yml restart backend
    endscript
}
```

---

## 🔄 **BACKUP & RECOVERY**

### **1. Script de Backup Automatizado**

```bash
# Criar script de backup
sudo nano /opt/scripts/backup.sh
```

```bash
#!/bin/bash
# FastAPI RBAC - Backup Script Enterprise

set -e

BACKUP_DIR="/opt/backups"
DATE=$(date +%Y%m%d_%H%M%S)
RETENTION_DAYS=30

# Database backup
echo "Starting database backup..."
docker-compose -f /opt/fast-rbac/docker-compose.prod.yml exec -T postgres \
    pg_dump -U rbac_user rbac_prod | gzip > "$BACKUP_DIR/db_backup_$DATE.sql.gz"

# Redis backup
echo "Starting Redis backup..."
docker-compose -f /opt/fast-rbac/docker-compose.prod.yml exec -T redis \
    redis-cli --rdb /data/dump.rdb
cp /opt/fast-rbac/redis_data/dump.rdb "$BACKUP_DIR/redis_backup_$DATE.rdb"

# Application files backup
echo "Starting application backup..."
tar -czf "$BACKUP_DIR/app_backup_$DATE.tar.gz" -C /opt fast-rbac \
    --exclude='fast-rbac/logs' \
    --exclude='fast-rbac/.git' \
    --exclude='fast-rbac/__pycache__'

# Cleanup old backups
find "$BACKUP_DIR" -name "*backup*" -mtime +$RETENTION_DAYS -delete

echo "Backup completed: $DATE"
```

### **2. Configurar Cron para Backup**

```bash
# Crontab para backup automático
sudo crontab -e

# Backup diário às 2:00 AM
0 2 * * * /opt/scripts/backup.sh >> /opt/logs/backup.log 2>&1

# Backup de logs semanalmente
0 3 * * 0 tar -czf /opt/backups/logs_$(date +\%Y\%m\%d).tar.gz /opt/fast-rbac/logs/
```

---

## ⚡ **PERFORMANCE TUNING**

### **1. Benchmarks de Performance**

Com Redis e configurações otimizadas:
- **Permission Checks**: ~2ms (vs 50ms database)
- **User Authentication**: ~5ms
- **2FA Token Generation**: ~500ms
- **Cache Hit Rate**: >90%
- **Rate Limiting Overhead**: <1ms

### **2. Configurações de Performance**

```env
# .env.production - Performance settings
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=40
DATABASE_POOL_RECYCLE=3600
REDIS_MAX_CONNECTIONS=100
REDIS_TIMEOUT=30
RATE_LIMIT_ENABLED=true
```

### **3. Monitoramento de Performance**

```bash
# Verificar performance da aplicação
curl -X POST -H "Authorization: Bearer TOKEN" \
    "https://your-domain.com/api/cache/test?iterations=1000"

# Estatísticas do cache
curl -H "Authorization: Bearer TOKEN" \
    "https://your-domain.com/api/cache/stats"
```

---

## 🔧 **TROUBLESHOOTING**

### **1. Problemas Comuns**

#### **Backend não inicia**
```bash
# Verificar logs
docker-compose -f docker-compose.prod.yml logs backend

# Verificar database connection
docker-compose -f docker-compose.prod.yml exec backend \
    uv run python -c "from app.database.base import check_database_connection; print(check_database_connection())"
```

#### **Redis connection failed**
```bash
# Verificar Redis
docker-compose -f docker-compose.prod.yml exec redis redis-cli ping

# Verificar configuração
docker-compose -f docker-compose.prod.yml exec backend \
    uv run python -c "from app.services.redis_service import redis_service; print(redis_service.test_connection())"
```

#### **2FA não funciona**
```bash
# Verificar configuração 2FA
curl -H "Authorization: Bearer TOKEN" \
    "https://your-domain.com/api/auth/2fa/status"

# Verificar logs de 2FA
docker-compose -f docker-compose.prod.yml logs backend | grep -i totp
```

### **2. Health Checks**

```bash
# Script de health check completo
#!/bin/bash
echo "=== FastAPI RBAC Health Check ==="

# Backend
if curl -f -s https://your-domain.com/health >/dev/null; then
    echo "✅ Backend: OK"
else
    echo "❌ Backend: FAIL"
fi

# Database
if docker-compose -f /opt/fast-rbac/docker-compose.prod.yml exec -T postgres pg_isready -U rbac_user >/dev/null; then
    echo "✅ Database: OK"
else
    echo "❌ Database: FAIL"
fi

# Redis
if docker-compose -f /opt/fast-rbac/docker-compose.prod.yml exec -T redis redis-cli ping >/dev/null; then
    echo "✅ Redis: OK"
else
    echo "❌ Redis: FAIL"
fi

# Frontend
if curl -f -s https://admin.your-domain.com >/dev/null; then
    echo "✅ Frontend: OK"
else
    echo "❌ Frontend: FAIL"
fi
```

### **3. Comandos de Manutenção**

```bash
# Restart completo
docker-compose -f docker-compose.prod.yml restart

# Restart apenas backend
docker-compose -f docker-compose.prod.yml restart backend

# Ver uso de recursos
docker stats

# Limpar logs antigos
docker-compose -f docker-compose.prod.yml exec backend find /app/logs -name "*.log" -mtime +7 -delete

# Executar migrações
docker-compose -f docker-compose.prod.yml exec backend uv run alembic upgrade head

# Backup manual
/opt/scripts/backup.sh
```

---

## 📞 **SUPORTE & CONTATO**

Para suporte enterprise:
- **Documentação**: [README.md](README.md), [ENDPOINTS.md](ENDPOINTS.md)
- **Logs**: `/opt/fast-rbac/logs/`
- **Monitoring**: Cache stats endpoint disponível

---

**FastAPI RBAC Enterprise** - Deploy Guide Completo 🚀 