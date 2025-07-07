# FastAPI RBAC - Sistema de Autenticação e Autorização

Uma aplicação FastAPI completa com sistema RBAC (Role-Based Access Control), múltiplos provedores de autenticação e recursos enterprise de performance e segurança.

## 🚀 Características

### 🔐 **Autenticação & Autorização**
- ✅ **Autenticação Múltipla**: Login básico (username/password) e OAuth2
- ✅ **Provedores OAuth**: Google, Microsoft, GitHub
- ✅ **Sistema RBAC**: Controle de acesso baseado em roles e permissões
- ✅ **JWT Tokens**: Autenticação segura via tokens JWT
- ✅ **Hierarquia Superadmin**: Sistema de super usuários

### ⚡ **Performance & Cache (NÍVEL 2)**
- ✅ **Redis Integration**: Cache distribuído e sessions
- ✅ **Permission Caching**: Cache inteligente de permissões (TTL: 30min)
- ✅ **User Data Caching**: Cache de dados de usuário (TTL: 15min)
- ✅ **Session Management**: Sessions distribuídos com Redis
- ✅ **Query Result Caching**: Cache de resultados de consultas
- ✅ **Connection Pooling**: Pool de conexões otimizado

### 🛡️ **Segurança & Rate Limiting**
- ✅ **Advanced Rate Limiting**: Rate limiting inteligente por endpoint
- ✅ **Adaptive Rate Limiting**: Ajusta limites baseado na carga do sistema
- ✅ **Circuit Breaker Pattern**: Proteção contra cascading failures
- ✅ **Multi-Level Protection**: Rate limiting por usuário, IP e endpoint
- ✅ **Security Middleware**: TrustedHost, GZIP, CORS configuráveis

### 🖥️ **Interface & Monitoring**
- ✅ **Frontend Administrativo**: Interface Streamlit completa
- ✅ **Dashboard Interativo**: Métricas em tempo real
- ✅ **Cache Monitoring**: Endpoints de monitoramento de cache
- ✅ **Performance Testing**: Testes de performance integrados
- ✅ **Health Checks**: Monitoramento de saúde do sistema

### 🗄️ **Database & Infrastructure**
- ✅ **SQLAlchemy ORM**: PostgreSQL/SQLite support
- ✅ **Alembic Migrations**: Sistema de migração de banco
- ✅ **Docker Support**: Containerização completa
- ✅ **Production Ready**: Configurações para produção

## 📋 Pré-requisitos

- Python 3.11+
- UV (gerenciador de pacotes)
- Redis (opcional, para cache distribuído)
- PostgreSQL (opcional, para produção)

## 🛠️ Instalação

1. **Clone o repositório**:
```bash
git clone <repositorio>
cd fast-rbac
```

2. **Instale as dependências**:
```bash
uv sync
```

3. **Configure as variáveis de ambiente**:
```bash
cp env.example .env
```

4. **Edite o arquivo `.env`** com suas configurações:
```env
# Application
ENVIRONMENT=development
DEBUG=true
SECRET_KEY=sua-chave-secreta-aqui

# Database
DATABASE_URL=sqlite:///./app.db
# DATABASE_URL=postgresql://user:pass@localhost:5432/rbac_db

# Redis (Performance)
REDIS_ENABLED=false
REDIS_URL=redis://localhost:6379/0

# Rate Limiting
RATE_LIMIT_ENABLED=true
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_WINDOW=60

# OAuth Providers (opcional)
GOOGLE_CLIENT_ID=seu-google-client-id
GOOGLE_CLIENT_SECRET=seu-google-client-secret
MICROSOFT_CLIENT_ID=seu-microsoft-client-id
MICROSOFT_CLIENT_SECRET=seu-microsoft-client-secret
GITHUB_CLIENT_ID=seu-github-client-id
GITHUB_CLIENT_SECRET=seu-github-client-secret
```

## 🗄️ Inicialização do Banco de Dados

**Inicialize o banco de dados com dados padrão**:
```bash
uv run task init-db
```

Isso criará:
- **Permissões padrão**: users:*, roles:*, permissions:*, posts:*, settings:*, logs:view, superadmin:manage
- **Roles padrão**: superadmin, admin, manager, editor, viewer
- **Usuário admin**: username=`admin`, password=`admin123`

