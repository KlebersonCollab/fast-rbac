import streamlit as st
from front.config.settings import settings
from front.utils.helpers import init_session_state, check_session_timeout
from front.services.auth_service import auth_service
from front.components.sidebar import render_sidebar, get_current_page
from front.pages.login import render_login
from front.pages.dashboard import render_dashboard
from front.pages.users import render_users_page
from front.pages.roles import render_roles_page
from front.pages.permissions import render_permissions_page
from front.pages.examples import render_posts_page, render_settings_page

def configure_page():
    """Configure Streamlit page"""
    st.set_page_config(
        page_title=settings.PAGE_TITLE,
        page_icon=settings.PAGE_ICON,
        layout=settings.LAYOUT,
        initial_sidebar_state=settings.INITIAL_SIDEBAR_STATE
    )
    
    # Custom CSS
    st.markdown("""
    <style>
        .main .block-container {
            padding-top: 1rem;
            padding-bottom: 1rem;
        }
        
        .stMetric {
            background-color: #f0f2f6;
            border: 1px solid #e1e5e9;
            padding: 1rem;
            border-radius: 0.5rem;
            box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1);
        }
        
        .success-message {
            background-color: #d4edda;
            border: 1px solid #c3e6cb;
            color: #155724;
            padding: 0.75rem 1.25rem;
            margin-bottom: 1rem;
            border-radius: 0.25rem;
        }
        
        .error-message {
            background-color: #f8d7da;
            border: 1px solid #f5c6cb;
            color: #721c24;
            padding: 0.75rem 1.25rem;
            margin-bottom: 1rem;
            border-radius: 0.25rem;
        }
        
        .info-message {
            background-color: #d1ecf1;
            border: 1px solid #bee5eb;
            color: #0c5460;
            padding: 0.75rem 1.25rem;
            margin-bottom: 1rem;
            border-radius: 0.25rem;
        }
        
        .sidebar .sidebar-content {
            background-color: #f8f9fa;
        }
        
        .stButton > button {
            width: 100%;
        }
        
        .role-badge-admin {
            background-color: #dc3545;
            color: white;
            padding: 0.25rem 0.5rem;
            border-radius: 0.25rem;
            font-size: 0.75rem;
            font-weight: bold;
        }
        
        .role-badge-manager {
            background-color: #fd7e14;
            color: white;
            padding: 0.25rem 0.5rem;
            border-radius: 0.25rem;
            font-size: 0.75rem;
            font-weight: bold;
        }
        
        .role-badge-editor {
            background-color: #007bff;
            color: white;
            padding: 0.25rem 0.5rem;
            border-radius: 0.25rem;
            font-size: 0.75rem;
            font-weight: bold;
        }
        
        .role-badge-viewer {
            background-color: #6c757d;
            color: white;
            padding: 0.25rem 0.5rem;
            border-radius: 0.25rem;
            font-size: 0.75rem;
            font-weight: bold;
        }
    </style>
    """, unsafe_allow_html=True)

def handle_authentication():
    """Handle user authentication flow"""
    # Initialize session state
    init_session_state()
    
    # Check session timeout
    if auth_service.is_authenticated() and check_session_timeout():
        st.warning("Sua sessão expirou. Faça login novamente.")
        auth_service.logout()
        return False
    
    # Check if user is authenticated
    if not auth_service.is_authenticated():
        render_login()
        return False
    
    return True

def render_main_app():
    """Render main application"""
    # Render sidebar
    render_sidebar()
    
    # Get current page
    current_page = get_current_page()
    
    # Route to appropriate page
    if current_page == "Dashboard":
        render_dashboard()
    elif current_page == "Users":
        render_users_page()
    elif current_page == "Roles":
        render_roles_page()
    elif current_page == "Permissions":
        render_permissions_page()
    elif current_page == "Posts":
        render_posts_page()
    elif current_page == "Settings":
        render_settings_page()
    else:
        # Default to dashboard
        render_dashboard()

def show_footer():
    """Show application footer"""
    st.markdown("---")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("**FastAPI RBAC v1.0.0**")
        st.caption("Sistema de controle de acesso")
    
    with col2:
        st.markdown("**Tecnologias:**")
        st.caption("FastAPI • Streamlit • SQLAlchemy • JWT")
    
    with col3:
        st.markdown("**Status:**")
        try:
            from front.services.api_client import api_client
            health = api_client.health_check()
            if health.get("status") == "healthy":
                st.caption("🟢 Backend Online")
            else:
                st.caption("🟡 Backend Instável")
        except:
            st.caption("🔴 Backend Offline")

def main():
    """Main application function"""
    # Configure page
    configure_page()
    
    # Show app header
    if not st.session_state.get("authenticated", False):
        # Only show header on login page
        pass
    else:
        # Show compact header for authenticated users
        with st.container():
            col1, col2, col3 = st.columns([2, 1, 1])
            
            with col1:
                st.markdown(f"# {settings.APP_ICON} {settings.APP_TITLE}")
            
            with col2:
                # Quick stats for authenticated users
                if auth_service.is_authenticated():
                    user = auth_service.get_current_user()
                    if user:
                        st.metric("Papéis", len(user.get("roles", [])))
            
            with col3:
                # Quick actions
                if auth_service.is_authenticated():
                    permissions_count = len(auth_service.get_user_permissions())
                    st.metric("Permissões", permissions_count)
    
    # Handle authentication and main app
    try:
        if handle_authentication():
            render_main_app()
            show_footer()
    except Exception as e:
        st.error(f"Erro na aplicação: {str(e)}")
        
        if settings.DEBUG:
            st.exception(e)
        
        if st.button("🔄 Recarregar Aplicação"):
            st.rerun()

if __name__ == "__main__":
    main() 