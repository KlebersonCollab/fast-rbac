# 📊 Dashboard de Logs em Tempo Real

## 🎯 Visão Geral

O **Dashboard de Logs** é uma funcionalidade completa de monitoramento e análise de logs em tempo real para o sistema FastAPI + RBAC. Permite visualização, filtragem e análise avançada de todos os logs do sistema.

## 🚀 Características Principais

### ✅ **Implementado**
- **📊 Visão Geral em Tempo Real**: Métricas principais, gráficos de distribuição
- **🔍 Análise Detalhada**: Filtros avançados, busca textual, exploração interativa
- **👥 Atividade de Usuários**: Estatísticas de login, navegação, ações
- **⚡ Performance**: Análise de endpoints, requests lentos, status codes
- **🚨 Alertas Automáticos**: Detecção de problemas em tempo real
- **🔄 Auto-refresh**: Atualização automática a cada 30 segundos
- **🎛️ Filtros Avançados**: Por categoria, nível, usuário, período
- **📈 Gráficos Interativos**: Plotly charts com drill-down

## 🛡️ Controle de Acesso

**Permissão necessária**: `logs:view`

**Roles com acesso**:
- ✅ **admin**: Acesso completo
- ✅ **manager**: Acesso completo  
- ❌ **editor**: Sem acesso (segurança)
- ❌ **viewer**: Sem acesso (segurança)

## 📱 Interface

### 🏠 **Navegação**
- Acessível via sidebar: **"📊 Logs Monitor"**
- Disponível apenas para usuários com permissão

### 📋 **Abas do Dashboard**

#### 1. **📊 Visão Geral**
- **Métricas principais**: Total de entradas, erros, tempo de resposta
- **Gráfico de pizza**: Logs por nível (DEBUG, INFO, WARNING, ERROR)
- **Gráfico de barras**: Volume por categoria (Backend, Frontend, System)
- **Timeline**: Atividade por hora

#### 2. **🔍 Análise Detalhada**
- **Filtros**: Categoria, nível, termo de busca
- **Tabela interativa**: Logs filtrados com paginação
- **Detalhes JSON**: Visualização completa de logs selecionados
- **Controle de volume**: Slider para máximo de entradas

#### 3. **👥 Atividade de Usuários**
- **Usuários ativos**: Contagem em tempo real
- **Estatísticas de login**: Tentativas, sucessos, falhas, taxa de sucesso
- **Top usuários**: Ranking por atividade
- **Page views**: Páginas mais visitadas

#### 4. **⚡ Performance**
- **Endpoints populares**: Ranking por número de requests
- **Status codes**: Distribuição 2xx, 3xx, 4xx, 5xx
- **Requests lentos**: Top 10 com detalhes
- **Tempo de resposta**: Médio por endpoint

## 🚨 Sistema de Alertas

### **Alertas Automáticos**:
- 🔴 **Alto número de erros** (>10 na última hora)
- 🟡 **Requests lentos** (>5 requests >2s na última hora)
- 🔴 **Múltiplas falhas de login** (>5 na última hora)
- 🟡 **Tempo de resposta alto** (média >500ms)

### **Níveis de Alerta**:
- 🔴 **High**: Problemas críticos de segurança/erro
- 🟡 **Medium**: Problemas de performance
- 🟢 **Low**: Informacionais

## ⚙️ Configurações

### **Períodos de Análise**:
- Última 1 hora
- Últimas 6 horas  
- **Últimas 24 horas** (padrão)
- Últimos 3 dias
- Última semana

### **Auto-refresh**:
- ✅ **Ativado por padrão**: 30 segundos
- 🔄 **Refresh manual**: Botão dedicado
- 📱 **Responsivo**: Interface adaptável

## 📂 Arquivos de Log Suportados

### **Backend**:
- `api/access.log`: Requests HTTP
- `auth/auth.log`: Autenticação
- `rbac/rbac.log`: Controle de acesso
- `errors/errors.log`: Erros do sistema

### **Frontend**:
- `user_actions/actions.log`: Ações dos usuários
- `permissions/permissions.log`: Verificações de permissão
- `ui/ui.log`: Interações de interface
- `api/api.log`: Chamadas de API

### **System**:
- `startup/startup.log`: Inicialização
- `health/health.log`: Health checks

## 🔧 Implementação Técnica

### **Serviços**:
- `front/services/logs_analyzer.py`: Análise de logs
- `front/pages/logs_dashboard.py`: Interface do dashboard

### **Dependências Adicionadas**:
- **plotly**: Gráficos interativos
- **pandas**: Manipulação de dados

### **Permissões**:
- `logs:view`: Visualização de logs do sistema

## 🎯 Casos de Uso

### **👨‍💼 Para Administradores**:
- Monitoramento de segurança em tempo real
- Análise de performance de APIs
- Detecção de padrões suspeitos
- Auditoria de ações de usuários

### **👨‍💻 Para Managers**:
- Acompanhamento de uso do sistema
- Identificação de problemas de UX
- Análise de carga e performance
- Relatórios de atividade

### **🔧 Para Debugging**:
- Rastreamento de erros específicos
- Análise de fluxo de requests
- Correlação entre frontend e backend
- Identificação de gargalos

## 📈 Próximos Passos Sugeridos

### **Fase 1: Melhorias Imediatas**
- 📧 **Alertas por email**: Notificações automáticas
- 📱 **Dashboard mobile**: Interface otimizada
- 🔍 **Busca avançada**: Regex, operadores booleanos
- 📊 **Exports**: CSV, PDF, Excel

### **Fase 2: Integrações**
- 🐘 **PostgreSQL**: Migration para produção
- 🗄️ **Redis**: Cache de métricas
- 📈 **Prometheus**: Métricas técnicas
- 🎯 **Grafana**: Dashboards avançados

### **Fase 3: Inteligência**
- 🤖 **ML Anomalies**: Detecção automática
- 📊 **Trending**: Análise de tendências
- 🎯 **Predictions**: Alertas preditivos
- 📋 **Reports**: Relatórios automatizados

## 🎉 Resultado

✅ **Dashboard completo e funcional**  
✅ **Interface intuitiva e responsiva**  
✅ **Análise em tempo real**  
✅ **Controle de acesso integrado**  
✅ **Sistema de alertas automático**  
✅ **Performance otimizada**

---

*🔄 Última atualização: Dashboard implementado e operacional*  
*📊 Status: ✅ Produção*  
*🛡️ Segurança: ✅ Permissions-based* 