## 🚀 Execução

### Desenvolvimento

**Inicie o servidor de desenvolvimento**:
```bash
uv run task dev
```

**Inicie o frontend administrativo**:
```bash
# Em outro terminal
uv run task front
```

### Docker (Recomendado)

**Para desenvolvimento com Redis**:
```bash
uv run task docker-dev
```

**Para produção**:
```bash
uv run task docker-prod
```

### URLs Disponíveis
- **Backend API**: `http://localhost:8000`
- **Frontend Admin**: `http://localhost:8501`
- **API Docs**: `http://localhost:8000/docs`
- **Redis Monitor**: `http://localhost:8000/cache/stats` (requer admin)

## 📊 Performance & Monitoring

### Cache Statistics
```bash
# Estatísticas de cache (requer token de admin)
curl -H "Authorization: Bearer TOKEN" http://localhost:8000/cache/stats

# Health check do cache
curl http://localhost:8000/cache/health

# Teste de performance
curl -X POST -H "Authorization: Bearer TOKEN" \
  "http://localhost:8000/cache/test?iterations=1000"
```

### Rate Limiting Headers
Todas as respostas incluem headers de rate limiting:
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1640995200
```

### Performance Benchmarks
Com Redis habilitado:
- **Permission Checks**: ~2ms (vs 50ms database)
- **User Data**: ~1ms (vs 25ms database)
- **Cache Hit Rate**: >90% para permissões
- **Rate Limiting**: ~0.5ms overhead

## 🔐 Endpoints Principais

### Autenticação Básica
- `POST /auth/register` - Registrar novo usuário
- `POST /auth/login` - Login com username/password  
- `POST /auth/token` - Endpoint OAuth2 compatível
- `GET /auth/me` - Perfil do usuário atual
- `POST /auth/refresh` - Renovar token de acesso

### OAuth
- `GET /oauth/{provider}/login` - Iniciar login OAuth
- `GET /oauth/{provider}/callback` - Callback OAuth
- `GET /oauth/providers` - Listar provedores configurados

### Administração (requer permissões)
- `GET /admin/users` - Listar usuários
- `POST /admin/roles` - Criar role
- `POST /admin/permissions` - Criar permissão
- `POST /admin/users/{id}/roles/{role_id}` - Atribuir role

### Cache & Monitoring (admin only)
- `GET /cache/stats` - Estatísticas de cache
- `GET /cache/health` - Health check do Redis
- `POST /cache/clear` - Limpar cache
- `GET /cache/keys` - Listar chaves de cache
- `POST /cache/test` - Teste de performance

### Sistema Info
- `GET /health` - Health check geral
- `GET /info` - Informações do sistema (dev only)

## 🎭 Sistema RBAC

### Roles Padrão

| Role | Descrição | Permissões |
|------|-----------|------------|
| **superadmin** | Super administrador | Todas + superadmin:manage |
| **admin** | Administrador completo | Todas as permissões exceto superadmin |
| **manager** | Gerente com acesso limitado | users:read/update, posts:*, settings:read, logs:view |
| **editor** | Editor de conteúdo | posts:create/read/update |
| **viewer** | Apenas visualização | posts:read |

### Permissões Disponíveis

#### Básicas
- **users:** create, read, update, delete, superadmin
- **roles:** create, read, update, delete
- **permissions:** create, read, update, delete
- **posts:** create, read, update, delete
- **settings:** read, update

#### Sistema
- **logs:** view
- **superadmin:** manage
- **system:** admin

### Cache de Permissões
O sistema utiliza cache inteligente para permissões:
- **TTL**: 30 minutos para permissões, 15 minutos para dados de usuário
- **Invalidação**: Automática quando permissões são alteradas
- **Fallback**: Database quando Redis indisponível
- **Performance**: 95%+ cache hit rate

## 🔒 Rate Limiting

### Limites por Endpoint

| Endpoint | Limite | Janela |
|----------|--------|---------|
| `/auth/login` | 5 tentativas | 5 minutos |
| `/auth/register` | 3 tentativas | 5 minutos |
| `/auth/*` | 10 requests | 1 minuto |
| `/oauth/*` | 20 requests | 1 minuto |
| `/admin/*` | 50 requests | 1 minuto |
| `/api/*` (read) | 1000 requests | 1 minuto |
| `/api/*` (write) | 100 requests | 1 minuto |
| **Default** | 100 requests | 1 minuto |

### Rate Limiting Adaptativo
- **Carga Normal**: Limites padrão
- **Carga Alta (60%+ memory)**: Limites reduzidos em 30%
- **Carga Crítica (80%+ memory)**: Limites reduzidos em 50%
- **Circuit Breaker**: Proteção automática contra falhas em cascata

## 🔧 Configuração Redis

### Desenvolvimento
```env
REDIS_ENABLED=true
REDIS_URL=redis://localhost:6379/0
```

### Docker
```yaml
services:
  redis:
    image: redis:7-alpine
    ports: ["6379:6379"]
    volumes: ["redis_data:/data"]
```

### Produção
```env
REDIS_ENABLED=true
REDIS_URL=redis://redis-server:6379/0
REDIS_MAX_CONNECTIONS=100
```

## 🚀 Deploy em Produção

Ver documentação completa em [DEPLOYMENT.md](./DEPLOYMENT.md)

### Docker Compose
```bash
# Build e deploy
uv run task docker-prod

# Com PostgreSQL e Redis
docker-compose -f docker-compose.prod.yml up -d
```

### Variáveis de Produção
```env
ENVIRONMENT=production
DEBUG=false
DATABASE_URL=postgresql://user:pass@postgres:5432/rbac_prod
REDIS_ENABLED=true
REDIS_URL=redis://redis:6379/0
SECRET_KEY=super-secret-production-key
```

## 🔧 Tasks Disponíveis

```bash
# Desenvolvimento
uv run task dev          # Servidor backend
uv run task front        # Frontend Streamlit  
uv run task init-db      # Inicializar banco

# Docker
uv run task docker-dev   # Docker desenvolvimento
uv run task docker-prod  # Docker produção
uv run task docker-build # Build das imagens

# Database
uv run task migrate      # Executar migrações
uv run task create-migration  # Criar nova migração

# Produção
uv run task prod         # Servidor produção
```

## 📈 Roadmap

### ✅ NÍVEL 1 - PRODUÇÃO READY
- Configurações avançadas
- PostgreSQL + Redis support
- Docker + docker-compose
- Security hardening
- Health checks e monitoring

### ✅ NÍVEL 2 - PERFORMANCE
- Redis cache distribuído
- Rate limiting inteligente
- Connection pooling
- Cache de permissões
- Performance monitoring

### 🚧 NÍVEL 3 - FEATURES AVANÇADAS (Em Desenvolvimento)
- 🔐 2FA (TOTP)
- 🔑 API Keys para integrações
- 🔗 Sistema de webhooks
- 📦 Operações em lote
- 📄 Templates de roles

### 🔮 NÍVEL 4 - IA INTEGRATION
- 🤖 Detecção de anomalias com ML
- 🧠 Sugestões inteligentes de permissões
- ⚙️ Auto-provisioning de usuários
- 📈 Relatórios inteligentes

### 🏢 NÍVEL 5 - ENTERPRISE
- 🔗 SAML/SSO integration
- 🏢 Active Directory/LDAP
- 🏢 Multi-tenancy
- 📱 Mobile app
- 🏪 Marketplace de plugins

## 🔍 Testando Permissões

1. **Faça login como admin** para obter acesso completo
2. **Crie novos usuários** via `/auth/register`
3. **Atribua roles** via `/admin/users/{id}/roles/{role_id}`
4. **Teste endpoints protegidos** com diferentes usuários

## 🚨 Segurança

- **Tokens JWT** com expiração configurável
- **Senhas hash** com bcrypt
- **Validação de permissões** em todas as rotas protegidas
- **CORS configurado** (ajuste para produção)
- **Middleware de sessão** para OAuth

## 🤝 Contribuição

1. Fork o projeto
2. Crie uma branch para sua feature
3. Commit suas mudanças
4. Push para a branch
5. Abra um Pull Request

## 📄 Licença

Este projeto está sob a licença MIT. Veja o arquivo LICENSE para detalhes.

---

**Desenvolvido com ❤️ usando FastAPI e UV** 