"""
Interface para gerenciamento de API Keys
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
from front.utils.helpers import format_datetime, show_error, show_success, show_warning, safe_json_loads


class APIKeysView:
    """View para gerenciamento de API Keys"""

    def __init__(self, api_client: APIClient):
        self.api_client = api_client

    def render(self):
        """Renderizar a interface de API Keys"""
        st.title("🔑 Gerenciamento de API Keys")
        st.markdown("---")

        # Verificar autenticação
        if not st.session_state.get("token"):
            st.error("🚫 Você precisa estar logado para acessar esta página")
            return

        # Tabs principais
        tab1, tab2, tab3, tab4 = st.tabs(
            [
                "📋 Listar API Keys",
                "🆕 Criar Nova",
                "📊 Estatísticas",
                "⚙️ Configurações",
            ]
        )

        with tab1:
            self._render_list_keys()

        with tab2:
            self._render_create_key()

        with tab3:
            self._render_statistics()

        with tab4:
            self._render_settings()

    def _render_list_keys(self):
        """Renderizar lista de API Keys"""
        st.subheader("📋 Suas API Keys")

        # Botão de atualizar
        col1, col2 = st.columns([1, 4])
        with col1:
            if st.button("🔄 Atualizar", key="refresh_keys"):
                st.rerun()

        # Buscar API Keys
        try:
            api_keys = self.api_client.get("/api-keys/")

            if not api_keys:
                st.info("📝 Nenhuma API Key encontrada. Crie sua primeira!")
                return

            # Filtros
            st.markdown("### 🔍 Filtros")
            col1, col2, col3 = st.columns(3)

            with col1:
                status_filter = st.selectbox(
                    "Status",
                    ["Todos", "Ativa", "Inativa", "Expirada"],
                    key="status_filter",
                )

            with col2:
                scope_filter = st.selectbox(
                    "Escopo",
                    ["Todos", "read", "write", "admin", "delete"],
                    key="scope_filter",
                )

            with col3:
                sort_by = st.selectbox(
                    "Ordenar por",
                    ["Nome", "Data Criação", "Último Uso", "Expira em"],
                    key="sort_by",
                )

            # Processar e filtrar dados
            filtered_keys = self._filter_api_keys(api_keys, status_filter, scope_filter)

            # Exibir tabela
            if filtered_keys:
                df = self._create_keys_dataframe(filtered_keys)

                # Configurar colunas editáveis
                edited_df = st.data_editor(
                    df,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "Ações": st.column_config.Column(
                            "Ações",
                            width="medium",
                        ),
                        "Status": st.column_config.Column(
                            "Status",
                            width="small",
                        ),
                        "Uso": st.column_config.ProgressColumn(
                            "Uso",
                            help="Uso atual vs limite",
                            min_value=0,
                            max_value=100,
                            format="%.0f%%",
                        ),
                    },
                    disabled=[
                        "ID",
                        "Nome",
                        "Prefixo",
                        "Status",
                        "Escopos",
                        "Criada em",
                        "Último uso",
                        "Expira em",
                        "Ações",
                    ],
                    key="api_keys_table",
                )

                # Processar ações
                self._handle_key_actions(filtered_keys)
            else:
                st.info("🔍 Nenhuma API Key encontrada com os filtros aplicados")

        except Exception as e:
            show_error(f"Erro ao carregar API Keys: {str(e)}")

    def _render_create_key(self):
        """Renderizar formulário de criação de API Key"""
        st.subheader("🆕 Criar Nova API Key")

        with st.form("create_api_key"):
            # Informações básicas
            st.markdown("### 📝 Informações Básicas")
            col1, col2 = st.columns(2)

            with col1:
                name = st.text_input(
                    "Nome da API Key *",
                    placeholder="Ex: Frontend Dashboard",
                    help="Nome descritivo para identificar esta API Key",
                )

                description = st.text_area(
                    "Descrição",
                    placeholder="Descreva o propósito desta API Key...",
                    height=100,
                )

            with col2:
                tenant_id = st.number_input(
                    "Tenant ID",
                    min_value=1,
                    value=1,
                    help="ID do tenant (deixe 1 para tenant padrão)",
                )

                expires_in_days = st.number_input(
                    "Expira em (dias)",
                    min_value=1,
                    max_value=365,
                    value=90,
                    help="Número de dias até a expiração",
                )

            # Permissões e escopos
            st.markdown("### 🔐 Permissões e Escopos")
            col1, col2 = st.columns(2)

            with col1:
                st.markdown("**Escopos:**")
                scopes = []
                if st.checkbox("📖 Read (Leitura)", value=True):
                    scopes.append("read")
                if st.checkbox("✏️ Write (Escrita)"):
                    scopes.append("write")
                if st.checkbox("🗑️ Delete (Exclusão)"):
                    scopes.append("delete")
                if st.checkbox("👑 Admin (Administrador)"):
                    scopes.append("admin")

            with col2:
                st.markdown("**Permissões Específicas:**")
                permissions = []
                if st.checkbox("users:read"):
                    permissions.append("users:read")
                if st.checkbox("users:write"):
                    permissions.append("users:write")
                if st.checkbox("admin:manage"):
                    permissions.append("admin:manage")
                if st.checkbox("api:manage"):
                    permissions.append("api:manage")

            # Configurações avançadas
            st.markdown("### ⚙️ Configurações Avançadas")
            col1, col2 = st.columns(2)

            with col1:
                rate_limit = st.number_input(
                    "Rate Limit (req/min)",
                    min_value=10,
                    max_value=10000,
                    value=1000,
                    help="Número máximo de requisições por minuto",
                )

            with col2:
                is_active = st.checkbox("Ativar imediatamente", value=True)

            # Botão de criação
            st.markdown("---")
            submitted = st.form_submit_button("🔑 Criar API Key", type="primary")

            if submitted and name:
                self._create_api_key(
                    {
                        "name": name,
                        "description": description,
                        "tenant_id": tenant_id,
                        "scopes": scopes,
                        "permissions": permissions,
                        "rate_limit_per_minute": rate_limit,
                        "expires_in_days": expires_in_days,
                        "is_active": is_active,
                    }
                )
            elif submitted:
                st.error("❌ Nome da API Key é obrigatório")

    def _render_statistics(self):
        """Renderizar estatísticas das API Keys"""
        st.subheader("📊 Estatísticas de Uso")

        try:
            # Buscar estatísticas
            stats = self.api_client.get("/api-keys/stats/")

            # Métricas principais
            col1, col2, col3, col4 = st.columns(4)

            with col1:
                st.metric(
                    "Total de Keys",
                    stats.get("total_keys", 0),
                    delta=stats.get("new_keys_this_month", 0),
                )

            with col2:
                st.metric(
                    "Keys Ativas",
                    stats.get("active_keys", 0),
                    delta=f"{stats.get('active_percentage', 0):.1f}%",
                )

            with col3:
                st.metric(
                    "Requests Hoje",
                    stats.get("requests_today", 0),
                    delta=stats.get("requests_yesterday", 0),
                )

            with col4:
                st.metric(
                    "Rate Limit Hits",
                    stats.get("rate_limit_hits", 0),
                    delta=stats.get("rate_limit_hits_yesterday", 0),
                )

            # Gráficos
            if stats.get("usage_data"):
                st.markdown("### 📈 Uso ao Longo do Tempo")

                usage_df = pd.DataFrame(stats["usage_data"])
                st.line_chart(usage_df.set_index("date"))

            # Top API Keys
            if stats.get("top_keys"):
                st.markdown("### 🏆 Top API Keys (por uso)")
                top_df = pd.DataFrame(stats["top_keys"])
                st.dataframe(top_df, use_container_width=True)

        except Exception as e:
            show_error(f"Erro ao carregar estatísticas: {str(e)}")

    def _render_settings(self):
        """Renderizar configurações globais de API Keys"""
        st.subheader("⚙️ Configurações Globais")

        # Configurações de segurança
        st.markdown("### 🔒 Segurança")

        col1, col2 = st.columns(2)
        with col1:
            max_keys_per_user = st.number_input(
                "Máximo de Keys por Usuário", min_value=1, max_value=100, value=10
            )

            default_expiry_days = st.number_input(
                "Expiração Padrão (dias)", min_value=1, max_value=365, value=90
            )

        with col2:
            auto_rotate = st.checkbox("Auto-rotação de Keys")
            require_2fa = st.checkbox("Exigir 2FA para criar Keys")

        # Configurações de rate limiting
        st.markdown("### 🚦 Rate Limiting")

        col1, col2 = st.columns(2)
        with col1:
            global_rate_limit = st.number_input(
                "Rate Limit Global (req/min)",
                min_value=100,
                max_value=100000,
                value=10000,
            )

        with col2:
            burst_limit = st.number_input(
                "Burst Limit", min_value=10, max_value=1000, value=100
            )

        if st.button("💾 Salvar Configurações"):
            # Implementar salvamento de configurações
            show_success("Configurações salvas com sucesso!")

    def _filter_api_keys(
        self, api_keys: List[Dict], status_filter: str, scope_filter: str
    ) -> List[Dict]:
        """Filtrar API Keys baseado nos filtros selecionados"""
        filtered = api_keys.copy()

        # Filtro por status
        if status_filter != "Todos":
            if status_filter == "Ativa":
                filtered = [k for k in filtered if k.get("is_active", False)]
            elif status_filter == "Inativa":
                filtered = [k for k in filtered if not k.get("is_active", False)]
            elif status_filter == "Expirada":
                current_time = datetime.now()
                filtered = [
                    k
                    for k in filtered
                    if k.get("expires_at")
                    and datetime.fromisoformat(k["expires_at"].replace("Z", "+00:00"))
                    < current_time
                ]

        # Filtro por escopo
        if scope_filter != "Todos":
            filtered = [k for k in filtered if scope_filter in k.get("scopes", "")]

        return filtered

    def _create_keys_dataframe(self, api_keys: List[Dict]) -> pd.DataFrame:
        """Criar DataFrame para exibição das API Keys"""
        data = []

        for key in api_keys:
            # Calcular status
            status = "🟢 Ativa" if key.get("is_active") else "🔴 Inativa"

            # Verificar expiração
            if key.get("expires_at"):
                expires_at = datetime.fromisoformat(
                    key["expires_at"].replace("Z", "+00:00")
                )
                if expires_at < datetime.now():
                    status = "⏰ Expirada"

            # Calcular uso (mockado por enquanto)
            usage_percent = min(
                100,
                key.get("usage_count", 0)
                / max(1, key.get("rate_limit_per_minute", 1000))
                * 100,
            )

            scopes_raw = key.get("scopes")
            scopes_parsed = safe_json_loads(scopes_raw, [])

            data.append(
                {
                    "ID": key.get("id"),
                    "Nome": key.get("name"),
                    "Prefixo": key.get("key_prefix", "N/A"),
                    "Status": status,
                    "Escopos": ", ".join(scopes_parsed),
                    "Uso": usage_percent,
                    "Criada em": format_datetime(key.get("created_at")),
                    "Último uso": (
                        format_datetime(key.get("last_used_at"))
                        if key.get("last_used_at")
                        else "Nunca"
                    ),
                    "Expira em": (
                        format_datetime(key.get("expires_at"))
                        if key.get("expires_at")
                        else "Nunca"
                    ),
                    "Ações": "🔧",
                }
            )

        return pd.DataFrame(data)

    def _handle_key_actions(self, api_keys: List[Dict]):
        """Processar ações nas API Keys"""
        st.markdown("### ⚡ Ações Rápidas")

        selected_key = st.selectbox(
            "Selecionar API Key",
            options=[f"{key['name']} (ID: {key['id']})" for key in api_keys],
            index=0 if api_keys else None,
            key="selected_api_key"
        )

        if selected_key and api_keys:
            key_id = int(selected_key.split("ID: ")[1].split(")")[0])

            # Limpar flags antigas (mais de 30 segundos) e de outras keys
            import time
            current_time = time.time()
            keys_to_remove = []
            
            for session_key in list(st.session_state.keys()):
                if session_key.startswith(("confirm_delete_", "delete_clicked_", "delete_timestamp_")):
                    try:
                        session_key_id = int(session_key.split("_")[-1])
                        # Se não é a key atual, limpar
                        if session_key_id != key_id:
                            keys_to_remove.append(session_key)
                        # Se é timestamp antigo (>30 segundos), limpar
                        elif session_key.startswith("delete_timestamp_"):
                            timestamp = st.session_state.get(session_key, 0)
                            if current_time - timestamp > 30:  # 30 segundos
                                keys_to_remove.extend([
                                    f"confirm_delete_{session_key_id}",
                                    f"delete_clicked_{session_key_id}",
                                    f"delete_timestamp_{session_key_id}"
                                ])
                    except (ValueError, IndexError):
                        keys_to_remove.append(session_key)
            
            for key in keys_to_remove:
                if key in st.session_state:
                    del st.session_state[key]

            col1, col2, col3, col4 = st.columns(4)

            with col1:
                if st.button("🔄 Regenerar", key=f"regen_{key_id}"):
                    self._regenerate_key(key_id)

            with col2:
                if st.button("⏸️ Desativar", key=f"deactivate_{key_id}"):
                    self._toggle_key_status(key_id, False)

            with col3:
                if st.button("▶️ Ativar", key=f"activate_{key_id}"):
                    self._toggle_key_status(key_id, True)

            with col4:
                if st.button("🗑️ Deletar", key=f"delete_{key_id}", type="secondary"):
                    # Marcar que o delete foi clicado especificamente agora
                    st.session_state[f"delete_clicked_{key_id}"] = True
                    st.session_state[f"confirm_delete_{key_id}"] = True
                    st.session_state[f"delete_timestamp_{key_id}"] = current_time
                    st.rerun()
            
            # Mostrar confirmação APENAS se o delete foi clicado recentemente
            show_confirmation = (
                st.session_state.get(f"confirm_delete_{key_id}", False) and 
                st.session_state.get(f"delete_clicked_{key_id}", False) and
                (current_time - st.session_state.get(f"delete_timestamp_{key_id}", 0)) <= 30  # 30 segundos
            )
            
            if show_confirmation:
                st.warning("⚠️ **ATENÇÃO**: Esta ação não pode ser desfeita!")
                col_yes, col_no = st.columns(2)
                
                with col_yes:
                    if st.button("✅ Sim, deletar", key=f"confirm_yes_{key_id}", type="primary"):
                        self._execute_delete_key(key_id)
                        # Limpar flags de confirmação
                        st.session_state[f"confirm_delete_{key_id}"] = False
                        st.session_state[f"delete_clicked_{key_id}"] = False
                        st.session_state[f"delete_timestamp_{key_id}"] = 0
                        
                with col_no:
                    if st.button("❌ Cancelar", key=f"confirm_no_{key_id}"):
                        # Limpar flags de confirmação
                        st.session_state[f"confirm_delete_{key_id}"] = False
                        st.session_state[f"delete_clicked_{key_id}"] = False
                        st.session_state[f"delete_timestamp_{key_id}"] = 0
                        st.rerun()

    def _create_api_key(self, data: Dict):
        """Criar nova API Key"""
        try:
            response = self.api_client.post("/api-keys", data)
            if response:
                # O backend retorna APIKeyCreateResponse: {"api_key": {...}, "key": "..."}
                show_success("🎉 API Key criada com sucesso!")

                # Mostrar a key gerada (apenas uma vez)
                new_key = response.get("key")
                if new_key:
                    st.markdown("### 🔑 Sua Nova API Key")
                    st.code(new_key)
                    st.warning(
                        "⚠️ **IMPORTANTE**: Copie e salve esta key agora! Ela não será mostrada novamente."
                    )

                # Aguardar um pouco e recarregar
                time.sleep(2)
                st.rerun()
            else:
                show_error("Erro ao criar API Key")

        except Exception as e:
            show_error(f"Erro ao criar API Key: {str(e)}")

    def _regenerate_key(self, key_id: int):
        """Regenerar API Key"""
        try:
            st.info(f"🔄 Regenerando API Key ID: {key_id}...")
            response = self.api_client.post(f"/api-keys/{key_id}/rotate")
            
            if response:
                # O backend retorna APIKeyCreateResponse: {"api_key": {...}, "key": "..."}
                new_key = response.get("key")
                show_success("🔄 API Key regenerada com sucesso!")

                if new_key:
                    st.code(new_key)
                    st.warning(
                        "⚠️ A key anterior foi invalidada. Atualize suas aplicações!"
                    )
                
                time.sleep(2)
                st.rerun()
            else:
                show_error("❌ Erro ao regenerar API Key")
        except Exception as e:
            show_error(f"❌ Erro ao regenerar API Key: {str(e)}")

    def _toggle_key_status(self, key_id: int, active: bool):
        """Ativar/desativar API Key"""
        try:
            st.info(f"🔄 {'Ativando' if active else 'Desativando'} API Key ID: {key_id}...")
            
            # Usar endpoint PUT com is_active no corpo
            data = {"is_active": active}
            response = self.api_client.put(f"/api-keys/{key_id}", data)

            if response:
                status_text = "ativada" if active else "desativada"
                show_success(f"✅ API Key {status_text} com sucesso!")
                time.sleep(1)
                st.rerun()
            else:
                show_error(f"❌ Erro ao alterar status da API Key")
        except Exception as e:
            show_error(f"❌ Erro ao alterar status da API Key: {str(e)}")

    def _execute_delete_key(self, key_id: int):
        """Executar exclusão de API Key"""
        try:
            st.info(f"🔄 Deletando API Key ID: {key_id}...")
            response = self.api_client.delete(f"/api-keys/{key_id}")
            
            if response:
                show_success("🗑️ API Key deletada com sucesso!")
                time.sleep(1)
                st.rerun()
            else:
                show_error("❌ Erro ao deletar API Key")
        except Exception as e:
            show_error(f"❌ Erro ao deletar API Key: {str(e)}")


def render_api_keys_view():
    """Função principal para renderizar a view de API Keys"""
    api_client = APIClient()
    view = APIKeysView(api_client)
    view.render()
