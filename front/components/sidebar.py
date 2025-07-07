import streamlit as st
import time
from front.services.auth_service import auth_service

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
        
        # Navigation menu
        st.markdown("### 📋 Navegação")
        
        # Dashboard (available to all authenticated users)
        if st.button("📊 Dashboard", use_container_width=True):
            st.session_state.page = "Dashboard"
            st.rerun()
        
        # Users management (requires users:read permission)
        if auth_service.has_permission("users:read"):
            if st.button("👥 Usuários", use_container_width=True):
                st.session_state.page = "Users"
                st.rerun()
        
        # Roles management (requires roles:read permission)
        if auth_service.has_permission("roles:read"):
            if st.button("🎭 Papéis", use_container_width=True):
                st.session_state.page = "Roles"
                st.rerun()
        
        # Permissions management (requires permissions:read permission)
        if auth_service.has_permission("permissions:read"):
            if st.button("🔐 Permissões", use_container_width=True):
                st.session_state.page = "Permissions"
                st.rerun()
        
        # Logs dashboard (requires logs:view permission)
        if auth_service.has_permission("logs:view"):
            if st.button("📊 Logs Monitor", use_container_width=True):
                st.session_state.page = "Logs"
                st.rerun()
        
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
                "viewer": "⚪"
            }
            
            for role in roles:
                color = role_colors.get(role, "⚫")
                st.markdown(f"{color} {role}")
        
        # OAuth provider info
        provider = user.get('provider', 'basic')
        if provider != 'basic':
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
            if st.button("🔄 Atualizar", use_container_width=True, help="Atualizar permissões manualmente"):
                with st.spinner("Atualizando..."):
                    if auth_service.refresh_user_permissions(force=True):
                        st.success("Permissões atualizadas!")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("Erro ao atualizar")
        
        with col2:
            if st.button("❌ Limpar", use_container_width=True, help="Forçar expiração do cache"):
                auth_service.invalidate_permissions_cache()
                st.info("Cache limpo!")
                st.rerun()
        
        # Botão especial para recarregar do backend
        if st.button("🔧 Reload Backend", use_container_width=True, help="Recarregar dados completos do backend", type="secondary"):
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