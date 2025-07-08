"""
Interface para gerenciamento de Tenants (Multi-tenancy)
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


class TenantsView:
    """View para gerenciamento de Tenants"""

    def __init__(self, api_client: APIClient):
        self.api_client = api_client

    def render(self):
        """Renderizar a interface de Tenants"""
        st.title("🏢 Gerenciamento de Tenants")
        st.markdown("---")

        # Verificar autenticação
        if not st.session_state.get("token"):
            st.error("🚫 Você precisa estar logado para acessar esta página")
            return

        # Tabs principais
        tab1, tab2, tab3, tab4, tab5 = st.tabs(
            [
                "📋 Listar Tenants",
                "🆕 Criar Novo",
                "⚙️ Configurações",
                "📊 Analytics",
                "👥 Usuários",
            ]
        )

        with tab1:
            self._render_list_tenants()

        with tab2:
            self._render_create_tenant()

        with tab3:
            self._render_tenant_settings()

        with tab4:
            self._render_analytics()

        with tab5:
            self._render_tenant_users()

    def _render_list_tenants(self):
        """Renderizar lista de Tenants"""
        st.subheader("📋 Tenants Cadastrados")

        # Controles superiores
        col1, col2, col3 = st.columns([1, 2, 1])
        with col1:
            if st.button("🔄 Atualizar", key="refresh_tenants"):
                st.rerun()

        with col3:
            view_mode = st.selectbox(
                "Visualização", ["Tabela", "Cards"], key="view_mode"
            )

        # Buscar tenants
        try:
            tenants = self.api_client.get("/tenants/")

            if not tenants:
                st.info("🏢 Nenhum tenant encontrado. Crie o primeiro!")
                return

            # Filtros
            st.markdown("### 🔍 Filtros")
            col1, col2, col3, col4 = st.columns(4)

            with col1:
                status_filter = st.selectbox(
                    "Status",
                    ["Todos", "Ativo", "Inativo", "Suspenso"],
                    key="tenant_status_filter",
                )

            with col2:
                plan_filter = st.selectbox(
                    "Plano",
                    ["Todos", "free", "basic", "premium", "enterprise"],
                    key="plan_filter",
                )

            with col3:
                verified_filter = st.selectbox(
                    "Verificação",
                    ["Todos", "Verificado", "Não Verificado"],
                    key="verified_filter",
                )

            with col4:
                sort_by = st.selectbox(
                    "Ordenar por",
                    ["Nome", "Data Criação", "Usuários", "Plano"],
                    key="tenant_sort_by",
                )

            # Filtrar dados
            filtered_tenants = self._filter_tenants(
                tenants, status_filter, plan_filter, verified_filter
            )

            # Exibir baseado no modo selecionado
            if view_mode == "Tabela":
                self._render_tenants_table(filtered_tenants)
            else:
                self._render_tenants_cards(filtered_tenants)

            # Exibir ações rápidas
            self._render_tenant_actions(filtered_tenants)

        except Exception as e:
            show_error(f"Erro ao carregar tenants: {str(e)}")

    def _render_create_tenant(self):
        """Renderizar formulário de criação de tenant"""
        st.subheader("🆕 Criar Novo Tenant")

        with st.form("create_tenant"):
            # Informações básicas
            st.markdown("### 📝 Informações Básicas")
            col1, col2 = st.columns(2)

            with col1:
                name = st.text_input(
                    "Nome do Tenant *",
                    placeholder="Ex: Empresa ABC",
                    help="Nome da empresa ou organização",
                )

                slug = st.text_input(
                    "Slug *",
                    placeholder="empresa-abc",
                    help="Identificador único (URL-friendly)",
                )

                contact_email = st.text_input(
                    "Email de Contato *", placeholder="admin@empresa.com"
                )

            with col2:
                description = st.text_area(
                    "Descrição", placeholder="Descrição do tenant...", height=100
                )

                website = st.text_input("Website", placeholder="https://empresa.com")

                phone = st.text_input("Telefone", placeholder="+55 11 99999-9999")

            # Configurações do plano
            st.markdown("### 💼 Plano e Limites")
            col1, col2, col3 = st.columns(3)

            with col1:
                plan_type = st.selectbox(
                    "Tipo de Plano", ["free", "basic", "premium", "enterprise"], index=0
                )

                max_users = st.number_input(
                    "Máximo de Usuários",
                    min_value=1,
                    max_value=10000,
                    value=self._get_default_max_users(plan_type),
                )

            with col2:
                max_api_keys = st.number_input(
                    "Máximo de API Keys",
                    min_value=1,
                    max_value=1000,
                    value=self._get_default_max_api_keys(plan_type),
                )

                max_storage_mb = st.number_input(
                    "Storage (MB)",
                    min_value=100,
                    max_value=100000,
                    value=self._get_default_storage(plan_type),
                )

            with col3:
                is_active = st.checkbox("Ativar imediatamente", value=True)
                is_verified = st.checkbox("Marcar como verificado", value=False)
                allow_registration = st.checkbox("Permitir auto-registro", value=True)

            # Configurações avançadas
            st.markdown("### ⚙️ Configurações Avançadas")
            col1, col2 = st.columns(2)

            with col1:
                require_email_verification = st.checkbox(
                    "Exigir verificação de email", value=True
                )
                enforce_2fa = st.checkbox("Forçar 2FA para todos usuários", value=False)

            with col2:
                custom_domain = st.text_input(
                    "Domínio Customizado", placeholder="tenant.meuapp.com"
                )

                timezone = st.selectbox(
                    "Timezone",
                    ["America/Sao_Paulo", "UTC", "America/New_York", "Europe/London"],
                    index=0,
                )

            # Botão de criação
            st.markdown("---")
            submitted = st.form_submit_button("🏢 Criar Tenant", type="primary")

            if submitted and name and slug and contact_email:
                self._create_tenant(
                    {
                        "name": name,
                        "slug": slug,
                        "description": description,
                        "contact_email": contact_email,
                        "website": website,
                        "phone": phone,
                        "plan_type": plan_type,
                        "max_users": max_users,
                        "max_api_keys": max_api_keys,
                        "max_storage_mb": max_storage_mb,
                        "is_active": is_active,
                        "is_verified": is_verified,
                        "custom_domain": custom_domain,
                        "timezone": timezone,
                        "settings": {
                            "allow_registration": allow_registration,
                            "require_email_verification": require_email_verification,
                            "enforce_2fa": enforce_2fa,
                        },
                    }
                )
            elif submitted:
                st.error("❌ Campos obrigatórios: Nome, Slug e Email de Contato")

    def _render_tenant_settings(self):
        """Renderizar configurações específicas de um tenant"""
        st.subheader("⚙️ Configurações do Tenant")

        # Seletor de tenant
        try:
            response = self.api_client.get("/tenants")
            if response:
                tenants = response

                if not tenants:
                    st.info("🏢 Nenhum tenant disponível")
                    return

                selected_tenant = st.selectbox(
                    "Selecionar Tenant",
                    options=[f"{t['name']} (ID: {t['id']})" for t in tenants],
                    key="settings_tenant_select",
                )

                if selected_tenant:
                    tenant_id = int(selected_tenant.split("ID: ")[1].split(")")[0])
                    tenant = next((t for t in tenants if t["id"] == tenant_id), None)

                    if tenant:
                        self._render_tenant_settings_form(tenant)

        except Exception as e:
            show_error(f"Erro ao carregar tenants: {str(e)}")

    def _render_analytics(self):
        """Renderizar analytics dos tenants"""
        st.subheader("📊 Analytics de Tenants")

        try:
            # Buscar estatísticas
            stats = self.api_client.get("/tenants/analytics/")

            # Métricas principais
            col1, col2, col3, col4 = st.columns(4)

            with col1:
                total_tenants = stats.get("total_tenants", 0) or 0
                new_tenants = stats.get("new_tenants_this_month", 0) or 0
                st.metric("Total Tenants", total_tenants, delta=new_tenants)

            with col2:
                active_tenants = stats.get("active_tenants", 0) or 0
                active_percentage = stats.get("active_percentage", 0) or 0
                st.metric(
                    "Tenants Ativos",
                    active_tenants,
                    delta=f"{active_percentage:.1f}%",
                )

            with col3:
                total_users = stats.get("total_users", 0) or 0
                new_users = stats.get("new_users_this_month", 0) or 0
                st.metric("Total Usuários", total_users, delta=new_users)

            with col4:
                monthly_revenue = stats.get("monthly_revenue", 0) or 0
                revenue_growth = stats.get("revenue_growth", 0) or 0
                st.metric(
                    "Receita Mensal",
                    f"R$ {monthly_revenue:,.2f}",
                    delta=f"R$ {revenue_growth:,.2f}",
                )

            # Gráficos
            col1, col2 = st.columns(2)

            with col1:
                st.markdown("### 📈 Crescimento de Tenants")
                try:
                    growth_data = stats.get("tenant_growth_data", [])
                    if growth_data and isinstance(growth_data, list) and len(growth_data) > 0:
                        # Verificar se o primeiro item tem as chaves necessárias
                        first_item = growth_data[0]
                        if isinstance(first_item, dict) and "date" in first_item and "tenants" in first_item:
                            growth_df = pd.DataFrame(growth_data)
                            # Converter date para datetime para melhor visualização
                            growth_df['date'] = pd.to_datetime(growth_df['date'])
                            st.line_chart(growth_df.set_index("date")["tenants"])
                        else:
                            st.info("📊 Formato de dados de crescimento inválido")
                    else:
                        st.info("📊 Dados de crescimento não disponíveis")
                except Exception as e:
                    st.error(f"Erro ao carregar gráfico de crescimento: {str(e)}")

            with col2:
                st.markdown("### 📊 Distribuição por Plano")
                try:
                    plan_data = stats.get("plan_distribution", [])
                    if plan_data and isinstance(plan_data, list) and len(plan_data) > 0:
                        # Verificar se o primeiro item tem as chaves necessárias
                        first_item = plan_data[0]
                        if isinstance(first_item, dict) and "plan" in first_item and "count" in first_item:
                            plan_df = pd.DataFrame(plan_data)
                            st.bar_chart(plan_df.set_index("plan")["count"])
                        else:
                            st.info("📊 Formato de dados de distribuição inválido")
                    else:
                        st.info("📊 Dados de distribuição não disponíveis")
                except Exception as e:
                    st.error(f"Erro ao carregar gráfico de distribuição: {str(e)}")

            # Tabela de top tenants
            st.markdown("### 🏆 Top Tenants por Atividade")
            try:
                top_tenants_data = stats.get("top_tenants", [])
                if top_tenants_data and isinstance(top_tenants_data, list) and len(top_tenants_data) > 0:
                    # Verificar se os dados têm a estrutura esperada
                    first_item = top_tenants_data[0]
                    if isinstance(first_item, dict) and "name" in first_item:
                        top_df = pd.DataFrame(top_tenants_data)
                        if not top_df.empty:
                            # Renomear colunas para português
                            top_df = top_df.rename(columns={
                                "name": "Nome do Tenant",
                                "users": "Usuários"
                            })
                            st.dataframe(top_df, use_container_width=True)
                        else:
                            st.info("📊 Nenhum tenant disponível para exibir")
                    else:
                        st.info("📊 Formato de dados dos top tenants inválido")
                else:
                    st.info("📊 Nenhum tenant disponível para exibir")
            except Exception as e:
                st.error(f"Erro ao carregar tabela de top tenants: {str(e)}")

        except Exception as e:
            show_error(f"Erro ao carregar analytics: {str(e)}")

    def _render_tenant_users(self):
        """Renderizar usuários de um tenant específico"""
        st.subheader("👥 Usuários por Tenant")

        # Seletor de tenant
        try:
            tenants = self.api_client.get("/tenants/")

            if not tenants:
                st.info("🏢 Nenhum tenant disponível")
                return

            selected_tenant = st.selectbox(
                "Selecionar Tenant",
                options=[f"{t['name']} (ID: {t['id']})" for t in tenants],
                key="users_tenant_select",
            )

            if selected_tenant:
                tenant_id = int(selected_tenant.split("ID: ")[1].split(")")[0])

                # Buscar usuários do tenant
                users = self.api_client.get(f"/tenants/{tenant_id}/users")

                if users:
                    # Exibir estatísticas rápidas
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Total Usuários", len(users))
                    with col2:
                        active_users = len(
                            [u for u in users if u.get("is_active")]
                        )
                        st.metric("Usuários Ativos", active_users)
                    with col3:
                        admin_users = len(
                            [u for u in users if u.get("is_superuser")]
                        )
                        st.metric("Administradores", admin_users)

                    # Tabela de usuários
                    users_df = pd.DataFrame(
                        [
                            {
                                "ID": u.get("id"),
                                "Nome": u.get("full_name", u.get("username")),
                                "Email": u.get("email"),
                                "Status": (
                                    "🟢 Ativo"
                                    if u.get("is_active")
                                    else "🔴 Inativo"
                                ),
                                "Admin": "👑" if u.get("is_superuser") else "",
                                "Último Login": format_datetime(
                                    u.get("last_login")
                                ),
                                "Criado em": format_datetime(
                                    u.get("created_at")
                                ),
                            }
                            for u in users
                        ]
                    )

                    st.dataframe(users_df, use_container_width=True)
                else:
                    st.info("👤 Nenhum usuário encontrado neste tenant")

        except Exception as e:
            show_error(f"Erro ao carregar usuários: {str(e)}")

    def _render_tenants_table(self, tenants: List[Dict]):
        """Renderizar tabela de tenants"""
        if not tenants:
            st.info("🔍 Nenhum tenant encontrado com os filtros aplicados")
            return

        # Criar DataFrame
        df = pd.DataFrame(
            [
                {
                    "ID": t.get("id"),
                    "Nome": t.get("name"),
                    "Slug": t.get("slug"),
                    "Plano": t.get("plan_type", "N/A").upper(),
                    "Usuários": f"{t.get('user_count', 0)}/{t.get('max_users', 0)}",
                    "API Keys": f"{t.get('api_key_count', 0)}/{t.get('max_api_keys', 0)}",
                    "Status": "🟢 Ativo" if t.get("is_active") else "🔴 Inativo",
                    "Verificado": "✅" if t.get("is_verified") else "⏳",
                    "Criado em": format_datetime(t.get("created_at")),
                }
                for t in tenants
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
                "Verificado": st.column_config.CheckboxColumn(
                    "Verificado", width="small"
                ),
            },
            disabled=[
                "ID",
                "Nome",
                "Slug",
                "Plano",
                "Usuários",
                "API Keys",
                "Criado em",
            ],
            key="tenants_table",
        )

    def _render_tenants_cards(self, tenants: List[Dict]):
        """Renderizar cards de tenants"""
        cols = st.columns(2)

        for i, tenant in enumerate(tenants):
            with cols[i % 2]:
                with st.container():
                    # Header do card
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.markdown(f"### 🏢 {tenant.get('name')}")
                        st.caption(f"Slug: {tenant.get('slug')}")

                    with col2:
                        status_icon = "🟢" if tenant.get("is_active") else "🔴"
                        verified_icon = "✅" if tenant.get("is_verified") else "⏳"
                        st.markdown(f"{status_icon} {verified_icon}")

                    # Informações principais
                    st.markdown(f"**Plano:** {tenant.get('plan_type', 'N/A').upper()}")
                    st.markdown(f"**Email:** {tenant.get('contact_email')}")

                    # Métricas
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric(
                            "Usuários",
                            f"{tenant.get('user_count', 0)}/{tenant.get('max_users', 0)}",
                        )
                    with col2:
                        st.metric(
                            "API Keys",
                            f"{tenant.get('api_key_count', 0)}/{tenant.get('max_api_keys', 0)}",
                        )

                    # Ações
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        if st.button("⚙️ Config", key=f"config_{tenant['id']}"):
                            st.session_state.selected_tenant_config = tenant["id"]
                    with col2:
                        if st.button("👥 Users", key=f"users_{tenant['id']}"):
                            st.session_state.selected_tenant_users = tenant["id"]
                    with col3:
                        if st.button("📊 Stats", key=f"stats_{tenant['id']}"):
                            st.session_state.selected_tenant_stats = tenant["id"]

                    st.markdown("---")

    def _filter_tenants(
        self,
        tenants: List[Dict],
        status_filter: str,
        plan_filter: str,
        verified_filter: str,
    ) -> List[Dict]:
        """Filtrar tenants baseado nos filtros selecionados"""
        filtered = tenants.copy()

        # Filtro por status
        if status_filter != "Todos":
            if status_filter == "Ativo":
                filtered = [t for t in filtered if t.get("is_active", False)]
            elif status_filter == "Inativo":
                filtered = [t for t in filtered if not t.get("is_active", False)]

        # Filtro por plano
        if plan_filter != "Todos":
            filtered = [t for t in filtered if t.get("plan_type") == plan_filter]

        # Filtro por verificação
        if verified_filter != "Todos":
            if verified_filter == "Verificado":
                filtered = [t for t in filtered if t.get("is_verified", False)]
            elif verified_filter == "Não Verificado":
                filtered = [t for t in filtered if not t.get("is_verified", False)]

        return filtered

    def _get_default_max_users(self, plan_type: str) -> int:
        """Obter limite padrão de usuários por plano"""
        limits = {"free": 5, "basic": 25, "premium": 100, "enterprise": 1000}
        return limits.get(plan_type, 5)

    def _get_default_max_api_keys(self, plan_type: str) -> int:
        """Obter limite padrão de API keys por plano"""
        limits = {"free": 2, "basic": 10, "premium": 50, "enterprise": 200}
        return limits.get(plan_type, 2)

    def _get_default_storage(self, plan_type: str) -> int:
        """Obter limite padrão de storage por plano"""
        limits = {"free": 100, "basic": 1000, "premium": 10000, "enterprise": 100000}
        return limits.get(plan_type, 100)

    def _render_tenant_settings_form(self, tenant: Dict):
        """Renderizar formulário de configurações do tenant"""
        st.markdown(f"### ⚙️ Configurações: {tenant['name']}")

        with st.form(f"tenant_settings_{tenant['id']}"):
            # Configurações básicas
            col1, col2 = st.columns(2)

            with col1:
                is_active = st.checkbox(
                    "Tenant Ativo", value=tenant.get("is_active", False)
                )
                is_verified = st.checkbox(
                    "Tenant Verificado", value=tenant.get("is_verified", False)
                )
                allow_registration = st.checkbox("Permitir Auto-Registro", value=True)

            with col2:
                require_email_verification = st.checkbox(
                    "Exigir Verificação Email", value=True
                )
                enforce_2fa = st.checkbox("Forçar 2FA", value=False)
                maintenance_mode = st.checkbox("Modo Manutenção", value=False)

            # Limites
            col1, col2, col3 = st.columns(3)
            with col1:
                max_users = st.number_input(
                    "Máx. Usuários", value=tenant.get("max_users", 10)
                )
            with col2:
                max_api_keys = st.number_input(
                    "Máx. API Keys", value=tenant.get("max_api_keys", 5)
                )
            with col3:
                max_storage_mb = st.number_input(
                    "Storage (MB)", value=tenant.get("max_storage_mb", 1000)
                )

            if st.form_submit_button("💾 Salvar Configurações"):
                self._update_tenant_settings(
                    tenant["id"],
                    {
                        "is_active": is_active,
                        "is_verified": is_verified,
                        "max_users": max_users,
                        "max_api_keys": max_api_keys,
                        "max_storage_mb": max_storage_mb,
                        "settings": {
                            "allow_registration": allow_registration,
                            "require_email_verification": require_email_verification,
                            "enforce_2fa": enforce_2fa,
                            "maintenance_mode": maintenance_mode,
                        },
                    },
                )

    def _render_tenant_actions(self, tenants: List[Dict]):
        """Renderizar ações para tenants"""
        if not tenants:
            return

        st.markdown("### ⚡ Ações Rápidas")

        selected_tenant = st.selectbox(
            "Selecionar Tenant para Ação",
            options=[f"{t['name']} (ID: {t['id']})" for t in tenants],
            key="action_tenant_select",
        )

        if selected_tenant:
            tenant_id = int(selected_tenant.split("ID: ")[1].split(")")[0])

            # Limpar flags antigas (mais de 30 segundos) e de outros tenants
            import time
            current_time = time.time()
            keys_to_remove = []
            
            for session_key in list(st.session_state.keys()):
                if session_key.startswith(("confirm_delete_tenant_", "delete_clicked_tenant_", "delete_timestamp_tenant_")):
                    try:
                        session_tenant_id = int(session_key.split("_")[-1])
                        # Se não é o tenant atual, limpar
                        if session_tenant_id != tenant_id:
                            keys_to_remove.append(session_key)
                        # Se é timestamp antigo (>30 segundos), limpar
                        elif session_key.startswith("delete_timestamp_tenant_"):
                            timestamp = st.session_state.get(session_key, 0)
                            if current_time - timestamp > 30:  # 30 segundos
                                keys_to_remove.extend([
                                    f"confirm_delete_tenant_{session_tenant_id}",
                                    f"delete_clicked_tenant_{session_tenant_id}",
                                    f"delete_timestamp_tenant_{session_tenant_id}"
                                ])
                    except (ValueError, IndexError):
                        keys_to_remove.append(session_key)
            
            for key in keys_to_remove:
                if key in st.session_state:
                    del st.session_state[key]

            col1, col2, col3, col4 = st.columns(4)

            with col1:
                if st.button("✅ Verificar", key=f"verify_{tenant_id}"):
                    self._verify_tenant(tenant_id)

            with col2:
                if st.button("⏸️ Suspender", key=f"suspend_{tenant_id}"):
                    self._suspend_tenant(tenant_id)

            with col3:
                if st.button("🔄 Reativar", key=f"activate_{tenant_id}"):
                    self._activate_tenant(tenant_id)

            with col4:
                if st.button("🗑️ Deletar", key=f"delete_tenant_{tenant_id}", type="secondary"):
                    # Marcar que o delete foi clicado especificamente agora
                    st.session_state[f"delete_clicked_tenant_{tenant_id}"] = True
                    st.session_state[f"confirm_delete_tenant_{tenant_id}"] = True
                    st.session_state[f"delete_timestamp_tenant_{tenant_id}"] = current_time
                    st.rerun()
            
            # Mostrar confirmação APENAS se o delete foi clicado recentemente
            show_confirmation = (
                st.session_state.get(f"confirm_delete_tenant_{tenant_id}", False) and 
                st.session_state.get(f"delete_clicked_tenant_{tenant_id}", False) and
                (current_time - st.session_state.get(f"delete_timestamp_tenant_{tenant_id}", 0)) <= 30  # 30 segundos
            )
            
            if show_confirmation:
                st.warning("⚠️ **ATENÇÃO**: Esta ação não pode ser desfeita! Todos os dados do tenant serão perdidos.")
                col_yes, col_no = st.columns(2)
                
                with col_yes:
                    if st.button("✅ Sim, deletar tenant", key=f"confirm_yes_tenant_{tenant_id}", type="primary"):
                        self._execute_delete_tenant(tenant_id)
                        # Limpar flags de confirmação
                        st.session_state[f"confirm_delete_tenant_{tenant_id}"] = False
                        st.session_state[f"delete_clicked_tenant_{tenant_id}"] = False
                        st.session_state[f"delete_timestamp_tenant_{tenant_id}"] = 0
                        
                with col_no:
                    if st.button("❌ Cancelar", key=f"confirm_no_tenant_{tenant_id}"):
                        # Limpar flags de confirmação
                        st.session_state[f"confirm_delete_tenant_{tenant_id}"] = False
                        st.session_state[f"delete_clicked_tenant_{tenant_id}"] = False
                        st.session_state[f"delete_timestamp_tenant_{tenant_id}"] = 0
                        st.rerun()

    def _create_tenant(self, data: Dict):
        """Criar novo tenant"""
        try:
            response = self.api_client.post("/tenants", data)
            if response:
                show_success("🎉 Tenant criado com sucesso!")
                time.sleep(1)
                st.rerun()
        except Exception as e:
            show_error(f"Erro ao criar tenant: {str(e)}")

    def _update_tenant_settings(self, tenant_id: int, data: Dict):
        """Atualizar configurações do tenant"""
        try:
            response = self.api_client.put(f"/tenants/{tenant_id}", data)
            if response:
                show_success("✅ Configurações atualizadas com sucesso!")
        except Exception as e:
            show_error(f"Erro ao atualizar configurações: {str(e)}")

    def _verify_tenant(self, tenant_id: int):
        """Verificar tenant"""
        try:
            response = self.api_client.post(f"/tenants/{tenant_id}/verify")
            if response:
                show_success("✅ Tenant verificado com sucesso!")
                st.rerun()
        except Exception as e:
            show_error(f"Erro ao verificar tenant: {str(e)}")

    def _suspend_tenant(self, tenant_id: int):
        """Suspender tenant"""
        try:
            response = self.api_client.post(f"/tenants/{tenant_id}/suspend")
            if response:
                show_success("⏸️ Tenant suspenso com sucesso!")
                st.rerun()
        except Exception as e:
            show_error(f"Erro ao suspender tenant: {str(e)}")

    def _activate_tenant(self, tenant_id: int):
        """Reativar tenant"""
        try:
            response = self.api_client.post(f"/tenants/{tenant_id}/activate")
            if response:
                show_success("🔄 Tenant reativado com sucesso!")
                st.rerun()
        except Exception as e:
            show_error(f"Erro ao reativar tenant: {str(e)}")

    def _execute_delete_tenant(self, tenant_id: int):
        """Executar a exclusão definitiva do tenant"""
        try:
            st.info(f"🔄 Deletando tenant ID: {tenant_id}...")
            response = self.api_client.delete(f"/tenants/{tenant_id}")
            if response:
                show_success("🗑️ Tenant deletado com sucesso!")
                time.sleep(1)
                st.rerun()
            else:
                show_error("❌ Erro ao deletar tenant")
        except Exception as e:
            show_error(f"Erro ao deletar tenant: {str(e)}")


def render_tenants_view():
    """Função principal para renderizar a view de Tenants"""
    api_client = APIClient()
    view = TenantsView(api_client)
    view.render()
