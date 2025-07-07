# 📊 Sistema de Logs Customizados - FastAPI + Streamlit RBAC

## 🚀 **Implementação Completa**

Este documento demonstra o sistema completo de logs customizados implementado no projeto, que captura todas as atividades tanto do backend quanto do frontend de forma estruturada e organizada.

## 📁 **Estrutura de Logs**

```
logs/
├── backend/           # Logs do servidor FastAPI
│   ├── app.log       # Log principal da aplicação  
│   ├── auth/         # Logs de autenticação
│   │   └── auth.log
│   ├── rbac/         # Logs de controle de acesso
│   │   └── rbac.log
│   ├── api/          # Logs de requisições HTTP
│   │   └── access.log
│   └── errors/       # Logs de erros
│       └── errors.log
├── frontend/         # Logs do frontend Streamlit
│   ├── frontend.log  # Log principal do frontend
│   ├── user_actions/ # Ações dos usuários
│   │   └── actions.log
│   ├── permissions/  # Verificações de permissão
│   │   └── permissions.log
│   └── ui/          # Interações da interface
│       └── interactions.log
└── system/          # Logs do sistema
    ├── startup/     # Inicialização
    │   └── startup.log
    └── health/      # Health checks
        └── health.log
```

## 🔧 **Funcionalidades Implementadas**

### **Backend (FastAPI)**

#### **1. Middlewares Automáticos**
- ✅ **LoggingMiddleware**: Captura todas requisições/respostas
- ✅ **PerformanceLoggingMiddleware**: Detecta requests lentos (>500ms)
- ✅ **HealthCheckLoggingMiddleware**: Logs separados para health checks
- ✅ **UserActivityLoggingMiddleware**: Auditoria de ações de usuários

#### **2. Trace IDs Únicos**
- Cada requisição recebe um ID único para rastreamento
- Propagado através de headers `X-Trace-ID`
- Facilita debugging em sistemas distribuídos

#### **3. Logs Estruturados (JSON)**
- Formato consistente para análise automatizada
- Campos padronizados: timestamp, level, user_id, action, etc.
- Integração com ferramentas de monitoramento

#### **4. Rotação Automática**
- Arquivos limitados a 10MB
- 5 backups automáticos
- Compressão para otimizar espaço

### **Frontend (Streamlit)**

#### **1. Rastreamento de Sessão**
- Session IDs únicos por usuário
- Correlação entre ações do mesmo usuário
- Persistência durante toda a sessão

#### **2. Logs de Ações do Usuário**
- Login/logout com detalhes
- Navegação entre páginas
- Operações CRUD (criar, editar, deletar)
- Tentativas de acesso negadas

#### **3. Verificação de Permissões**
- Log de todas verificações de permissão
- Motivos de negação (usuário não encontrado, permissão inexistente, etc.)
- Identificação de roles que concedem acesso

#### **4. Integração com API**
- Logs de todas chamadas HTTP
- Tempo de resposta monitorado
- Captura de erros de conectividade

## 📊 **Exemplos de Logs**

### **1. Login Bem-Sucedido (Frontend)**
```json
{
  "timestamp": "2025-07-07T19:10:41.018269",
  "level": "INFO",
  "logger": "frontend.actions",
  "message": "User action: login on login for authentication",
  "user_id": 2,
  "username": "kleberson",
  "session_id": "c39cb476",
  "action": "login",
  "page": "login",
  "resource": "authentication",
  "details": {
    "username": "kleberson",
    "roles_count": 1,
    "user_id": 2
  }
}
```

### **2. Requisição HTTP (Backend)**
```json
{
  "timestamp": "2025-07-07T19:10:41.319912",
  "level": "INFO",
  "logger": "app.api",
  "message": "GET /auth/test-token - 200 (0.002s)",
  "user_id": null,
  "username": null,
  "ip_address": "127.0.0.1",
  "endpoint": "/auth/test-token",
  "method": "GET",
  "status_code": 200,
  "duration": 0.0017502307891845703,
  "trace_id": "969fc679"
}
```

