# FastAPI RBAC - Sistema de Autenticação e Autorização

Uma aplicação FastAPI completa com sistema RBAC (Role-Based Access Control) e múltiplos provedores de autenticação.

## 🚀 Características

- ✅ **Autenticação Múltipla**: Suporte a login básico (username/password) e OAuth2
- ✅ **Provedores OAuth**: Google, Microsoft, GitHub
- ✅ **Sistema RBAC**: Controle de acesso baseado em roles e permissões
- ✅ **JWT Tokens**: Autenticação via tokens JWT
- ✅ **SQLAlchemy ORM**: Integração com banco de dados SQLite
- ✅ **FastAPI**: API moderna e documentação automática
- ✅ **UV Package Manager**: Gerenciamento de dependências com UV

## 📋 Pré-requisitos

- Python 3.9+
- UV (gerenciador de pacotes)

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
# Database
DATABASE_URL=sqlite:///./app.db

# JWT
SECRET_KEY=sua-chave-secreta-aqui
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

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
- **Permissões padrão**: users:*, roles:*, permissions:*, posts:*, settings:*
- **Roles padrão**: admin, manager, editor, viewer
- **Usuário admin**: username=`admin`, password=`admin123`

## 🚀 Execução

**Inicie o servidor de desenvolvimento**:
```bash
uv run task dev
```

A aplicação estará disponível em: `http://localhost:8000`

## 📚 Documentação da API

- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

## 🔐 Endpoints Principais

### Autenticação Básica
- `POST /auth/register` - Registrar novo usuário
- `POST /auth/login` - Login com username/password
- `POST /auth/token` - Endpoint OAuth2 compatível
- `GET /auth/me` - Perfil do usuário atual

### OAuth
- `GET /oauth/{provider}/login` - Iniciar login OAuth (google|microsoft|github)
- `GET /oauth/{provider}/callback` - Callback OAuth
- `GET /oauth/providers` - Listar provedores configurados

### Administração (requer permissões)
- `GET /admin/users` - Listar usuários
- `POST /admin/roles` - Criar role
- `POST /admin/permissions` - Criar permissão
- `POST /admin/users/{id}/roles/{role_id}` - Atribuir role a usuário

### Rotas Protegidas (exemplos)
- `GET /protected/profile` - Perfil (requer autenticação)
- `GET /protected/admin-only` - Acesso restrito a admins
- `GET /protected/read-posts` - Requer permissão `posts:read`
- `POST /protected/create-post` - Requer permissão `posts:create`

## 🎭 Sistema RBAC

### Roles Padrão

| Role | Descrição | Permissões |
|------|-----------|------------|
| **admin** | Administrador completo | Todas as permissões |
| **manager** | Gerente com acesso limitado | users:read/update, posts:*, settings:read |
| **editor** | Editor de conteúdo | posts:create/read/update |
| **viewer** | Apenas visualização | posts:read |

### Permissões Padrão

- **users:** create, read, update, delete
- **roles:** create, read, update, delete  
- **permissions:** create, read, update, delete
- **posts:** create, read, update, delete
- **settings:** read, update

## 🔒 Exemplos de Uso

### 1. Registro e Login

```bash
# Registrar usuário
curl -X POST "http://localhost:8000/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "usuario",
    "email": "usuario@example.com",
    "password": "senha123",
    "full_name": "Nome Completo"
  }'

# Login
curl -X POST "http://localhost:8000/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "usuario", 
    "password": "senha123"
  }'
```

### 2. Usar Token de Acesso

```bash
# Usar o token retornado no header Authorization
curl -X GET "http://localhost:8000/protected/profile" \
  -H "Authorization: Bearer SEU_TOKEN_AQUI"
```

### 3. Login Admin

```bash
# Login como admin (criado na inicialização)
curl -X POST "http://localhost:8000/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "password": "admin123"
  }'
```

## 🔧 Configuração OAuth

### Google OAuth

1. Acesse o [Google Cloud Console](https://console.cloud.google.com/)
2. Crie um projeto e habilite a Google+ API
3. Configure OAuth 2.0 credentials
4. Adicione `http://localhost:8000/oauth/google/callback` como redirect URI
5. Configure no `.env`: `GOOGLE_CLIENT_ID` e `GOOGLE_CLIENT_SECRET`

### Microsoft OAuth

1. Acesse o [Azure Portal](https://portal.azure.com/)
2. Registre uma aplicação no Azure AD
3. Configure redirect URI: `http://localhost:8000/oauth/microsoft/callback`
4. Configure no `.env`: `MICROSOFT_CLIENT_ID` e `MICROSOFT_CLIENT_SECRET`

### GitHub OAuth

1. Acesse GitHub Settings > Developer settings > OAuth Apps
2. Crie uma nova OAuth App
3. Configure Authorization callback URL: `http://localhost:8000/oauth/github/callback`
4. Configure no `.env`: `GITHUB_CLIENT_ID` e `GITHUB_CLIENT_SECRET`

## 🛠️ Comandos Úteis

```bash
# Executar aplicação em desenvolvimento
uv run task dev

# Inicializar banco de dados
uv run task init-db

# Executar testes
uv run task test

# Formatar código
uv run task format

# Verificar código
uv run task lint
```

## 📁 Estrutura do Projeto

```
fast-rbac/
├── app/
│   ├── auth/           # Módulos de autenticação
│   ├── config/         # Configurações
│   ├── database/       # Configuração do banco
│   ├── middleware/     # Middleware RBAC
│   ├── models/         # Modelos e schemas
│   ├── routes/         # Rotas da API
│   └── main.py         # Aplicação principal
├── pyproject.toml      # Configuração UV
├── env.example         # Exemplo de variáveis
└── README.md
```

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