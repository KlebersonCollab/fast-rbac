# 📚 API Reference - FastAPI RBAC Enterprise

Documentação técnica completa da API do sistema FastAPI RBAC Enterprise com autenticação 2FA, cache Redis, rate limiting e controle de acesso avançado.

## 📋 Sumário

1. [Autenticação](#autenticação)
2. [Endpoints de Autenticação](#endpoints-de-autenticação)
3. [Endpoints 2FA](#endpoints-2fa)
4. [Endpoints OAuth](#endpoints-oauth)
5. [Endpoints Protegidos](#endpoints-protegidos)
6. [Endpoints de Administração](#endpoints-de-administração)
7. [Endpoints de Cache](#endpoints-de-cache)
8. [Schemas](#schemas)
9. [Códigos de Erro](#códigos-de-erro)
10. [Rate Limiting](#rate-limiting)
11. [Exemplos de Uso](#exemplos-de-uso)

---

## 🔐 Autenticação

### **Tipos de Autenticação**

1. **JWT Bearer Token**: Padrão para API
2. **2FA TOTP**: Autenticação de dois fatores
3. **OAuth2**: Google, Microsoft, GitHub

### **Headers Obrigatórios**

```http
Authorization: Bearer <jwt_token>
Content-Type: application/json
```

### **Permissões**

Sistema baseado em permissões granulares:

```
users:create, users:read, users:update, users:delete, users:superadmin
roles:create, roles:read, roles:update, roles:delete
permissions:create, permissions:read, permissions:update, permissions:delete
posts:create, posts:read, posts:update, posts:delete
settings:read, settings:update
logs:view
superadmin:manage
```

---

## 🔑 Endpoints de Autenticação

### **POST /auth/register**
Registrar novo usuário

**Request:**
```json
{
  "username": "novousuario",
  "email": "usuario@example.com",
  "password": "senha123",
  "full_name": "Nome Completo"
}
```

**Response:**
```json
{
  "id": 1,
  "username": "novousuario",
  "email": "usuario@example.com",
  "full_name": "Nome Completo",
  "is_active": true,
  "created_at": "2024-01-20T10:00:00"
}
```

### **POST /auth/login**
Fazer login

**Request:**
```json
{
  "username": "admin",
  "password": "admin123"
}
```

**Response:**
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "token_type": "bearer",
  "expires_in": 1800,
  "user": {
    "id": 1,
    "username": "admin",
    "email": "admin@example.com",
    "is_2fa_enabled": false
  }
}
```

### **GET /auth/me**
Obter perfil do usuário atual

**Headers:**
```http
Authorization: Bearer <token>
```

**Response:**
```json
{
  "id": 1,
  "username": "admin",
  "email": "admin@example.com",
  "full_name": "Administrator",
  "is_active": true,
  "is_2fa_enabled": false,
  "roles": ["superadmin"],
  "permissions": ["superadmin:manage"],
  "created_at": "2024-01-20T10:00:00"
}
```

### **GET /auth/test-token**
Testar validade do token

**Headers:**
```http
Authorization: Bearer <token>
```

**Response:**
```json
{
  "valid": true,
  "user_id": 1,
  "username": "admin",
  "expires_at": "2024-01-20T12:00:00"
}
```

---

## 🔑 Endpoints 2FA

### **GET /auth/2fa/status**
Verificar status do 2FA

**Response:**
```json
{
  "is_enabled": false,
  "has_backup_codes": false,
  "backup_codes_count": 0,
  "setup_required": true
}
```

### **POST /auth/2fa/setup**
Configurar 2FA

**Response:**
```json
{
  "secret": "JBSWY3DPEHPK3PXP",
  "qr_code": "data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjUwIiBoZWlnaHQ9IjI1MCI+...",
  "backup_codes": [
    "12345678",
    "87654321",
    "11223344"
  ],
  "setup_key": "JBSWY3DPEHPK3PXP"
}
```

### **POST /auth/2fa/enable**
Habilitar 2FA

**Request:**
```json
{
  "totp_code": "123456"
}
```

**Response:**
```json
{
  "success": true,
  "message": "2FA habilitado com sucesso",
  "backup_codes": [
    "12345678",
    "87654321"
  ]
}
```

### **POST /auth/2fa/login**
Login com 2FA

**Request:**
```json
{
  "username": "admin",
  "password": "admin123",
  "totp_code": "123456"
}
```

**Response:**
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "token_type": "bearer",
  "expires_in": 1800,
  "user": {
    "id": 1,
    "username": "admin",
    "is_2fa_enabled": true
  }
}
```

### **GET /auth/2fa/qr-code**
Obter QR code para 2FA

**Response:**
```json
{
  "qr_code": "data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjUwIiBoZWlnaHQ9IjI1MCI+...",
  "manual_entry_key": "JBSWY3DPEHPK3PXP"
}
```

### **POST /auth/2fa/regenerate-backup-codes**
Regenerar códigos de backup

**Response:**
```json
{
  "backup_codes": [
    "98765432",
    "13579246",
    "24681357"
  ],
  "count": 3
}
```

---

## 🌐 Endpoints OAuth

### **GET /oauth/providers**
Listar provedores OAuth disponíveis

**Response:**
```json
{
  "providers": [
    {
      "name": "google",
      "display_name": "Google",
      "login_url": "/oauth/google/login"
    },
    {
      "name": "microsoft",
      "display_name": "Microsoft",
      "login_url": "/oauth/microsoft/login"
    },
    {
      "name": "github",
      "display_name": "GitHub",
      "login_url": "/oauth/github/login"
    }
  ]
}
```

### **GET /oauth/{provider}/login**
Iniciar login OAuth

**Parameters:**
- `provider`: google, microsoft, github

**Response:**
```json
{
  "authorization_url": "https://accounts.google.com/oauth/authorize?...",
  "state": "random_state_string"
}
```

### **GET /oauth/{provider}/callback**
Callback OAuth

**Parameters:**
- `code`: Authorization code
- `state`: State parameter

**Response:**
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "token_type": "bearer",
  "user": {
    "id": 1,
    "username": "user@gmail.com",
    "email": "user@gmail.com",
    "provider": "google"
  }
}
```

---

## 🛡️ Endpoints Protegidos

### **GET /protected/profile**
Obter perfil do usuário autenticado

**Permission:** Qualquer usuário autenticado

**Response:**
```json
{
  "id": 1,
  "username": "admin",
  "email": "admin@example.com",
  "full_name": "Administrator",
  "roles": ["superadmin"],
  "permissions": ["superadmin:manage"]
}
```

### **GET /protected/posts**
Listar posts

**Permission:** `posts:read`

**Response:**
```json
{
  "posts": [
    {
      "id": 1,
      "title": "Primeiro Post",
      "content": "Conteúdo do post",
      "author": "admin",
      "created_at": "2024-01-20T10:00:00"
    }
  ],
  "total": 1
}
```

### **POST /protected/posts/create**
Criar novo post

**Permission:** `posts:create`

**Request:**
```json
{
  "title": "Novo Post",
  "content": "Conteúdo do novo post"
}
```

**Response:**
```json
{
  "id": 2,
  "title": "Novo Post",
  "content": "Conteúdo do novo post",
  "author": "admin",
  "created_at": "2024-01-20T10:30:00"
}
```

### **GET /protected/settings**
Acessar configurações

**Permission:** `settings:read`

**Response:**
```json
{
  "app_name": "FastAPI RBAC",
  "version": "1.0.0",
  "environment": "production",
  "features": {
    "2fa_enabled": true,
    "oauth_enabled": true,
    "redis_enabled": true
  }
}
```

---

## 👥 Endpoints de Administração

### **GET /admin/users**
Listar usuários

**Permission:** `users:read`

**Query Parameters:**
- `page`: Página (padrão: 1)
- `size`: Tamanho da página (padrão: 10)
- `search`: Busca por username ou email

**Response:**
```json
{
  "users": [
    {
      "id": 1,
      "username": "admin",
      "email": "admin@example.com",
      "full_name": "Administrator",
      "is_active": true,
      "is_2fa_enabled": false,
      "roles": ["superadmin"],
      "created_at": "2024-01-20T10:00:00"
    }
  ],
  "total": 1,
  "page": 1,
  "size": 10,
  "pages": 1
}
```

### **GET /admin/users/{user_id}**
Obter usuário específico

**Permission:** `users:read`

**Response:**
```json
{
  "id": 1,
  "username": "admin",
  "email": "admin@example.com",
  "full_name": "Administrator",
  "is_active": true,
  "is_2fa_enabled": false,
  "roles": ["superadmin"],
  "permissions": ["superadmin:manage"],
  "created_at": "2024-01-20T10:00:00"
}
```

### **POST /admin/users/{user_id}/roles/{role_id}**
Atribuir role ao usuário

**Permission:** `users:update`

**Response:**
```json
{
  "success": true,
  "message": "Role atribuído com sucesso",
  "user_id": 1,
  "role_id": 2
}
```

### **DELETE /admin/users/{user_id}/roles/{role_id}**
Remover role do usuário

**Permission:** `users:update`

**Response:**
```json
{
  "success": true,
  "message": "Role removido com sucesso",
  "user_id": 1,
  "role_id": 2
}
```

### **POST /admin/users/{user_id}/superadmin**
Tornar usuário superadmin

**Permission:** `superadmin:manage`

**Response:**
```json
{
  "success": true,
  "message": "Usuário promovido a superadmin",
  "user_id": 1
}
```

### **GET /admin/roles**
Listar roles

**Permission:** `roles:read`

**Response:**
```json
{
  "roles": [
    {
      "id": 1,
      "name": "superadmin",
      "description": "Super administrador",
      "permissions": ["superadmin:manage"],
      "user_count": 1
    }
  ],
  "total": 1
}
```

### **POST /admin/roles**
Criar role

**Permission:** `roles:create`

**Request:**
```json
{
  "name": "custom_role",
  "description": "Role personalizada",
  "permissions": ["users:read", "posts:read"]
}
```

**Response:**
```json
{
  "id": 6,
  "name": "custom_role",
  "description": "Role personalizada",
  "permissions": ["users:read", "posts:read"],
  "created_at": "2024-01-20T10:00:00"
}
```

### **PUT /admin/roles/{role_id}**
Atualizar role

**Permission:** `roles:update`

**Request:**
```json
{
  "name": "updated_role",
  "description": "Role atualizada",
  "permissions": ["users:read", "posts:read", "posts:create"]
}
```

### **DELETE /admin/roles/{role_id}**
Excluir role

**Permission:** `roles:delete`

**Response:**
```json
{
  "success": true,
  "message": "Role excluído com sucesso"
}
```

### **GET /admin/permissions**
Listar permissões

**Permission:** `permissions:read`

**Response:**
```json
{
  "permissions": [
    {
      "id": 1,
      "name": "users:read",
      "description": "Ler usuários",
      "resource": "users",
      "action": "read"
    }
  ],
  "total": 22
}
```

### **POST /admin/permissions**
Criar permissão

**Permission:** `permissions:create`

**Request:**
```json
{
  "name": "custom:action",
  "description": "Ação personalizada",
  "resource": "custom",
  "action": "action"
}
```

---

## 📊 Endpoints de Cache

### **GET /cache/health**
Health check do Redis

**Response:**
```json
{
  "redis_status": "connected",
  "ping": "pong",
  "info": {
    "version": "7.0.0",
    "uptime": "123456",
    "memory_usage": "2.5MB"
  }
}
```

### **GET /cache/stats**
Estatísticas do cache

**Permission:** `admin` ou `superadmin`

**Response:**
```json
{
  "cache_stats": {
    "hits": 1250,
    "misses": 150,
    "hit_rate": 89.3,
    "total_keys": 45
  },
  "performance_stats": {
    "avg_response_time": 2.5,
    "permissions_cache_hits": 95.2,
    "users_cache_hits": 87.1
  },
  "rate_limiting": {
    "total_requests": 5000,
    "blocked_requests": 12,
    "block_rate": 0.24
  }
}
```

### **POST /cache/clear**
Limpar cache

**Permission:** `admin` ou `superadmin`

**Request:**
```json
{
  "type": "all"
}
```

**Types disponíveis:**
- `all`: Limpar todo o cache
- `permissions`: Limpar cache de permissões
- `users`: Limpar cache de usuários
- `sessions`: Limpar cache de sessões

**Response:**
```json
{
  "success": true,
  "message": "Cache limpo com sucesso",
  "keys_deleted": 45
}
```

### **GET /cache/keys**
Listar chaves do cache

**Permission:** `admin` ou `superadmin`

**Query Parameters:**
- `pattern`: Padrão para busca (ex: "user:*")
- `limit`: Limite de chaves (padrão: 100)

**Response:**
```json
{
  "keys": [
    "user:1:permissions",
    "user:1:data",
    "session:abc123"
  ],
  "total": 3,
  "pattern": "user:*"
}
```

### **POST /cache/test**
Testar performance do cache

**Permission:** `admin` ou `superadmin`

**Query Parameters:**
- `iterations`: Número de iterações (padrão: 1000)

**Response:**
```json
{
  "test_results": {
    "iterations": 1000,
    "total_time": 250.5,
    "avg_time_per_operation": 0.25,
    "operations_per_second": 4000,
    "cache_hit_rate": 92.5
  }
}
```

---

## 📋 Schemas

### **User**
```json
{
  "id": "integer",
  "username": "string",
  "email": "string",
  "full_name": "string",
  "is_active": "boolean",
  "is_2fa_enabled": "boolean",
  "roles": ["string"],
  "permissions": ["string"],
  "created_at": "datetime",
  "updated_at": "datetime"
}
```

### **Role**
```json
{
  "id": "integer",
  "name": "string",
  "description": "string",
  "permissions": ["string"],
  "user_count": "integer",
  "created_at": "datetime"
}
```

### **Permission**
```json
{
  "id": "integer",
  "name": "string",
  "description": "string",
  "resource": "string",
  "action": "string",
  "created_at": "datetime"
}
```

### **Token**
```json
{
  "access_token": "string",
  "refresh_token": "string",
  "token_type": "bearer",
  "expires_in": "integer",
  "user": "User"
}
```

---

## ⚠️ Códigos de Erro

### **400 Bad Request**
```json
{
  "detail": "Dados inválidos",
  "errors": {
    "username": ["Campo obrigatório"],
    "email": ["Formato inválido"]
  }
}
```

### **401 Unauthorized**
```json
{
  "detail": "Token inválido ou expirado"
}
```

### **403 Forbidden**
```json
{
  "detail": "Permissão insuficiente para acessar este recurso"
}
```

### **404 Not Found**
```json
{
  "detail": "Recurso não encontrado"
}
```

### **422 Validation Error**
```json
{
  "detail": [
    {
      "loc": ["body", "username"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

### **429 Too Many Requests**
```json
{
  "detail": "Rate limit exceeded. Try again later.",
  "retry_after": 60
}
```

### **500 Internal Server Error**
```json
{
  "detail": "Erro interno do servidor"
}
```

---

## 🚦 Rate Limiting

### **Limites por Endpoint**

| Endpoint | Limite | Janela |
|----------|---------|---------|
| `/auth/login` | 5 req | 5 min |
| `/auth/register` | 3 req | 5 min |
| `/auth/*` | 10 req | 1 min |
| `/oauth/*` | 20 req | 1 min |
| `/admin/*` | 50 req | 1 min |
| `/api/*` | 1000 req | 1 min |
| **Default** | 100 req | 1 min |

### **Headers de Rate Limiting**

```http
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1640995200
X-RateLimit-Retry-After: 60
```

---

## 💡 Exemplos de Uso

### **Login Completo**

```bash
# 1. Login básico
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}'

# 2. Usar token nas requisições
curl -X GET http://localhost:8000/auth/me \
  -H "Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."

# 3. Login com 2FA (se habilitado)
curl -X POST http://localhost:8000/auth/2fa/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123","totp_code":"123456"}'
```

### **Configurar 2FA**

```bash
# 1. Verificar status
curl -X GET http://localhost:8000/auth/2fa/status \
  -H "Authorization: Bearer <token>"

# 2. Configurar 2FA
curl -X POST http://localhost:8000/auth/2fa/setup \
  -H "Authorization: Bearer <token>"

# 3. Habilitar 2FA
curl -X POST http://localhost:8000/auth/2fa/enable \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"totp_code":"123456"}'
```

### **Gerenciar Usuários**

```bash
# 1. Listar usuários
curl -X GET http://localhost:8000/admin/users \
  -H "Authorization: Bearer <token>"

# 2. Atribuir role
curl -X POST http://localhost:8000/admin/users/1/roles/2 \
  -H "Authorization: Bearer <token>"

# 3. Criar role personalizada
curl -X POST http://localhost:8000/admin/roles \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"name":"custom_role","description":"Role personalizada","permissions":["users:read"]}'
```

### **Monitorar Cache**

```bash
# 1. Verificar health do Redis
curl -X GET http://localhost:8000/cache/health

# 2. Estatísticas de cache
curl -X GET http://localhost:8000/cache/stats \
  -H "Authorization: Bearer <token>"

# 3. Testar performance
curl -X POST http://localhost:8000/cache/test?iterations=1000 \
  -H "Authorization: Bearer <token>"
```

---

## 🔧 Configuração do Cliente

### **Python (httpx)**

```python
import httpx

class RBACClient:
    def __init__(self, base_url="http://localhost:8000", token=None):
        self.base_url = base_url
        self.token = token
        self.client = httpx.Client(base_url=base_url)
    
    def login(self, username, password):
        response = self.client.post("/auth/login", json={
            "username": username,
            "password": password
        })
        if response.status_code == 200:
            data = response.json()
            self.token = data["access_token"]
            return data
        return None
    
    def get_headers(self):
        if self.token:
            return {"Authorization": f"Bearer {self.token}"}
        return {}
    
    def get_users(self):
        response = self.client.get("/admin/users", headers=self.get_headers())
        return response.json()
    
    def enable_2fa(self, totp_code):
        response = self.client.post("/auth/2fa/enable", 
                                  json={"totp_code": totp_code},
                                  headers=self.get_headers())
        return response.json()

# Uso
client = RBACClient()
client.login("admin", "admin123")
users = client.get_users()
```

### **JavaScript (fetch)**

```javascript
class RBACClient {
  constructor(baseUrl = 'http://localhost:8000', token = null) {
    this.baseUrl = baseUrl;
    this.token = token;
  }
  
  async login(username, password) {
    const response = await fetch(`${this.baseUrl}/auth/login`, {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({username, password})
    });
    
    if (response.ok) {
      const data = await response.json();
      this.token = data.access_token;
      return data;
    }
    return null;
  }
  
  getHeaders() {
    return this.token ? 
      {'Authorization': `Bearer ${this.token}`} : 
      {};
  }
  
  async getUsers() {
    const response = await fetch(`${this.baseUrl}/admin/users`, {
      headers: this.getHeaders()
    });
    return response.json();
  }
  
  async enable2FA(totpCode) {
    const response = await fetch(`${this.baseUrl}/auth/2fa/enable`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...this.getHeaders()
      },
      body: JSON.stringify({totp_code: totpCode})
    });
    return response.json();
  }
}

// Uso
const client = new RBACClient();
await client.login('admin', 'admin123');
const users = await client.getUsers();
```

---

**FastAPI RBAC Enterprise API** - Documentação Técnica Completa 🚀 