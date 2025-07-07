# 🚀 **FASTAPI RBAC - GUIA DE DEPLOYMENT COMPLETO**

Este guia fornece instruções detalhadas para deploy em produção do sistema FastAPI RBAC com todas as funcionalidades enterprise implementadas.

## 📋 **ÍNDICE**

1. [Pré-requisitos](#pré-requisitos)
2. [Configuração do Ambiente](#configuração-do-ambiente)
3. [Database PostgreSQL](#database-postgresql)
4. [Redis Cache](#redis-cache)
5. [Deploy com Docker](#deploy-com-docker)
6. [Configuração de Segurança](#configuração-de-segurança)
7. [Monitoramento](#monitoramento)
8. [Backup & Recovery](#backup--recovery)
9. [Performance Tuning](#performance-tuning)
10. [Troubleshooting](#troubleshooting)

---

## 🛠️ **PRÉ-REQUISITOS**

### **Sistema Operacional**
- Ubuntu 20.04+ / CentOS 8+ / Amazon Linux 2
- Docker & Docker Compose instalados
- Nginx (reverse proxy)
- Certbot (SSL certificates)

### **Hardware Mínimo**
- **CPU**: 2 cores
- **RAM**: 4GB (8GB recomendado)
- **Storage**: 20GB SSD
- **Network**: 1Gbps

### **Hardware Recomendado (Produção)**
- **CPU**: 4+ cores
- **RAM**: 16GB+
- **Storage**: 100GB+ SSD
- **Database**: Instância separada
- **Redis**: Instância separada ou cluster

---

## ⚙️ **CONFIGURAÇÃO DO AMBIENTE**

### **1. Clone e Preparação**

```bash
# Clone do repositório
git clone <your-repo>
cd fast-rbac

# Criar diretórios de produção
sudo mkdir -p /opt/fast-rbac
sudo cp -r . /opt/fast-rbac/
cd /opt/fast-rbac

# Configurar permissões
sudo chown -R $USER:$USER /opt/fast-rbac
chmod +x scripts/*.sh
```

### **2. Variáveis de Ambiente de Produção**

```bash
# Copiar template de produção
cp env.production.example .env.production

# Editar configurações
nano .env.production
```

**Configuração completa `.env.production`:**

```env
# ===================================
# FASTAPI RBAC - PRODUCTION ENVIRONMENT
# ===================================

# Application
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO
APP_NAME=FastAPI RBAC
APP_VERSION=1.0.0

# Security (CRÍTICO - ALTERE TODOS!)
SECRET_KEY=your-super-secret-production-key-256-bits
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# Database PostgreSQL
DATABASE_URL=postgresql://rbac_user:strong_password@postgres:5432/rbac_prod
POSTGRES_USER=rbac_user
POSTGRES_PASSWORD=strong_password
POSTGRES_DB=rbac_prod

# Redis Cache & Sessions (PERFORMANCE)
REDIS_ENABLED=true
REDIS_URL=redis://redis:6379/0
REDIS_PASSWORD=redis_strong_password
REDIS_MAX_CONNECTIONS=100

# Rate Limiting (SECURITY)
RATE_LIMIT_ENABLED=true
RATE_LIMIT_REQUESTS=1000
RATE_LIMIT_WINDOW=60
RATE_LIMIT_REDIS_KEY_PREFIX=fastapi_rbac_rate_limit

# CORS (Ajuste para seus domínios)
ALLOWED_ORIGINS=https://your-domain.com,https://admin.your-domain.com

# OAuth Providers (Configure conforme necessário)
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
MICROSOFT_CLIENT_ID=your-microsoft-client-id
MICROSOFT_CLIENT_SECRET=your-microsoft-client-secret
GITHUB_CLIENT_ID=your-github-client-id
GITHUB_CLIENT_SECRET=your-github-client-secret

# Email Notifications
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=noreply@your-domain.com
SMTP_PASSWORD=app-specific-password
SMTP_USE_TLS=true

# Monitoring & Logging
ENABLE_PROMETHEUS=true
SENTRY_DSN=https://your-sentry-dsn@sentry.io/project-id

# File Upload
UPLOAD_MAX_SIZE=52428800  # 50MB
UPLOAD_ALLOWED_TYPES=image/jpeg,image/png,image/gif,application/pdf

# Security Headers
TRUSTED_HOSTS=your-domain.com,admin.your-domain.com
ENABLE_CSRF_PROTECTION=true

# Performance
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=40
DATABASE_POOL_RECYCLE=3600
```

---

## 🗄️ **DATABASE POSTGRESQL**

### **1. Instalação PostgreSQL**

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install postgresql postgresql-contrib

# CentOS/RHEL
sudo yum install postgresql postgresql-server postgresql-contrib
```

### **2. Configuração do Database**

```bash
# Conectar como postgres
sudo -u postgres psql

-- Criar usuário e database
CREATE USER rbac_user WITH PASSWORD 'strong_password';
CREATE DATABASE rbac_prod OWNER rbac_user;
GRANT ALL PRIVILEGES ON DATABASE rbac_prod TO rbac_user;

-- Configurações de performance
ALTER SYSTEM SET shared_buffers = '256MB';
ALTER SYSTEM SET effective_cache_size = '1GB';
ALTER SYSTEM SET maintenance_work_mem = '64MB';
ALTER SYSTEM SET checkpoint_completion_target = 0.9;
ALTER SYSTEM SET wal_buffers = '16MB';
ALTER SYSTEM SET default_statistics_target = 100;

-- Reload configuration
SELECT pg_reload_conf();
```

### **3. Backup Automatizado**

```bash
# Criar script de backup
sudo nano /opt/scripts/backup_db.sh
```

```bash
#!/bin/bash
# Database Backup Script

BACKUP_DIR="/opt/backups/database"
DB_NAME="rbac_prod"
DB_USER="rbac_user"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/rbac_backup_$TIMESTAMP.sql.gz"

# Criar diretório se não existir
mkdir -p $BACKUP_DIR

# Fazer backup comprimido
pg_dump -U $DB_USER -h localhost $DB_NAME | gzip > $BACKUP_FILE

# Manter apenas últimos 7 backups
find $BACKUP_DIR -name "rbac_backup_*.sql.gz" -mtime +7 -delete

echo "Backup criado: $BACKUP_FILE"
```

```bash
# Tornar executável e configurar cron
chmod +x /opt/scripts/backup_db.sh

# Backup diário às 2:00 AM
(crontab -l 2>/dev/null; echo "0 2 * * * /opt/scripts/backup_db.sh") | crontab -
```

---

## 🔄 **REDIS CACHE**

### **1. Instalação Redis**

```bash
# Ubuntu/Debian
sudo apt install redis-server

# CentOS/RHEL
sudo yum install redis

# Ou via Docker (recomendado)
docker run -d --name redis \
  -p 6379:6379 \
  -v redis_data:/data \
  --restart unless-stopped \
  redis:7-alpine redis-server --requirepass redis_strong_password
```

### **2. Configuração Redis**

```bash
# Editar configuração
sudo nano /etc/redis/redis.conf
```

```conf
# Configurações de produção
bind 127.0.0.1
port 6379
requirepass redis_strong_password

# Performance
maxmemory 2gb
maxmemory-policy allkeys-lru
save 900 1
save 300 10
save 60 10000

# Security
protected-mode yes
timeout 300

# Logging
loglevel notice
logfile /var/log/redis/redis-server.log
```

### **3. Monitoramento Redis**

```bash
# Script de monitoramento
sudo nano /opt/scripts/redis_monitor.sh
```

```bash
#!/bin/bash
# Redis Monitoring Script

REDIS_CLI="redis-cli -a redis_strong_password"
ALERT_EMAIL="admin@your-domain.com"

# Verificar conexão
if ! $REDIS_CLI ping > /dev/null 2>&1; then
    echo "Redis connection failed!" | mail -s "Redis Alert" $ALERT_EMAIL
    exit 1
fi

# Verificar uso de memória
MEMORY_USAGE=$($REDIS_CLI info memory | grep used_memory_human | cut -d: -f2 | tr -d '\r')
echo "Redis Memory Usage: $MEMORY_USAGE"

# Verificar keyspace
KEYSPACE=$($REDIS_CLI info keyspace)
echo "Redis Keyspace: $KEYSPACE"
```

---

## 🐳 **DEPLOY COM DOCKER**

### **1. Docker Compose Produção**

```bash
# Usar o docker-compose de produção
cp docker-compose.prod.yml docker-compose.yml

# Editar se necessário
nano docker-compose.yml
```

### **2. Deploy Completo**

```bash
# Build das imagens
uv run task docker-build

# Deploy em produção
docker-compose -f docker-compose.prod.yml up -d

# Verificar serviços
docker-compose ps
docker-compose logs -f backend
```

### **3. Configuração Nginx**

```bash
# Configuração do Nginx
sudo nano /etc/nginx/sites-available/fastapi-rbac
```

```nginx
upstream backend {
    server 127.0.0.1:8000;
    keepalive 32;
}

upstream frontend {
    server 127.0.0.1:8501;
    keepalive 32;
}

# Rate Limiting
limit_req_zone $binary_remote_addr zone=auth:10m rate=5r/m;
limit_req_zone $binary_remote_addr zone=api:10m rate=100r/m;

server {
    listen 80;
    server_name your-domain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com;

    # SSL Configuration
    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES128-GCM-SHA256:ECDHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;

    # Security Headers
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    add_header Strict-Transport-Security "max-age=63072000; includeSubDomains; preload";

    # API Backend
    location /api/ {
        limit_req zone=api burst=20 nodelay;
        proxy_pass http://backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Timeout settings
        proxy_connect_timeout 30s;
        proxy_send_timeout 30s;
        proxy_read_timeout 30s;
    }

    # Auth endpoints with strict rate limiting
    location ~ ^/(auth|oauth)/ {
        limit_req zone=auth burst=10 nodelay;
        proxy_pass http://backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Health checks (no rate limiting)
    location /health {
        proxy_pass http://backend;
        access_log off;
    }

    # Documentation (production: block or restrict)
    location ~ ^/(docs|redoc|openapi.json) {
        # deny all;  # Uncomment for production
        proxy_pass http://backend;
    }

    # Cache static files
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
        proxy_pass http://backend;
    }

    # Default to backend
    location / {
        proxy_pass http://backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}

# Admin Frontend
server {
    listen 443 ssl http2;
    server_name admin.your-domain.com;

    # SSL Configuration (same as above)
    ssl_certificate /etc/letsencrypt/live/admin.your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/admin.your-domain.com/privkey.pem;

    # Basic Auth for extra security
    auth_basic "Admin Area";
    auth_basic_user_file /etc/nginx/.htpasswd;

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
```

### **4. SSL com Let's Encrypt**

```bash
# Instalar Certbot
sudo apt install certbot python3-certbot-nginx

# Obter certificados
sudo certbot --nginx -d your-domain.com -d admin.your-domain.com

# Auto-renovação
(crontab -l 2>/dev/null; echo "0 12 * * * /usr/bin/certbot renew --quiet") | crontab -
```

---

## 🔒 **CONFIGURAÇÃO DE SEGURANÇA**

### **1. Firewall**

```bash
# UFW Configuration
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable

# Fail2ban para proteção contra ataques
sudo apt install fail2ban
sudo systemctl enable fail2ban
```

### **2. Configuração Fail2ban**

```bash
sudo nano /etc/fail2ban/jail.local
```

```ini
[DEFAULT]
bantime = 1h
findtime = 10m
maxretry = 5

[nginx-rate-limit]
enabled = true
filter = nginx-rate-limit
logpath = /var/log/nginx/error.log
maxretry = 10

[nginx-auth]
enabled = true
filter = nginx-auth
logpath = /var/log/nginx/error.log
maxretry = 3
```

### **3. Monitoring de Segurança**

```bash
# Script de monitoramento
sudo nano /opt/scripts/security_monitor.sh
```

```bash
#!/bin/bash
# Security Monitoring Script

LOG_FILE="/var/log/security_monitor.log"
ALERT_EMAIL="security@your-domain.com"

# Verificar tentativas de login suspeitas
FAILED_LOGINS=$(tail -1000 /var/log/auth.log | grep "Failed password" | wc -l)
if [ $FAILED_LOGINS -gt 50 ]; then
    echo "$(date): High failed login attempts: $FAILED_LOGINS" >> $LOG_FILE
    echo "High failed login attempts detected" | mail -s "Security Alert" $ALERT_EMAIL
fi

# Verificar uso de recursos
CPU_USAGE=$(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | cut -d'%' -f1)
if (( $(echo "$CPU_USAGE > 80" | bc -l) )); then
    echo "$(date): High CPU usage: $CPU_USAGE%" >> $LOG_FILE
fi

# Verificar espaço em disco
DISK_USAGE=$(df / | tail -1 | awk '{print $5}' | cut -d'%' -f1)
if [ $DISK_USAGE -gt 85 ]; then
    echo "$(date): High disk usage: $DISK_USAGE%" >> $LOG_FILE
    echo "High disk usage detected" | mail -s "System Alert" $ALERT_EMAIL
fi
```

---

## 📊 **MONITORAMENTO**

### **1. Health Checks**

```bash
# Script de health check
sudo nano /opt/scripts/health_check.sh
```

```bash
#!/bin/bash
# Health Check Script

API_URL="https://your-domain.com"
ALERT_EMAIL="ops@your-domain.com"

# Check API Health
if ! curl -f "$API_URL/health" > /dev/null 2>&1; then
    echo "API health check failed" | mail -s "API Down Alert" $ALERT_EMAIL
    exit 1
fi

# Check Database
if ! docker exec postgres pg_isready > /dev/null 2>&1; then
    echo "Database health check failed" | mail -s "Database Down Alert" $ALERT_EMAIL
    exit 1
fi

# Check Redis
if ! docker exec redis redis-cli -a redis_strong_password ping > /dev/null 2>&1; then
    echo "Redis health check failed" | mail -s "Redis Down Alert" $ALERT_EMAIL
    exit 1
fi

echo "All services healthy"
```

### **2. Prometheus & Grafana**

```yaml
# monitoring/docker-compose.yml
version: '3.8'

services:
  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--web.console.libraries=/etc/prometheus/console_libraries'
      - '--web.console.templates=/etc/prometheus/consoles'

  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    volumes:
      - grafana_data:/var/lib/grafana
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin_password

volumes:
  prometheus_data:
  grafana_data:
```

---

## 🎯 **PERFORMANCE TUNING**

### **1. Database Optimization**

```sql
-- Performance tuning PostgreSQL
-- /var/lib/postgresql/data/postgresql.conf

shared_buffers = 256MB                  # 25% of RAM
effective_cache_size = 1GB              # 75% of RAM
maintenance_work_mem = 64MB
checkpoint_completion_target = 0.9
wal_buffers = 16MB
default_statistics_target = 100

# Connection pooling
max_connections = 100
shared_preload_libraries = 'pg_stat_statements'
```

### **2. Redis Optimization**

```conf
# /etc/redis/redis.conf

# Memory optimization
maxmemory 2gb
maxmemory-policy allkeys-lru

# Persistence
save 900 1
save 300 10
save 60 10000

# Network
tcp-keepalive 300
timeout 0
```

### **3. Application Optimization**

```python
# app/config/settings.py - Production values

# Database
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=40
DATABASE_POOL_RECYCLE=3600

# Redis
REDIS_MAX_CONNECTIONS=100
REDIS_POOL_TIMEOUT=30

# Cache TTL
PERMISSION_CACHE_TTL=1800  # 30 minutes
USER_CACHE_TTL=900         # 15 minutes
SESSION_CACHE_TTL=86400    # 24 hours
```

---

## 🔧 **TROUBLESHOOTING**

### **1. Logs e Debugging**

```bash
# Visualizar logs
docker-compose logs -f backend
docker-compose logs -f frontend
docker-compose logs -f postgres
docker-compose logs -f redis

# Logs do sistema
tail -f /var/log/nginx/access.log
tail -f /var/log/nginx/error.log
tail -f /var/log/fail2ban.log

# Logs da aplicação
tail -f /opt/fast-rbac/logs/app.log
```

### **2. Problemas Comuns**

#### **Redis Connection Issues**
```bash
# Verificar Redis
docker exec redis redis-cli -a redis_strong_password ping

# Verificar conectividade
telnet localhost 6379

# Limpar cache se necessário
docker exec redis redis-cli -a redis_strong_password FLUSHALL
```

#### **Database Connection Issues**
```bash
# Verificar PostgreSQL
docker exec postgres pg_isready

# Verificar conexões
docker exec postgres psql -U rbac_user -d rbac_prod -c "SELECT version();"

# Verificar locks
docker exec postgres psql -U rbac_user -d rbac_prod -c "SELECT * FROM pg_locks;"
```

#### **Performance Issues**
```bash
# Verificar uso de recursos
docker stats

# Verificar cache hit rate
curl -H "Authorization: Bearer TOKEN" https://your-domain.com/cache/stats

# Verificar rate limiting
curl -I https://your-domain.com/api/health
```

### **3. Scripts de Manutenção**

```bash
# Script de manutenção diária
sudo nano /opt/scripts/daily_maintenance.sh
```

```bash
#!/bin/bash
# Daily Maintenance Script

echo "Starting daily maintenance..."

# Limpar logs antigos
find /var/log -name "*.log" -mtime +30 -delete

# Limpar cache desnecessário
docker exec redis redis-cli -a redis_strong_password --scan --pattern "*:expired:*" | xargs -I {} docker exec redis redis-cli -a redis_strong_password DEL {}

# Vacuum database
docker exec postgres psql -U rbac_user -d rbac_prod -c "VACUUM ANALYZE;"

# Verificar espaço em disco
df -h

echo "Daily maintenance completed."
```

---

## 📈 **CHECKLIST DE PRODUÇÃO**

### **Antes do Deploy**
- [ ] Todas as variáveis de ambiente configuradas
- [ ] SSL certificates instalados
- [ ] Firewall configurado
- [ ] Backup automatizado configurado
- [ ] Monitoring configurado
- [ ] Health checks funcionando

### **Após o Deploy**
- [ ] API health check respondendo
- [ ] Frontend acessível
- [ ] Redis funcionando
- [ ] Database conectado
- [ ] Logs sendo gerados
- [ ] Rate limiting funcionando
- [ ] SSL válido
- [ ] Performance dentro dos parâmetros

### **Monitoramento Contínuo**
- [ ] Verificar logs diariamente
- [ ] Monitorar uso de recursos
- [ ] Verificar backups
- [ ] Atualizar dependências mensalmente
- [ ] Renovar certificados automaticamente

---

## 🆘 **SUPORTE**

Para suporte adicional:
- **Logs**: Verificar `/var/log/` e `docker-compose logs`
- **Performance**: Usar `/cache/stats` e `/info` endpoints
- **Security**: Monitorar `/var/log/fail2ban.log`
- **Health**: Usar `/health` endpoint

**Configuração completamente enterprise-ready para produção!** 🚀 