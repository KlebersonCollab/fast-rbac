import streamlit as st
from front.services.auth_service import auth_service

def login_form():
    """Display login form"""
    st.markdown("### 🔐 Login")
    
    with st.form("login_form"):
        username = st.text_input("Usuário", placeholder="Digite seu usuário")
        password = st.text_input("Senha", type="password", placeholder="Digite sua senha")
        
        col1, col2 = st.columns(2)
        
        with col1:
            login_submitted = st.form_submit_button("🚀 Entrar", use_container_width=True)
        
        with col2:
            show_register = st.form_submit_button("📝 Cadastrar", use_container_width=True)
    
    if login_submitted:
        if username and password:
            if auth_service.login(username, password):
                st.success("Login realizado com sucesso!")
                st.rerun()
            else:
                st.error("Credenciais inválidas!")
        else:
            st.warning("Por favor, preencha todos os campos.")
    
    if show_register:
        st.session_state.show_register = True
        st.rerun()

def register_form():
    """Display registration form"""
    st.markdown("### 📝 Cadastro de Usuário")
    
    with st.form("register_form"):
        username = st.text_input("Usuário", placeholder="Escolha um nome de usuário")
        email = st.text_input("Email", placeholder="seu@email.com")
        full_name = st.text_input("Nome Completo", placeholder="Seu nome completo")
        password = st.text_input("Senha", type="password", placeholder="Escolha uma senha")
        password_confirm = st.text_input("Confirmar Senha", type="password", 
                                       placeholder="Confirme sua senha")
        
        col1, col2 = st.columns(2)
        
        with col1:
            register_submitted = st.form_submit_button("✅ Cadastrar", use_container_width=True)
        
        with col2:
            back_to_login = st.form_submit_button("⬅️ Voltar", use_container_width=True)
    
    if register_submitted:
        if not all([username, email, password]):
            st.warning("Por favor, preencha todos os campos obrigatórios.")
        elif password != password_confirm:
            st.error("As senhas não coincidem!")
        elif len(password) < 6:
            st.warning("A senha deve ter pelo menos 6 caracteres.")
        else:
            if auth_service.register(username, email, password, full_name):
                st.session_state.show_register = False
                st.rerun()
    
    if back_to_login:
        st.session_state.show_register = False
        st.rerun()

def auth_info():
    """Display current user authentication info"""
    user = auth_service.get_current_user()
    
    if user:
        with st.sidebar:
            st.markdown("---")
            st.markdown("### 👤 Usuário Logado")
            
            # User info
            st.markdown(f"**Nome:** {user.get('full_name', 'N/A')}")
            st.markdown(f"**Usuário:** {user.get('username')}")
            st.markdown(f"**Email:** {user.get('email')}")
            
            # Roles
            roles = auth_service.get_user_roles()
            if roles:
                st.markdown("**Papéis:**")
                for role in roles:
                    if role == "admin":
                        st.markdown(f"- :red[{role}]")
                    elif role == "manager":
                        st.markdown(f"- :orange[{role}]")
                    elif role == "editor":
                        st.markdown(f"- :blue[{role}]")
                    else:
                        st.markdown(f"- :gray[{role}]")
            
            # Logout button
            st.markdown("---")
            if st.button("🚪 Logout", use_container_width=True):
                auth_service.logout()

def require_auth():
    """Decorator component to require authentication"""
    if not auth_service.is_authenticated():
        st.error("Você precisa estar logado para acessar esta página.")
        return False
    return True

def check_permission_ui(permission: str, show_error: bool = True) -> bool:
    """Check permission and optionally show UI error"""
    if not auth_service.has_permission(permission):
        if show_error:
            st.error(f"Você não tem permissão para: {permission}")
        return False
    return True

def permission_guard(permission: str):
    """Permission guard component"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            if check_permission_ui(permission):
                return func(*args, **kwargs)
            else:
                st.stop()
        return wrapper
    return decorator 