### **3. Verificação de Permissão**
```json
{
  "timestamp": "2025-07-07T19:10:42.123456",
  "level": "INFO",
  "logger": "frontend.permissions",
  "message": "Permission users:read: granted for users",
  "user_id": 2,
  "username": "kleberson",
  "session_id": "c39cb476",
  "action": "permission_check",
  "permission": "users:read",
  "resource": "users",
  "granted": true,
  "role": "admin"
}
```

### **4. Erro de Autenticação (Backend)**
```json
{
  "timestamp": "2025-07-07T19:15:23.456789",
  "level": "WARNING",
  "logger": "app.auth",
  "message": "Auth login_attempt: failed for user test",
  "action": "login_attempt",
  "success": false,
  "username": "test",
  "reason": "user_not_found",
  "ip_address": "127.0.0.1"
}
```

## 🎯 **Casos de Uso Monitorados**

### **Segurança**
- ✅ Tentativas de login falhadas
- ✅ Acessos negados por falta de permissão
- ✅ Mudanças em roles e permissões
- ✅ Criação e edição de usuários

### **Performance**
- ✅ Requests que demoram mais que 500ms
- ✅ Tempo de resposta de todas as APIs
- ✅ Carregamento de páginas do frontend

### **Auditoria**
- ✅ Todas ações administrativas
- ✅ Histórico completo de navegação
- ✅ Modificações no sistema RBAC
- ✅ Atividade por usuário e sessão

### **Debugging**
- ✅ Trace IDs para seguir requisições
- ✅ Stack traces completos em erros
- ✅ Contexto detalhado em exceptions
- ✅ Logs estruturados para análise

## 🛠 **Como Usar**

### **Visualizar Logs em Tempo Real**
```bash
# Backend - Todas as requisições
tail -f logs/backend/api/access.log | jq .

# Frontend - Ações dos usuários  
tail -f logs/frontend/user_actions/actions.log | jq .

# Erros do sistema
tail -f logs/backend/errors/errors.log | jq .
```

### **Análise de Logs**
```bash
# Logins por usuário
cat logs/frontend/user_actions/actions.log | jq 'select(.action=="login") | {timestamp, username, success}'

# Requisições mais lentas
cat logs/backend/api/access.log | jq 'select(.duration > 0.1) | {endpoint, duration, timestamp}'

# Permissões negadas
cat logs/frontend/permissions/permissions.log | jq 'select(.granted==false) | {permission, username, reason}'
```

### **Integração com Ferramentas**

#### **ELK Stack (Elasticsearch + Logstash + Kibana)**
```yaml
# logstash.conf
input {
  file {
    path => "/app/logs/**/*.log"
    codec => "json"
  }
}
output {
  elasticsearch {
    hosts => ["elasticsearch:9200"]
  }
}
```

#### **Prometheus/Grafana**
- Métricas de performance extraídas dos logs
- Dashboards de monitoramento em tempo real
- Alertas baseados em padrões de erro

## 🔍 **Filtros e Buscas**

### **Por Usuário**
```bash
grep '"username": "kleberson"' logs/frontend/user_actions/actions.log | jq .
```

### **Por Endpoint**
```bash
grep '"/admin/users"' logs/backend/api/access.log | jq .
```

### **Por Trace ID**
```bash
grep '"trace_id": "969fc679"' logs/backend/**/*.log
```

### **Erros Críticos**
```bash
grep '"level": "ERROR"' logs/**/*.log | jq .
```

## 📈 **Benefícios**

1. **Transparência Total**: Visibilidade completa de todas as operações
2. **Debugging Eficiente**: Trace IDs e contexto detalhado
3. **Auditoria Completa**: Histórico de todas as ações
4. **Monitoramento Proativo**: Detecção de problemas em tempo real
5. **Compliance**: Logs estruturados para auditorias
6. **Performance**: Identificação de gargalos

## 🚀 **Próximos Passos**

- [ ] Dashboard web para visualização de logs
- [ ] Alertas automáticos por email/Slack
- [ ] Integração com Sentry para erros
- [ ] Métricas de negócio personalizadas
- [ ] Retenção configurável de logs
- [ ] Compression automática de logs antigos

---

O sistema de logs implementado fornece visibilidade completa e rastreabilidade total das operações, facilitando debugging, auditoria e monitoramento proativo do sistema FastAPI RBAC. 