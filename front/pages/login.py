import streamlit as st
from front.components.auth import login_form, register_form
from front.services.auth_service import auth_service
from front.services.api_client import api_client, APIException

def show_login_page():
    """Display login page"""
    
    # Center the login form
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        # App header
        st.markdown("""
        <div style="text-align: center; padding: 2rem 0;">
            <h1>🛡️ FastAPI RBAC</h1>
            <h3>Painel Administrativo</h3>
            <p>Sistema de controle de acesso baseado em papéis</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Check if we should show register form
        show_register = st.session_state.get("show_register", False)
        
        if show_register:
            register_form()
        else:
            login_form()
        
        # OAuth providers section
        st.markdown("---")
        show_oauth_providers()
        
        # API status
        st.markdown("---")
        show_api_status()

def show_oauth_providers():
    """Display OAuth login options"""
    st.markdown("### 🌐 Login Social")
    
    try:
        providers_data = api_client.get_oauth_providers()
        providers = providers_data.get("providers", [])
        
        if providers:
            st.info("Os provedores OAuth estão configurados, mas o login social requer configuração adicional no navegador.")
            
            for provider in providers:
                name = provider.get("name", "")
                display_name = provider.get("display_name", name)
                
                # Provider icons
                icon_map = {
                    "google": "🟡",
                    "microsoft": "🔵", 
                    "github": "⚫"
                }
                icon = icon_map.get(name, "🔗")
                
                if st.button(f"{icon} Entrar com {display_name}", 
                           use_container_width=True, 
                           disabled=True):  # Disabled for demo
                    st.info(f"Redirecionamento para {display_name} seria feito aqui.")
        else:
            st.info("Nenhum provedor OAuth configurado.")
            
    except APIException as e:
        st.warning(f"Erro ao carregar provedores OAuth: {e.message}")
    except Exception:
        st.warning("Erro ao conectar com a API.")

def show_api_status():
    """Display API connection status"""
    st.markdown("### 🔧 Status da API")
    
    try:
        health_data = api_client.health_check()
        status = health_data.get("status", "unknown")
        service = health_data.get("service", "unknown")
        
        if status == "healthy":
            st.success(f"✅ {service} - Conectado")
        else:
            st.warning(f"⚠️ {service} - Status: {status}")
            
    except APIException as e:
        st.error(f"❌ API desconectada: {e.message}")
    except Exception:
        st.error("❌ Erro de conexão com a API")

def demo_credentials():
    """Show demo credentials info"""
    with st.expander("🔑 Credenciais de Demonstração"):
        st.markdown("""
        **Usuário Administrador:**
        - **Usuário:** `admin`
        - **Senha:** `admin123`
        - **Permissões:** Acesso completo ao sistema
        
        **Funcionalidades disponíveis:**
        - ✅ Gerenciamento de usuários
        - ✅ Gerenciamento de papéis e permissões
        - ✅ Dashboard com métricas
        - ✅ Exemplos de funcionalidades protegidas
        
        **Como testar:**
        1. Faça login com as credenciais acima
        2. Explore o menu lateral para acessar diferentes funcionalidades
        3. Crie novos usuários e atribua diferentes papéis
        4. Teste as permissões com diferentes usuários
        """)

def render_login():
    """Main login page render function"""
    # Check if already authenticated
    if auth_service.is_authenticated():
        st.rerun()
    
    # Show login page
    show_login_page()
    
    # Show demo credentials
    demo_credentials() 