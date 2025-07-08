"""
Interface para gerenciamento de Webhooks
Funcionalidades NÍVEL 5 - Enterprise
"""

import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import pandas as pd
import requests
import streamlit as st

from front.services.api_client import APIClient
from front.utils.helpers import format_datetime, show_error, show_success, show_warning


class WebhooksView:
    """View para gerenciamento de Webhooks"""

    def __init__(self, api_client: APIClient):
        self.api_client = api_client

    def render(self):
        """Renderizar a interface de Webhooks"""
        st.title("🪝 Gerenciamento de Webhooks")
        st.markdown("---")

        # Verificar autenticação
        if not st.session_state.get("token"):
            st.error("🚫 Você precisa estar logado para acessar esta página")
            return

        # Tabs principais
        tab1, tab2, tab3, tab4, tab5 = st.tabs(
            [
                "📋 Listar Webhooks",
                "🆕 Criar Novo",
                "📡 Logs de Entrega",
                "🧪 Testar Webhook",
                "📊 Analytics",
            ]
        )

        with tab1:
            self._render_list_webhooks()

        with tab2:
            self._render_create_webhook()

        with tab3:
            self._render_delivery_logs()

        with tab4:
            self._render_test_webhook()

        with tab5:
            self._render_analytics()

    def _render_list_webhooks(self):
        """Renderizar lista de Webhooks"""
        st.subheader("📋 Webhooks Configurados")

        # Controles superiores
        col1, col2, col3 = st.columns([1, 2, 1])
        with col1:
            if st.button("🔄 Atualizar", key="refresh_webhooks"):
                st.rerun()

        with col3:
            view_mode = st.selectbox(
                "Visualização", ["Tabela", "Cards"], key="webhook_view_mode"
            )

        # Buscar webhooks
        try:
            response = self.api_client.get("/webhooks")
            if response and response.get("status_code") == 200:
                webhooks = response.get("data", [])

                if not webhooks:
                    st.info("🪝 Nenhum webhook encontrado. Configure o primeiro!")
                    return

                # Filtros
                st.markdown("### 🔍 Filtros")
                col1, col2, col3, col4 = st.columns(4)

                with col1:
                    status_filter = st.selectbox(
                        "Status",
                        ["Todos", "Ativo", "Inativo", "Com Erro"],
                        key="webhook_status_filter",
                    )

                with col2:
                    event_filter = st.selectbox(
                        "Evento",
                        [
                            "Todos",
                            "user.created",
                            "user.updated",
                            "user.deleted",
                            "auth.login",
                            "auth.logout",
                        ],
                        key="event_filter",
                    )

                with col3:
                    method_filter = st.selectbox(
                        "Método HTTP",
                        ["Todos", "POST", "PUT", "PATCH"],
                        key="method_filter",
                    )

                with col4:
                    sort_by = st.selectbox(
                        "Ordenar por",
                        ["Nome", "Data Criação", "Última Entrega", "Taxa Sucesso"],
                        key="webhook_sort_by",
                    )

                # Filtrar dados
                filtered_webhooks = self._filter_webhooks(
                    webhooks, status_filter, event_filter, method_filter
                )

                # Exibir baseado no modo selecionado
                if view_mode == "Tabela":
                    self._render_webhooks_table(filtered_webhooks)
                else:
                    self._render_webhooks_cards(filtered_webhooks)

            else:
                st.error("❌ Erro ao carregar webhooks")

        except Exception as e:
            show_error(f"Erro ao carregar webhooks: {str(e)}")

    def _render_create_webhook(self):
        """Renderizar formulário de criação de webhook"""
        st.subheader("🆕 Criar Novo Webhook")

        with st.form("create_webhook"):
            # Informações básicas
            st.markdown("### 📝 Configuração Básica")
            col1, col2 = st.columns(2)

            with col1:
                name = st.text_input(
                    "Nome do Webhook *",
                    placeholder="Ex: Notificação Slack",
                    help="Nome descritivo para identificar este webhook",
                )

                url = st.text_input(
                    "URL de Destino *",
                    placeholder="https://hooks.slack.com/services/...",
                    help="URL onde os eventos serão enviados",
                )

                method = st.selectbox(
                    "Método HTTP",
                    ["POST", "PUT", "PATCH"],
                    index=0,
                    help="Método HTTP a ser usado",
                )

            with col2:
                description = st.text_area(
                    "Descrição",
                    placeholder="Descreva o propósito deste webhook...",
                    height=120,
                )

                secret = st.text_input(
                    "Secret (opcional)",
                    type="password",
                    help="Chave secreta para validação de segurança",
                )

            # Eventos
            st.markdown("### 🎯 Eventos a Monitorar")

            col1, col2, col3 = st.columns(3)

            events = []

            with col1:
                st.markdown("**👤 Usuários:**")
                if st.checkbox("user.created", help="Usuário criado"):
                    events.append("user.created")
                if st.checkbox("user.updated", help="Usuário atualizado"):
                    events.append("user.updated")
                if st.checkbox("user.deleted", help="Usuário deletado"):
                    events.append("user.deleted")
                if st.checkbox("user.activated", help="Usuário ativado"):
                    events.append("user.activated")
                if st.checkbox("user.deactivated", help="Usuário desativado"):
                    events.append("user.deactivated")

            with col2:
                st.markdown("**🔐 Autenticação:**")
                if st.checkbox("auth.login", help="Login realizado"):
                    events.append("auth.login")
                if st.checkbox("auth.logout", help="Logout realizado"):
                    events.append("auth.logout")
                if st.checkbox("auth.failed_login", help="Tentativa de login falhada"):
                    events.append("auth.failed_login")
                if st.checkbox("auth.password_reset", help="Reset de senha"):
                    events.append("auth.password_reset")
                if st.checkbox("auth.2fa_enabled", help="2FA habilitado"):
                    events.append("auth.2fa_enabled")

            with col3:
                st.markdown("**⚙️ Sistema:**")
                if st.checkbox("system.maintenance", help="Modo manutenção"):
                    events.append("system.maintenance")
                if st.checkbox("system.error", help="Erro do sistema"):
                    events.append("system.error")
                if st.checkbox("api.rate_limit", help="Rate limit atingido"):
                    events.append("api.rate_limit")
                if st.checkbox("tenant.created", help="Tenant criado"):
                    events.append("tenant.created")
                if st.checkbox("api_key.created", help="API Key criada"):
                    events.append("api_key.created")

            # Configurações avançadas
            st.markdown("### ⚙️ Configurações Avançadas")
            col1, col2, col3 = st.columns(3)

            with col1:
                timeout_seconds = st.number_input(
                    "Timeout (segundos)",
                    min_value=5,
                    max_value=300,
                    value=30,
                    help="Tempo limite para a requisição",
                )

                retry_enabled = st.checkbox(
                    "Habilitar Retry",
                    value=True,
                    help="Tentar novamente em caso de falha",
                )

            with col2:
                max_retries = st.number_input(
                    "Máximo de Tentativas",
                    min_value=1,
                    max_value=10,
                    value=3,
                    disabled=not retry_enabled,
                )

                retry_delay_seconds = st.number_input(
                    "Delay entre Tentativas (s)",
                    min_value=1,
                    max_value=3600,
                    value=60,
                    disabled=not retry_enabled,
                )

            with col3:
                is_active = st.checkbox("Ativar imediatamente", value=True)

                tenant_id = st.number_input(
                    "Tenant ID",
                    min_value=1,
                    value=1,
                    help="ID do tenant (1 para tenant padrão)",
                )

            # Headers customizados
            st.markdown("### 📋 Headers HTTP Customizados")

            headers_json = st.text_area(
                "Headers (JSON)",
                placeholder='{\n  "Content-Type": "application/json",\n  "Authorization": "Bearer token"\n}',
                height=100,
                help="Headers adicionais em formato JSON",
            )

            # Botão de criação
            st.markdown("---")
            submitted = st.form_submit_button("🪝 Criar Webhook", type="primary")

            if submitted and name and url:
                # Validar headers JSON
                custom_headers = {}
                if headers_json.strip():
                    try:
                        custom_headers = json.loads(headers_json)
                    except json.JSONDecodeError:
                        st.error("❌ Headers JSON inválido")
                        return

                if not events:
                    st.error("❌ Selecione pelo menos um evento para monitorar")
                    return

                self._create_webhook(
                    {
                        "name": name,
                        "url": url,
                        "method": method,
                        "description": description,
                        "secret": secret if secret else None,
                        "events": events,
                        "timeout_seconds": timeout_seconds,
                        "retry_enabled": retry_enabled,
                        "max_retries": max_retries,
                        "retry_delay_seconds": retry_delay_seconds,
                        "is_active": is_active,
                        "tenant_id": tenant_id,
                        "custom_headers": custom_headers,
                    }
                )
            elif submitted:
                st.error("❌ Nome e URL são obrigatórios")

    def _render_delivery_logs(self):
        """Renderizar logs de entrega dos webhooks"""
        st.subheader("📡 Logs de Entrega")

        # Filtros
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            webhook_filter = st.selectbox(
                "Webhook",
                ["Todos"] + [f"Webhook {i+1}" for i in range(5)],  # Placeholder
                key="delivery_webhook_filter",
            )

        with col2:
            status_filter = st.selectbox(
                "Status Entrega",
                ["Todos", "Sucesso", "Falha", "Pendente", "Retry"],
                key="delivery_status_filter",
            )

        with col3:
            period_filter = st.selectbox(
                "Período",
                ["Última Hora", "Último Dia", "Última Semana", "Último Mês"],
                key="delivery_period_filter",
            )

        with col4:
            if st.button("🔄 Atualizar Logs", key="refresh_delivery_logs"):
                st.rerun()

        # Buscar logs de entrega
        try:
            response = self.api_client.get(
                "/webhooks/delivery-logs",
                params={
                    "webhook_id": webhook_filter if webhook_filter != "Todos" else None,
                    "status": status_filter if status_filter != "Todos" else None,
                    "period": period_filter,
                },
            )

            if response and response.get("status_code") == 200:
                logs = response.get("data", [])

                if logs:
                    # Estatísticas rápidas
                    col1, col2, col3, col4 = st.columns(4)

                    success_count = len(
                        [l for l in logs if l.get("status") == "success"]
                    )
                    total_count = len(logs)
                    success_rate = (
                        (success_count / total_count * 100) if total_count > 0 else 0
                    )

                    with col1:
                        st.metric("Total Entregas", total_count)
                    with col2:
                        st.metric("Sucessos", success_count)
                    with col3:
                        st.metric("Taxa Sucesso", f"{success_rate:.1f}%")
                    with col4:
                        failed_count = total_count - success_count
                        st.metric("Falhas", failed_count)

                    # Tabela de logs
                    logs_df = pd.DataFrame(
                        [
                            {
                                "ID": log.get("id"),
                                "Webhook": log.get("webhook_name", "N/A"),
                                "Evento": log.get("event_type"),
                                "Status": self._format_delivery_status(
                                    log.get("status")
                                ),
                                "Código HTTP": log.get("http_status_code", "N/A"),
                                "Tentativas": f"{log.get('attempt_count', 1)}/{log.get('max_retries', 1)}",
                                "Tempo Resposta": f"{log.get('response_time_ms', 0)}ms",
                                "Enviado em": format_datetime(log.get("created_at")),
                                "Próxima Tentativa": (
                                    format_datetime(log.get("next_retry_at"))
                                    if log.get("next_retry_at")
                                    else "N/A"
                                ),
                            }
                            for log in logs
                        ]
                    )

                    # Configurar visualização da tabela
                    st.dataframe(
                        logs_df,
                        use_container_width=True,
                        column_config={
                            "Status": st.column_config.Column("Status", width="small"),
                            "Código HTTP": st.column_config.Column(
                                "HTTP", width="small"
                            ),
                            "Tempo Resposta": st.column_config.Column(
                                "Resp. Time", width="small"
                            ),
                        },
                    )

                    # Detalhes do log selecionado
                    if st.checkbox("Mostrar detalhes do log"):
                        selected_log_id = st.selectbox(
                            "Selecionar log para detalhes",
                            options=[
                                f"ID {log['id']} - {log.get('event_type')}"
                                for log in logs
                            ],
                        )

                        if selected_log_id:
                            log_id = int(selected_log_id.split("ID ")[1].split(" -")[0])
                            selected_log = next(
                                (l for l in logs if l["id"] == log_id), None
                            )

                            if selected_log:
                                self._render_log_details(selected_log)
                else:
                    st.info("📡 Nenhum log de entrega encontrado")
            else:
                st.error("❌ Erro ao carregar logs de entrega")

        except Exception as e:
            show_error(f"Erro ao carregar logs: {str(e)}")

    def _render_test_webhook(self):
        """Renderizar interface de teste de webhook"""
        st.subheader("🧪 Testar Webhook")

        # Seletor de webhook
        try:
            response = self.api_client.get("/webhooks")
            if response and response.get("status_code") == 200:
                webhooks = response.get("data", [])

                if not webhooks:
                    st.info("🪝 Nenhum webhook disponível para teste")
                    return

                selected_webhook = st.selectbox(
                    "Selecionar Webhook",
                    options=[f"{w['name']} - {w['url']}" for w in webhooks],
                    key="test_webhook_select",
                )

                if selected_webhook:
                    webhook_name = selected_webhook.split(" - ")[0]
                    webhook = next(
                        (w for w in webhooks if w["name"] == webhook_name), None
                    )

                    if webhook:
                        # Mostrar informações do webhook
                        col1, col2 = st.columns(2)

                        with col1:
                            st.markdown("**Informações do Webhook:**")
                            st.write(f"**Nome:** {webhook['name']}")
                            st.write(f"**URL:** {webhook['url']}")
                            st.write(f"**Método:** {webhook.get('method', 'POST')}")
                            st.write(
                                f"**Status:** {'🟢 Ativo' if webhook.get('is_active') else '🔴 Inativo'}"
                            )

                        with col2:
                            st.markdown("**Eventos Monitorados:**")
                            events = json.loads(webhook.get("events", "[]"))
                            for event in events:
                                st.write(f"• {event}")

                        # Configurar teste
                        st.markdown("### 🎯 Configurar Teste")

                        col1, col2 = st.columns(2)

                        with col1:
                            test_event = st.selectbox(
                                "Evento de Teste",
                                options=events if events else ["user.created"],
                                key="test_event_select",
                            )

                            test_data_template = st.selectbox(
                                "Template de Dados",
                                ["Usuário Exemplo", "Dados Customizados"],
                                key="test_data_template",
                            )

                        with col2:
                            include_timestamp = st.checkbox(
                                "Incluir timestamp", value=True
                            )
                            include_signature = st.checkbox(
                                "Incluir assinatura", value=True
                            )

                        # Payload de teste
                        if test_data_template == "Usuário Exemplo":
                            test_payload = {
                                "event": test_event,
                                "timestamp": (
                                    datetime.now().isoformat()
                                    if include_timestamp
                                    else None
                                ),
                                "data": {
                                    "user": {
                                        "id": 123,
                                        "username": "usuario_teste",
                                        "email": "teste@exemplo.com",
                                        "full_name": "Usuário Teste",
                                        "is_active": True,
                                        "created_at": datetime.now().isoformat(),
                                    }
                                },
                            }
                        else:
                            test_payload = {}

                        payload_json = st.text_area(
                            "Payload JSON",
                            value=json.dumps(test_payload, indent=2),
                            height=200,
                            help="Dados que serão enviados no webhook",
                        )

                        # Botão de teste
                        col1, col2 = st.columns([1, 3])
                        with col1:
                            if st.button("🚀 Executar Teste", type="primary"):
                                self._execute_webhook_test(
                                    webhook["id"], test_event, payload_json
                                )

                        # Histórico de testes
                        st.markdown("### 📊 Histórico de Testes")
                        self._render_test_history(webhook["id"])

        except Exception as e:
            show_error(f"Erro ao carregar webhooks para teste: {str(e)}")

    def _render_analytics(self):
        """Renderizar analytics dos webhooks"""
        st.subheader("📊 Analytics de Webhooks")

        try:
            # Buscar estatísticas
            stats_response = self.api_client.get("/webhooks/analytics")
            if stats_response and stats_response.get("status_code") == 200:
                stats = stats_response.get("data", {})

                # Métricas principais
                col1, col2, col3, col4 = st.columns(4)

                with col1:
                    st.metric(
                        "Total Webhooks",
                        stats.get("total_webhooks", 0),
                        delta=stats.get("new_webhooks_this_month", 0),
                    )

                with col2:
                    st.metric(
                        "Webhooks Ativos",
                        stats.get("active_webhooks", 0),
                        delta=f"{stats.get('active_percentage', 0):.1f}%",
                    )

                with col3:
                    st.metric(
                        "Entregas Hoje",
                        stats.get("deliveries_today", 0),
                        delta=stats.get("deliveries_yesterday", 0),
                    )

                with col4:
                    success_rate = stats.get("overall_success_rate", 0)
                    st.metric(
                        "Taxa Sucesso",
                        f"{success_rate:.1f}%",
                        delta=f"{stats.get('success_rate_change', 0):.1f}%",
                    )

                # Gráficos
                col1, col2 = st.columns(2)

                with col1:
                    if stats.get("delivery_volume_data"):
                        st.markdown("### 📈 Volume de Entregas")
                        volume_df = pd.DataFrame(stats["delivery_volume_data"])
                        st.line_chart(volume_df.set_index("date"))

                with col2:
                    if stats.get("success_rate_data"):
                        st.markdown("### 📊 Taxa de Sucesso")
                        success_df = pd.DataFrame(stats["success_rate_data"])
                        st.line_chart(success_df.set_index("date"))

                # Eventos mais populares
                if stats.get("popular_events"):
                    st.markdown("### 🎯 Eventos Mais Populares")
                    events_df = pd.DataFrame(stats["popular_events"])
                    st.bar_chart(events_df.set_index("event"))

                # Top webhooks por performance
                if stats.get("top_webhooks"):
                    st.markdown("### 🏆 Top Webhooks por Performance")
                    top_df = pd.DataFrame(stats["top_webhooks"])
                    st.dataframe(top_df, use_container_width=True)

            else:
                st.warning("⚠️ Não foi possível carregar analytics")

        except Exception as e:
            show_error(f"Erro ao carregar analytics: {str(e)}")

    def _render_webhooks_table(self, webhooks: List[Dict]):
        """Renderizar tabela de webhooks"""
        if not webhooks:
            st.info("🔍 Nenhum webhook encontrado com os filtros aplicados")
            return

        # Criar DataFrame
        df = pd.DataFrame(
            [
                {
                    "ID": w.get("id"),
                    "Nome": w.get("name"),
                    "URL": (
                        w.get("url")[:50] + "..."
                        if len(w.get("url", "")) > 50
                        else w.get("url")
                    ),
                    "Eventos": len(json.loads(w.get("events", "[]"))),
                    "Status": "🟢 Ativo" if w.get("is_active") else "🔴 Inativo",
                    "Última Entrega": (
                        format_datetime(w.get("last_delivery_at"))
                        if w.get("last_delivery_at")
                        else "Nunca"
                    ),
                    "Taxa Sucesso": f"{w.get('success_rate', 0):.1f}%",
                    "Total Entregas": w.get("total_deliveries", 0),
                    "Criado em": format_datetime(w.get("created_at")),
                }
                for w in webhooks
            ]
        )

        # Configurar editor de dados
        edited_df = st.data_editor(
            df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Status": st.column_config.SelectboxColumn(
                    "Status",
                    options=["🟢 Ativo", "🔴 Inativo"],
                    width="small",
                ),
                "Taxa Sucesso": st.column_config.ProgressColumn(
                    "Taxa Sucesso",
                    min_value=0,
                    max_value=100,
                    format="%.1f%%",
                    width="small",
                ),
            },
            disabled=[
                "ID",
                "Nome",
                "URL",
                "Eventos",
                "Última Entrega",
                "Total Entregas",
                "Criado em",
            ],
            key="webhooks_table",
        )

        # Ações rápidas
        self._render_webhook_actions(webhooks)

    def _render_webhooks_cards(self, webhooks: List[Dict]):
        """Renderizar cards de webhooks"""
        cols = st.columns(2)

        for i, webhook in enumerate(webhooks):
            with cols[i % 2]:
                with st.container():
                    # Header do card
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.markdown(f"### 🪝 {webhook.get('name')}")
                        st.caption(f"URL: {webhook.get('url')[:40]}...")

                    with col2:
                        status_icon = "🟢" if webhook.get("is_active") else "🔴"
                        st.markdown(f"{status_icon}")

                    # Informações principais
                    events = json.loads(webhook.get("events", "[]"))
                    st.markdown(f"**Eventos:** {len(events)} configurados")
                    st.markdown(f"**Método:** {webhook.get('method', 'POST')}")

                    # Métricas
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric(
                            "Taxa Sucesso", f"{webhook.get('success_rate', 0):.1f}%"
                        )
                    with col2:
                        st.metric("Entregas", webhook.get("total_deliveries", 0))

                    # Ações
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        if st.button("🧪 Teste", key=f"test_{webhook['id']}"):
                            st.session_state.test_webhook_id = webhook["id"]
                    with col2:
                        if st.button("📊 Logs", key=f"logs_{webhook['id']}"):
                            st.session_state.webhook_logs_id = webhook["id"]
                    with col3:
                        if st.button("⚙️ Edit", key=f"edit_{webhook['id']}"):
                            st.session_state.edit_webhook_id = webhook["id"]

                    st.markdown("---")

    def _filter_webhooks(
        self,
        webhooks: List[Dict],
        status_filter: str,
        event_filter: str,
        method_filter: str,
    ) -> List[Dict]:
        """Filtrar webhooks baseado nos filtros selecionados"""
        filtered = webhooks.copy()

        # Filtro por status
        if status_filter != "Todos":
            if status_filter == "Ativo":
                filtered = [w for w in filtered if w.get("is_active", False)]
            elif status_filter == "Inativo":
                filtered = [w for w in filtered if not w.get("is_active", False)]

        # Filtro por evento
        if event_filter != "Todos":
            filtered = [
                w for w in filtered if event_filter in json.loads(w.get("events", "[]"))
            ]

        # Filtro por método
        if method_filter != "Todos":
            filtered = [w for w in filtered if w.get("method") == method_filter]

        return filtered

    def _format_delivery_status(self, status: str) -> str:
        """Formatar status de entrega para exibição"""
        status_map = {
            "success": "✅ Sucesso",
            "failed": "❌ Falha",
            "pending": "⏳ Pendente",
            "retry": "🔄 Retry",
        }
        return status_map.get(status, status)

    def _render_log_details(self, log: Dict):
        """Renderizar detalhes de um log específico"""
        st.markdown("### 📋 Detalhes do Log")

        col1, col2 = st.columns(2)

        with col1:
            st.write(f"**ID:** {log.get('id')}")
            st.write(f"**Webhook:** {log.get('webhook_name')}")
            st.write(f"**Evento:** {log.get('event_type')}")
            st.write(f"**Status:** {self._format_delivery_status(log.get('status'))}")
            st.write(f"**Código HTTP:** {log.get('http_status_code', 'N/A')}")

        with col2:
            st.write(
                f"**Tentativas:** {log.get('attempt_count')}/{log.get('max_retries')}"
            )
            st.write(f"**Tempo Resposta:** {log.get('response_time_ms')}ms")
            st.write(f"**Enviado em:** {format_datetime(log.get('created_at'))}")
            if log.get("next_retry_at"):
                st.write(
                    f"**Próxima Tentativa:** {format_datetime(log.get('next_retry_at'))}"
                )

        # Payload e resposta
        if log.get("request_payload"):
            st.markdown("**Payload Enviado:**")
            st.code(
                json.dumps(json.loads(log["request_payload"]), indent=2),
                language="json",
            )

        if log.get("response_body"):
            st.markdown("**Resposta Recebida:**")
            st.code(log["response_body"])

        if log.get("error_message"):
            st.markdown("**Erro:**")
            st.error(log["error_message"])

    def _render_test_history(self, webhook_id: int):
        """Renderizar histórico de testes de um webhook"""
        # Implementar busca do histórico de testes
        test_history = [
            {
                "id": 1,
                "event": "user.created",
                "status": "success",
                "response_time": 150,
                "executed_at": datetime.now() - timedelta(minutes=5),
            },
            {
                "id": 2,
                "event": "user.updated",
                "status": "failed",
                "response_time": 5000,
                "executed_at": datetime.now() - timedelta(hours=1),
            },
        ]

        if test_history:
            history_df = pd.DataFrame(
                [
                    {
                        "Evento": test.get("event"),
                        "Status": self._format_delivery_status(test.get("status")),
                        "Tempo Resposta": f"{test.get('response_time')}ms",
                        "Executado em": format_datetime(test.get("executed_at")),
                    }
                    for test in test_history
                ]
            )

            st.dataframe(history_df, use_container_width=True)
        else:
            st.info("📝 Nenhum teste executado ainda")

    def _render_webhook_actions(self, webhooks: List[Dict]):
        """Renderizar ações para webhooks"""
        if not webhooks:
            return

        st.markdown("### ⚡ Ações Rápidas")

        selected_webhook = st.selectbox(
            "Selecionar Webhook para Ação",
            options=[f"{w['name']} (ID: {w['id']})" for w in webhooks],
            key="action_webhook_select",
        )

        if selected_webhook:
            webhook_id = int(selected_webhook.split("ID: ")[1].split(")")[0])

            col1, col2, col3, col4 = st.columns(4)

            with col1:
                if st.button("🧪 Testar"):
                    self._test_webhook(webhook_id)

            with col2:
                if st.button("⏸️ Desativar"):
                    self._toggle_webhook_status(webhook_id, False)

            with col3:
                if st.button("▶️ Ativar"):
                    self._toggle_webhook_status(webhook_id, True)

            with col4:
                if st.button("🗑️ Deletar", type="secondary"):
                    self._delete_webhook(webhook_id)

    def _create_webhook(self, data: Dict):
        """Criar novo webhook"""
        try:
            response = self.api_client.post("/webhooks", data)
            if response and response.get("status_code") == 200:
                show_success("🎉 Webhook criado com sucesso!")
                time.sleep(1)
                st.rerun()
            else:
                show_error("Erro ao criar webhook")
        except Exception as e:
            show_error(f"Erro ao criar webhook: {str(e)}")

    def _execute_webhook_test(self, webhook_id: int, event: str, payload: str):
        """Executar teste de webhook"""
        try:
            test_data = {
                "event": event,
                "payload": json.loads(payload) if payload else {},
            }

            response = self.api_client.post(f"/webhooks/{webhook_id}/test", test_data)
            if response and response.get("status_code") == 200:
                result = response.get("data", {})

                if result.get("success"):
                    show_success(
                        f"✅ Teste executado com sucesso! Tempo: {result.get('response_time', 0)}ms"
                    )
                else:
                    show_error(
                        f"❌ Teste falhou: {result.get('error', 'Erro desconhecido')}"
                    )
            else:
                show_error("Erro ao executar teste")
        except json.JSONDecodeError:
            show_error("❌ Payload JSON inválido")
        except Exception as e:
            show_error(f"Erro ao executar teste: {str(e)}")

    def _toggle_webhook_status(self, webhook_id: int, active: bool):
        """Ativar/desativar webhook"""
        try:
            action = "activate" if active else "deactivate"
            response = self.api_client.post(f"/webhooks/{webhook_id}/{action}")

            if response and response.get("status_code") == 200:
                status_text = "ativado" if active else "desativado"
                show_success(f"✅ Webhook {status_text} com sucesso!")
                st.rerun()
            else:
                show_error(f"Erro ao {'ativar' if active else 'desativar'} webhook")
        except Exception as e:
            show_error(f"Erro ao alterar status do webhook: {str(e)}")

    def _delete_webhook(self, webhook_id: int):
        """Deletar webhook"""
        if st.button("⚠️ Confirmar Exclusão", type="secondary"):
            try:
                response = self.api_client.delete(f"/webhooks/{webhook_id}")
                if response and response.get("status_code") == 200:
                    show_success("🗑️ Webhook deletado com sucesso!")
                    st.rerun()
                else:
                    show_error("Erro ao deletar webhook")
            except Exception as e:
                show_error(f"Erro ao deletar webhook: {str(e)}")


def render_webhooks_view():
    """Função principal para renderizar a view de Webhooks"""
    api_client = APIClient()
    view = WebhooksView(api_client)
    view.render()
