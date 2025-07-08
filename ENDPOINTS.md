# Estrutura de Endpoints - FastAPI RBAC

## Endpoints Organizados e Alinhados

### 🔐 **Autenticação (/auth)**
- `POST /auth/register` - Registrar novo usuário
- `POST /auth/login` - Login com usuário e senha
- `GET /auth/me` - Obter perfil do usuário atual
- `GET /auth/test-token` - Testar validade do token

### 🔑 **2FA Authentication (/auth/2fa)**
- `GET /auth/2fa/status` - Status do 2FA
- `POST /auth/2fa/setup` - Configurar 2FA
- `POST /auth/2fa/enable` - Habilitar 2FA
- `POST /auth/2fa/disable` - Desabilitar 2FA
- `POST /auth/2fa/verify` - Verificar código 2FA
- `POST /auth/2fa/login` - Login com 2FA
- `POST /auth/2fa/regenerate-backup-codes` - Regenerar códigos de backup
- `GET /auth/2fa/backup-codes/count` - Contar códigos de backup
- `GET /auth/2fa/qr-code` - Obter QR code
- `POST /auth/2fa/test-backup-code` - Testar código de backup

### 🌐 **OAuth (/oauth)**
- `GET /oauth/providers` - Listar provedores OAuth disponíveis
- `GET /oauth/{provider}/login` - Iniciar login OAuth
- `GET /oauth/{provider}/callback` - Callback OAuth
- `POST /oauth/{provider}/token` - Obter token OAuth

### 🛡️ **Endpoints Protegidos (/protected)**
- `GET /protected/profile` - Perfil do usuário (autenticado)
- `GET /protected/posts` - Listar posts (requer permissão `posts:read`)
- `POST /protected/posts/create` - Criar post (requer permissão `posts:create`)
- `GET /protected/settings` - Acessar configurações (requer permissão `settings:read`)

### 👥 **Administração (/admin)**

#### Usuários
- `GET /admin/users` - Listar usuários
- `GET /admin/users/{user_id}` - Obter usuário específico
- `POST /admin/users/{user_id}/roles/{role_id}` - Atribuir role ao usuário
- `DELETE /admin/users/{user_id}/roles/{role_id}` - Remover role do usuário
- `POST /admin/users/{user_id}/superadmin` - Tornar usuário superadmin
- `DELETE /admin/users/{user_id}/superadmin` - Remover superadmin

#### Roles
- `GET /admin/roles` - Listar roles
- `POST /admin/roles` - Criar role
- `PUT /admin/roles/{role_id}` - Atualizar role
- `DELETE /admin/roles/{role_id}` - Excluir role
- `POST /admin/roles/{role_id}/permissions/{permission_id}` - Atribuir permissão ao role
- `DELETE /admin/roles/{role_id}/permissions/{permission_id}` - Remover permissão do role

#### Permissões
- `GET /admin/permissions` - Listar permissões
- `POST /admin/permissions` - Criar permissão

### 🏢 **Tenants (/tenants)**
- `POST /` - Criar novo tenant
- `GET /` - Listar tenants (próprio ou todos para admin)
- `GET /my` - Obter o tenant do usuário logado
- `GET /{tenant_id}` - Obter tenant específico
- `PUT /{tenant_id}` - Atualizar tenant
- `DELETE /{tenant_id}` - Deletar tenant (admin)
- `POST /{tenant_id}/verify` - Verificar tenant (admin)
- `POST /{tenant_id}/suspend` - Suspender tenant (admin)
- `POST /{tenant_id}/activate` - Ativar tenant (admin)
- `GET /{tenant_id}/users` - Listar usuários do tenant
- `POST /{tenant_id}/users/{user_id}` - Adicionar usuário ao tenant
- `DELETE /{tenant_id}/users/{user_id}` - Remover usuário do tenant
- `GET /{tenant_id}/settings` - Obter configurações do tenant
- `PUT /{tenant_id}/settings` - Atualizar configurações do tenant
- `GET /{tenant_id}/stats` - Obter estatísticas do tenant

### 🔑 **API Keys (/api-keys)** *(Escopo por Tenant)*
- `POST /` - Criar chave de API
- `GET /` - Listar chaves de API
- `GET /{api_key_id}` - Obter chave de API
- `PUT /{api_key_id}` - Atualizar chave de API
- `DELETE /{api_key_id}` - Deletar chave de API
- `POST /{api_key_id}/rotate` - Rotacionar chave de API
- `GET /{api_key_id}/usage` - Ver uso da chave
- `GET /{api_key_id}/stats` - Ver estatísticas da chave

### 🔗 **Webhooks (/webhooks)** *(Escopo por Tenant)*
- `POST /` - Criar webhook
- `GET /` - Listar webhooks
- `GET /{webhook_id}` - Obter webhook
- `PUT /{webhook_id}` - Atualizar webhook
- `DELETE /{webhook_id}` - Deletar webhook
- `POST /{webhook_id}/test` - Testar webhook
- `GET /{webhook_id}/deliveries` - Ver entregas
- `GET /{webhook_id}/logs` - Ver logs
- `GET /events/types` - Listar tipos de eventos

### 📊 **Cache (/cache)** *(Disponível quando Redis habilitado)*
- `GET /cache/health` - Status do Redis
- `GET /cache/stats` - Estatísticas do cache
- `POST /cache/clear` - Limpar cache
- `GET /cache/keys` - Listar chaves do cache
- `GET /cache/key/{key}` - Obter valor da chave
- `DELETE /cache/key/{key}` - Remover chave
- `POST /cache/invalidate/user/{user_id}` - Invalidar cache do usuário
- `POST /cache/test` - Testar performance do cache

### 🔧 **Sistema**
- `GET /` - Informações básicas da API
- `GET /health` - Health check
- `GET /info` - Informações da aplicação (apenas desenvolvimento)

## Mudanças Realizadas

### ✅ **Endpoints Corrigidos**
1. **Alinhamento Frontend-Backend:**
   - `/protected/read-posts` → `/protected/posts`
   - `/protected/create-post` → `/protected/posts/create`

### ✅ **Endpoints Removidos**
1. **Duplicados:**
   - `/auth/token` (duplicado com `/auth/login`)

2. **Não Utilizados pelo Frontend:**
   - `/protected/update-post`
   - `/protected/delete-post`
   - `/protected/modify-settings`
   - `/protected/admin-only`
   - `/protected/manager-or-admin`

### ✅ **Estrutura Limpa**
- Todos os endpoints estão alinhados com o uso do frontend
- Removidas duplicidades desnecessárias
- Mantidos apenas endpoints ativos e necessários
- Documentação organizada por funcionalidade

## Uso no Frontend

Os endpoints atualmente utilizados pelo frontend estão todos funcionando:
- ✅ Login e autenticação
- ✅ Gerenciamento de usuários
- ✅ Gerenciamento de roles
- ✅ Gerenciamento de permissões
- ✅ Endpoints protegidos
- ✅ Provedores OAuth
- ✅ Health check

## Observações

1. **2FA**: Funcionalidade completa implementada no backend, aguardando integração no frontend
2. **Cache**: Endpoints disponíveis quando Redis está habilitado
3. **Permissões**: Sistema completo de RBAC funcionando
4. **OAuth**: Provedores configurados (Google, Microsoft, GitHub) 