import time

import streamlit as st

from front.services.auth_service import auth_service


def _get_sidebar_permissions():
    """Get permissions needed for sidebar navigation with caching"""
    # Use a simple cache key based on user ID and cache timestamp
    user = auth_service.get_current_user()
    if not user:
        return {}

    cache_key = f"sidebar_perms_{user.get('id', 'unknown')}"
    cache_timestamp_key = f"{cache_key}_timestamp"

    # Check if we have cached permissions and they're not expired (30 seconds cache)
    if (
        hasattr(st.session_state, cache_timestamp_key)
        and time.time() - st.session_state[cache_timestamp_key] < 30
        and hasattr(st.session_state, cache_key)
    ):
        return st.session_state[cache_key]

    # Batch check all permissions at once
    permissions = {
        "users_read": auth_service.has_permission_cached("users:read"),
        "roles_read": auth_service.has_permission_cached("roles:read"),
        "permissions_read": auth_service.has_permission_cached("permissions:read"),
        "logs_view": auth_service.has_permission_cached("logs:view"),
    }

    # Cache the results
    st.session_state[cache_key] = permissions
    st.session_state[cache_timestamp_key] = time.time()

    return permissions


def render_sidebar():
    """Render navigation sidebar"""
    with st.sidebar:
        st.markdown("# 🛡️ RBAC Admin")
        st.markdown("---")

        # Check if user is authenticated
        if not auth_service.is_authenticated():
            st.warning("Faça login para acessar o painel")
            return

        user = auth_service.get_current_user()

        # Proteção contra user None
        if not user:
            st.error("❌ Erro: Dados do usuário não encontrados")
            if st.button("🔄 Tentar Recarregar", use_container_width=True):
                st.rerun()
            if st.button("🚪 Logout e Login Novamente", use_container_width=True):
                auth_service.logout()
            return

        # Get cached permissions for sidebar
        perms = _get_sidebar_permissions()

        # Navigation menu
        st.markdown("### 📋 Navegação")

        # Dashboard (available to all authenticated users)
        if st.button("📊 Dashboard", use_container_width=True):
            st.session_state.page = "Dashboard"
            st.rerun()

        # Users management (requires users:read permission)
        if perms.get("users_read", False):
            if st.button("👥 Usuários", use_container_width=True):
                st.session_state.page = "Users"
                st.rerun()

        # Roles management (requires roles:read permission)
        if perms.get("roles_read", False):
            if st.button("🎭 Papéis", use_container_width=True):
                st.session_state.page = "Roles"
                st.rerun()

        # Permissions management (requires permissions:read permission)
        if perms.get("permissions_read", False):
            if st.button("🔐 Permissões", use_container_width=True):
                st.session_state.page = "Permissions"
                st.rerun()

        # Logs dashboard (requires logs:view permission)
        if perms.get("logs_view", False):
            if st.button("📊 Logs Monitor", use_container_width=True):
                st.session_state.page = "Logs"
                st.rerun()

        # Enterprise Features (Level 5)
        st.markdown("---")
        st.markdown("### 🏢 Enterprise (Nível 5)")
        
        # Verificar se usuário tem permissões para funcionalidades enterprise
        is_admin = user.get('is_superuser', False) or 'admin' in [r.lower() for r in auth_service.get_user_roles()]
        
        if is_admin:
            if st.button("🔑 API Keys", use_container_width=True):
                st.session_state.page = "API Keys"
                st.rerun()

            if st.button("🏢 Tenants", use_container_width=True):
                st.session_state.page = "Tenants"
                st.rerun()

            if st.button("🪝 Webhooks", use_container_width=True):
                st.session_state.page = "Webhooks"
                st.rerun()
        else:
            st.markdown("🔒 *Requer permissões de admin*")

        # Protected examples
        st.markdown("---")
        st.markdown("### 🧪 Exemplos")

        if st.button("📝 Posts", use_container_width=True):
            st.session_state.page = "Posts"
            st.rerun()

        if st.button("⚙️ Configurações", use_container_width=True):
            st.session_state.page = "Settings"
            st.rerun()

        # User info at bottom
        st.markdown("---")
        st.markdown("### 👤 Usuário")

        # User info
        st.markdown(f"**{user.get('full_name', 'N/A')}**")
        st.markdown(f"@{user.get('username')}")

        # Roles badges
        roles = auth_service.get_user_roles()
        if roles:
            st.markdown("**Papéis:**")
            role_colors = {
                "admin": "🔴",
                "manager": "🟠",
                "editor": "🔵",
                "viewer": "⚪",
            }

            for role in roles:
                color = role_colors.get(role, "⚫")
                st.markdown(f"{color} {role}")

        # OAuth provider info
        provider = user.get("provider", "basic")
        if provider != "basic":
            st.markdown(f"**Provedor:** {provider.title()}")

        # Quick stats
        permissions_count = len(auth_service.get_user_permissions())
        st.markdown(f"**Permissões:** {permissions_count}")

        # Permissions cache status
        st.markdown("---")
        st.markdown("### 🔄 Cache de Permissões")

        cache_info = auth_service.get_permissions_cache_info()

        if cache_info["cached"]:
            if cache_info["is_expired"]:
                st.markdown("🟡 **Status:** Expirado")
            else:
                st.markdown("🟢 **Status:** Ativo")
                minutes_left = int(cache_info["expires_in"] / 60)
                seconds_left = int(cache_info["expires_in"] % 60)
                st.markdown(f"⏱️ **Expira em:** {minutes_left}m {seconds_left}s")
        else:
            st.markdown("🔴 **Status:** Não cache")

        # Manual refresh button
        col1, col2 = st.columns(2)
        with col1:
            if st.button(
                "🔄 Atualizar",
                use_container_width=True,
                help="Atualizar permissões manualmente",
            ):
                with st.spinner("Atualizando..."):
                    if auth_service.refresh_user_permissions(force=True):
                        st.success("Permissões atualizadas!")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("Erro ao atualizar")

        with col2:
            if st.button(
                "❌ Limpar", use_container_width=True, help="Forçar expiração do cache"
            ):
                auth_service.invalidate_permissions_cache()
                st.info("Cache limpo!")
                st.rerun()

        # Botão especial para recarregar do backend
        if st.button(
            "🔧 Reload Backend",
            use_container_width=True,
            help="Recarregar dados completos do backend",
            type="secondary",
        ):
            with st.spinner("Recarregando do backend..."):
                try:
                    from front.services.api_client import api_client

                    user_data = api_client.get_current_user()

                    if user_data:
                        # Atualiza os dados do usuário na sessão
                        st.session_state["user"] = user_data

                        # Limpa cache e recarrega permissões
                        auth_service.invalidate_permissions_cache()
                        auth_service.refresh_user_permissions(force=True)

                        st.success("✅ Dados recarregados do backend!")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("❌ Erro ao recarregar dados do backend")
                except Exception as e:
                    st.error(f"❌ Erro: {str(e)}")

        # Logout button
        st.markdown("---")
        if st.button("🚪 Logout", use_container_width=True, type="secondary"):
            auth_service.logout()


def get_current_page():
    """Get current page from session state"""
    return st.session_state.get("page", "Dashboard")


def set_page(page_name: str):
    """Set current page in session state"""
    st.session_state.page = page_name
