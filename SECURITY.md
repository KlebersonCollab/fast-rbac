# 🔒 Guia de Segurança - FastAPI RBAC Enterprise

Documentação completa das práticas de segurança implementadas no sistema FastAPI RBAC Enterprise, incluindo 2FA, rate limiting, cache seguro e proteções avançadas.

## 📋 Sumário

1. [Visão Geral de Segurança](#visão-geral-de-segurança)
2. [Autenticação e Autorização](#autenticação-e-autorização)
3. [2FA - Autenticação de Dois Fatores](#2fa---autenticação-de-dois-fatores)
4. [Rate Limiting e Proteção DDoS](#rate-limiting-e-proteção-ddos)
5. [Segurança de Dados](#segurança-de-dados)
6. [Configurações de Segurança](#configurações-de-segurança)
7. [Monitoramento e Alertas](#monitoramento-e-alertas)
8. [Boas Práticas](#boas-práticas)
9. [Auditoria e Compliance](#auditoria-e-compliance)
10. [Resposta a Incidentes](#resposta-a-incidentes)

---

## 🛡️ Visão Geral de Segurança

### **Níveis de Segurança Implementados**

#### **NÍVEL 1 - Básico**
- ✅ **Autenticação JWT**: Tokens seguros com expiração
- ✅ **Hash de Senhas**: bcrypt com salt
- ✅ **HTTPS**: Certificados SSL/TLS
- ✅ **CORS**: Configuração restritiva
- ✅ **Input Validation**: Validação de todos os inputs

#### **NÍVEL 2 - Intermediário**
- ✅ **RBAC**: Sistema de controle de acesso baseado em roles
- ✅ **Rate Limiting**: Proteção contra ataques de força bruta
- ✅ **Security Headers**: Headers de segurança HTTP
- ✅ **Session Management**: Gerenciamento seguro de sessões
- ✅ **Error Handling**: Tratamento seguro de erros

#### **NÍVEL 3 - Avançado**
- ✅ **2FA TOTP**: Autenticação de dois fatores
- ✅ **Backup Codes**: Códigos de recuperação criptografados
- ✅ **Anti-Replay**: Proteção contra ataques de replay
- ✅ **Circuit Breaker**: Proteção contra falhas em cascata
- ✅ **Adaptive Security**: Ajuste automático de segurança
- ✅ **Compliance**: Conformidade com padrões

#### **NÍVEL 4 - Enterprise**
- ✅ **OAuth2**: Integração com provedores externos
- ✅ **Audit Logging**: Logs completos de auditoria
- ✅ **Monitoring**: Monitoramento em tempo real
- ✅ **Compliance**: Conformidade com padrões

#### **NÍVEL 5 - Multi-Tenant**
- ✅ **Isolamento de Dados**: Queries filtradas por `tenant_id`
- ✅ **Escopo de Token**: JWT contém `tenant_id` para reforçar o isolamento
- ✅ **Acesso de Superadmin**: Superusuários podem acessar todos os tenants
- ✅ **Segregação de Recursos**: API Keys e Webhooks são específicos do tenant

---

## 🔐 Autenticação e Autorização

### **JWT (JSON Web Tokens)**

#### **Configuração Segura**
```python
# Configurações JWT
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7
SECRET_KEY = "sua-chave-secreta-256-bits"
ALGORITHM = "HS256"
```

#### **Implementação**
- **Tokens de Acesso**: Expiração curta (30 minutos)
- **Tokens de Refresh**: Expiração longa (7 dias)
- **Chave Secreta**: Mínimo 256 bits, gerada aleatoriamente
- **Algoritmo**: HS256 (recomendado para aplicações internas)
- **Payload com Tenant**: O `tenant_id` é incluído no payload do token para garantir que todas as operações subsequentes sejam corretamente escopadas para o tenant do usuário.

### **Sistema RBAC (Role-Based Access Control)**

#### **Roles Implementados**
```python
ROLES = {
    "superadmin": {
        "permissions": ["*"],  # Acesso total
        "description": "Super administrador do sistema"
    },
    "admin": {
        "permissions": [
            "users:*", "roles:*", "permissions:*", 
            "posts:*", "settings:*", "logs:view"
        ],
        "description": "Administrador completo"
    },
    "manager": {
        "permissions": [
            "users:read", "users:update", "posts:*", 
            "settings:read", "logs:view"
        ],
        "description": "Gerente com acesso limitado"
    },
    "editor": {
        "permissions": ["posts:create", "posts:read", "posts:update"],
        "description": "Editor de conteúdo"
    },
    "viewer": {
        "permissions": ["posts:read"],
        "description": "Apenas visualização"
    }
}
```

#### **Verificação de Permissões**
```python
# Middleware de verificação
async def check_permission(permission: str, user: User):
    if user.is_superadmin:
        return True
    
    # Verificar no cache primeiro
    cached_perms = await redis_service.get_user_permissions(user.id)
    if cached_perms:
        return permission in cached_perms
    
    # Fallback para database
    user_perms = await db.get_user_permissions(user.id)
    await redis_service.cache_user_permissions(user.id, user_perms)
    
    return permission in user_perms
```

---

## 🔑 2FA - Autenticação de Dois Fatores

### **TOTP (Time-based One-Time Password)**

#### **Implementação Enterprise**
```python
# Configuração TOTP
TOTP_ISSUER = "FastAPI RBAC Enterprise"
TOTP_PERIOD = 30  # Segundos
TOTP_DIGITS = 6
TOTP_WINDOW = 1   # Janela de tolerância
```

#### **Recursos de Segurança**
- **Criptografia Fernet**: Secrets criptografados no banco
- **Anti-Replay**: Prevenção de reutilização de códigos
- **Backup Codes**: Códigos de recuperação criptografados
- **QR Code Seguro**: Geração SVG sem vazamento de dados

### **Códigos de Backup**

#### **Geração e Armazenamento**
```python
def generate_backup_codes(count: int = 10) -> List[str]:
    codes = []
    for _ in range(count):
        # Gerar código de 8 dígitos
        code = ''.join(random.choices(string.digits, k=8))
        codes.append(code)
    
    # Hash dos códigos antes de armazenar
    hashed_codes = [hash_backup_code(code) for code in codes]
    
    return codes, hashed_codes
```

#### **Validação Segura**
```python
async def validate_backup_code(user_id: int, code: str) -> bool:
    # Buscar códigos do usuário
    user_codes = await db.get_user_backup_codes(user_id)
    
    # Verificar se o código é válido
    code_hash = hash_backup_code(code)
    if code_hash in user_codes:
        # Remover código usado (one-time use)
        await db.remove_backup_code(user_id, code_hash)
        return True
    
    return False
```

---

## 🚦 Rate Limiting e Proteção DDoS

### **Rate Limiting por Endpoint**

#### **Configuração Avançada**
```python
RATE_LIMITS = {
    "/auth/login": {
        "requests": 5,
        "window": 300,  # 5 minutos
        "burst": 2
    },
    "/auth/register": {
        "requests": 3,
        "window": 300,
        "burst": 1
    },
    "/auth/2fa/login": {
        "requests": 3,
        "window": 300,
        "burst": 1
    },
    "/admin/*": {
        "requests": 50,
        "window": 60,
        "burst": 10
    },
    "default": {
        "requests": 100,
        "window": 60,
        "burst": 20
    }
}
```

#### **Rate Limiting Adaptativo**
```python
async def adaptive_rate_limit(request: Request) -> bool:
    # Verificar carga do sistema
    system_load = await get_system_load()
    
    # Ajustar limites baseado na carga
    if system_load > 0.8:
        # Reduzir limites em 50%
        adjusted_limit = base_limit * 0.5
    elif system_load > 0.6:
        # Reduzir limites em 30%
        adjusted_limit = base_limit * 0.7
    else:
        adjusted_limit = base_limit
    
    return await check_rate_limit(request, adjusted_limit)
```

### **Circuit Breaker Pattern**

#### **Implementação**
```python
class CircuitBreaker:
    def __init__(self, failure_threshold=5, recovery_timeout=60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
    
    async def call(self, func, *args, **kwargs):
        if self.state == "OPEN":
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = "HALF_OPEN"
            else:
                raise CircuitBreakerOpen("Circuit breaker is open")
        
        try:
            result = await func(*args, **kwargs)
            self.on_success()
            return result
        except Exception as e:
            self.on_failure()
            raise e
    
    def on_success(self):
        self.failure_count = 0
        self.state = "CLOSED"
    
    def on_failure(self):
        self.failure_count += 1
        self.last_failure_time = time.time()
        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"
```

---

## 🔒 Segurança de Dados

### **Criptografia**

#### **Senhas**
```python
# Hash de senhas com bcrypt
import bcrypt

def hash_password(password: str) -> str:
    # Gerar salt e hash
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
```

#### **Secrets 2FA**
```python
# Criptografia Fernet para secrets
from cryptography.fernet import Fernet

def encrypt_secret(secret: str, key: bytes) -> str:
    fernet = Fernet(key)
    encrypted = fernet.encrypt(secret.encode())
    return encrypted.decode()

def decrypt_secret(encrypted_secret: str, key: bytes) -> str:
    fernet = Fernet(key)
    decrypted = fernet.decrypt(encrypted_secret.encode())
    return decrypted.decode()
```

### **Sanitização de Dados**

#### **Input Validation**
```python
from pydantic import BaseModel, validator
import re

class UserCreate(BaseModel):
    username: str
    email: str
    password: str
    
    @validator('username')
    def validate_username(cls, v):
        if not re.match(r'^[a-zA-Z0-9_-]+$', v):
            raise ValueError('Username inválido')
        return v
    
    @validator('email')
    def validate_email(cls, v):
        if not re.match(r'^[^@]+@[^@]+\.[^@]+$', v):
            raise ValueError('Email inválido')
        return v
    
    @validator('password')
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Senha deve ter pelo menos 8 caracteres')
        return v
```

#### **SQL Injection Prevention**
```python
# Sempre usar ORM ou prepared statements
async def get_user_by_id(user_id: int) -> User:
    # ✅ Seguro - usando ORM
    return await db.query(User).filter(User.id == user_id).first()
    
    # ❌ Inseguro - concatenação de strings
    # query = f"SELECT * FROM users WHERE id = {user_id}"
```

---

## ⚙️ Configurações de Segurança

### **Headers de Segurança**

#### **Middleware de Security Headers**
```python
security_headers = {
    "X-Frame-Options": "DENY",
    "X-Content-Type-Options": "nosniff",
    "X-XSS-Protection": "1; mode=block",
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
    "Content-Security-Policy": "default-src 'self'",
    "Referrer-Policy": "strict-origin-when-cross-origin"
}
```

### **CORS Configuration**

#### **Configuração Restritiva**
```python
# Produção
CORS_ORIGINS = [
    "https://your-domain.com",
    "https://admin.your-domain.com"
]

# Desenvolvimento
CORS_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:8501"
]
```

### **Environment Variables**

#### **Configurações Críticas**
```env
# NUNCA commitar essas chaves
SECRET_KEY=sua-chave-secreta-256-bits
DATABASE_URL=postgresql://user:pass@localhost/db
REDIS_PASSWORD=redis-password-forte

# OAuth Secrets
GOOGLE_CLIENT_SECRET=seu-google-secret
MICROSOFT_CLIENT_SECRET=seu-microsoft-secret
GITHUB_CLIENT_SECRET=seu-github-secret

# 2FA Encryption Key
TOTP_ENCRYPTION_KEY=sua-chave-fernet-32-bytes
```

---

## 📊 Monitoramento e Alertas

### **Logs de Segurança**

#### **Eventos Monitorados**
```python
SECURITY_EVENTS = [
    "login_success",
    "login_failure", 
    "2fa_enabled",
    "2fa_disabled",
    "permission_denied",
    "rate_limit_exceeded",
    "suspicious_activity",
    "admin_action"
]
```

#### **Estrutura de Logs**
```json
{
  "timestamp": "2024-01-20T10:00:00Z",
  "event_type": "login_failure",
  "user_id": 123,
  "ip_address": "192.168.1.100",
  "user_agent": "Mozilla/5.0...",
  "details": {
    "reason": "invalid_password",
    "attempts": 3
  }
}
```

### **Alertas Automáticos**

#### **Condições de Alerta**
```python
ALERT_CONDITIONS = {
    "multiple_failed_logins": {
        "threshold": 5,
        "window": 300,  # 5 minutos
        "severity": "HIGH"
    },
    "admin_actions": {
        "threshold": 10,
        "window": 3600,  # 1 hora
        "severity": "MEDIUM"
    },
    "rate_limit_exceeded": {
        "threshold": 100,
        "window": 60,
        "severity": "MEDIUM"
    }
}
```

---

## 📋 Boas Práticas

### **Desenvolvimento Seguro**

#### **Checklist de Segurança**
- [ ] **Validação de Input**: Todos os inputs validados
- [ ] **Sanitização**: Dados sanitizados antes do uso
- [ ] **Autorização**: Verificação de permissões em todos endpoints
- [ ] **Logs**: Eventos importantes logados
- [ ] **Secrets**: Nunca hardcodados no código
- [ ] **Dependencies**: Dependências atualizadas
- [ ] **Tests**: Testes de segurança implementados

#### **Code Review**
```python
# ✅ Boas práticas
async def create_user(user_data: UserCreate, current_user: User = Depends(get_current_user)):
    # Verificar permissão
    if not await check_permission("users:create", current_user):
        raise HTTPException(403, "Permissão negada")
    
    # Validar e escopar a criação para o tenant do usuário
    if not user_data.tenant_id:
        user_data.tenant_id = current_user.tenant_id

    if user_data.tenant_id != current_user.tenant_id and not current_user.is_superadmin:
        raise HTTPException(403, "Você só pode criar usuários no seu próprio tenant.")
    
    # Hash da senha
    validated_data = user_data.dict()
    validated_data["password"] = hash_password(validated_data["password"])
    
    # Criar usuário
    user = await db.create_user(validated_data)
    
    # Log da ação
    await log_security_event("user_created", current_user.id, {"new_user_id": user.id})
    
    return user
```

### **Configuração de Produção**

#### **Checklist de Deploy**
- [ ] **HTTPS**: Certificado SSL válido
- [ ] **Firewall**: Portas desnecessárias fechadas
- [ ] **Secrets**: Variáveis de ambiente seguras
- [ ] **Monitoring**: Sistema de monitoramento ativo
- [ ] **Backups**: Backups automáticos configurados
- [ ] **Updates**: Sistema de updates automáticos
- [ ] **Logs**: Logs centralizados e seguros

---

## 🔍 Auditoria e Compliance

### **Logs de Auditoria**

#### **Eventos Auditados**
```python
AUDIT_EVENTS = [
    "user_created",
    "user_updated", 
    "user_deleted",
    "role_assigned",
    "role_removed",
    "permission_granted",
    "permission_revoked",
    "2fa_enabled",
    "2fa_disabled",
    "admin_login",
    "data_export"
]
```

#### **Retenção de Logs**
```python
LOG_RETENTION = {
    "security_logs": 365,  # 1 ano
    "audit_logs": 2555,    # 7 anos
    "access_logs": 90,     # 3 meses
    "error_logs": 30       # 1 mês
}
```

### **Compliance**

#### **LGPD/GDPR**
- **Consentimento**: Registro de consentimentos
- **Portabilidade**: Exportação de dados do usuário
- **Esquecimento**: Exclusão completa de dados
- **Transparência**: Logs de acesso aos dados

#### **SOC 2**
- **Controles de Acesso**: RBAC implementado
- **Monitoramento**: Logs completos
- **Backup**: Backups automáticos
- **Incident Response**: Plano de resposta

---

## 🚨 Resposta a Incidentes

### **Procedimentos de Emergência**

#### **Compromisso de Conta**
1. **Detectar**: Monitoramento automático
2. **Bloquear**: Suspender conta imediatamente
3. **Investigar**: Análise de logs
4. **Notificar**: Usuário e administradores
5. **Remediar**: Resetar credenciais
6. **Monitorar**: Acompanhar atividade

#### **Ataque DDoS**
1. **Detectar**: Rate limiting triggering
2. **Mitigar**: Ativar proteções adicionais
3. **Bloquear**: IPs maliciosos
4. **Escalar**: Recursos adicionais
5. **Comunicar**: Stakeholders

### **Contatos de Emergência**

#### **Equipe de Segurança**
- **Security Lead**: security@your-domain.com
- **DevOps**: devops@your-domain.com
- **Legal**: legal@your-domain.com

#### **Procedimentos**
1. **Identificar** o tipo de incidente
2. **Classificar** a severidade
3. **Notificar** as pessoas apropriadas
4. **Documentar** todas as ações
5. **Investigar** e remediar
6. **Fazer** post-mortem

---

## 🎯 Métricas de Segurança

### **KPIs de Segurança**

#### **Métricas Principais**
- **Failed Login Rate**: < 5%
- **2FA Adoption**: > 80%
- **Vulnerability Response Time**: < 24h
- **Incident Response Time**: < 1h
- **Security Training Completion**: 100%

#### **Monitoramento**
```python
SECURITY_METRICS = {
    "failed_logins": {
        "current": 127,
        "threshold": 200,
        "trend": "decreasing"
    },
    "2fa_adoption": {
        "current": 85.5,
        "target": 90.0,
        "trend": "increasing"
    },
    "active_sessions": {
        "current": 1250,
        "max": 2000,
        "trend": "stable"
    }
}
```

---

## 🔐 Conclusão

O sistema FastAPI RBAC Enterprise implementa **múltiplas camadas de segurança** para proteger contra:

- **Ataques de autenticação**: 2FA, rate limiting, account lockout
- **Ataques de autorização**: RBAC granular, verificação de permissões
- **Ataques de rede**: DDoS protection, circuit breaker
- **Ataques de dados**: Criptografia, sanitização, SQL injection prevention
- **Ataques de sessão**: Secure tokens, session management

### **Benefícios**
- ✅ **Segurança Enterprise**: Múltiplas camadas de proteção
- ✅ **Compliance**: Conformidade com regulamentações
- ✅ **Auditoria**: Logs completos para auditoria
- ✅ **Monitoramento**: Detecção em tempo real
- ✅ **Resposta**: Procedimentos de resposta a incidentes

---

**FastAPI RBAC Enterprise** - Segurança de Nível Empresarial 🔒 