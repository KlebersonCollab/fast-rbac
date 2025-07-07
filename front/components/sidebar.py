import streamlit as st
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