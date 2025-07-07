import streamlit as st
from front.services.auth_service import auth_service
from front.services.api_client import api_client, APIException
from front.components.auth import check_permission_ui

def render_posts_page():
    """Render posts example page"""
    st.title("📝 Gerenciamento de Posts")
    st.markdown("Esta é uma página de exemplo para demonstrar o controle de acesso baseado em permissões.")
    
    # Check different permission levels
    can_read = auth_service.has_permission("posts:read")
    can_create = auth_service.has_permission("posts:create")
    can_update = auth_service.has_permission("posts:update")
    can_delete = auth_service.has_permission("posts:delete")
    
    # Show user permissions
    with st.expander("🔍 Suas Permissões para Posts"):
        st.write(f"📖 Ler posts: {'✅' if can_read else '❌'}")
        st.write(f"✏️ Criar posts: {'✅' if can_create else '❌'}")
        st.write(f"📝 Editar posts: {'✅' if can_update else '❌'}")
        st.write(f"🗑️ Deletar posts: {'✅' if can_delete else '❌'}")
    
    # Test API endpoints
    tab1, tab2, tab3 = st.tabs(["📖 Ler Posts", "✏️ Criar Post", "🧪 Testar API"])
    
    with tab1:
        if can_read:
            render_read_posts()
        else:
            st.error("❌ Você não tem permissão para ler posts.")
    
    with tab2:
        if can_create:
            render_create_post()
        else:
            st.error("❌ Você não tem permissão para criar posts.")
    
    with tab3:
        render_api_tests()

def render_read_posts():
    """Render read posts functionality"""
    st.markdown("### 📖 Lista de Posts")
    
    if st.button("🔄 Carregar Posts"):
        try:
            response = api_client.read_posts()
            st.success("✅ Posts carregados com sucesso!")
            st.json(response)
        except APIException as e:
            st.error(f"❌ Erro ao carregar posts: {e.message}")
    
    # Mock posts data for demonstration
    mock_posts = [
        {
            "id": 1,
            "title": "Bem-vindos ao Sistema RBAC",
            "content": "Este é o primeiro post do nosso sistema...",
            "author": "admin",
            "created_at": "2024-01-15T10:00:00Z",
            "status": "published"
        },
        {
            "id": 2,
            "title": "Como Gerenciar Permissões",
            "content": "Neste post vamos explicar como funciona...",
            "author": "editor01",
            "created_at": "2024-01-14T15:30:00Z",
            "status": "draft"
        },
        {
            "id": 3,
            "title": "Configurando OAuth",
            "content": "Passo a passo para configurar autenticação OAuth...",
            "author": "manager01",
            "created_at": "2024-01-13T09:15:00Z",
            "status": "published"
        }
    ]
    
    st.markdown("**Posts de Exemplo:**")
    for post in mock_posts:
        with st.container():
            col1, col2 = st.columns([3, 1])
            
            with col1:
                status_color = "🟢" if post["status"] == "published" else "🟡"
                st.markdown(f"**{post['title']}** {status_color}")
                st.caption(f"Por {post['author']} em {post['created_at'][:10]}")
                st.write(post["content"][:100] + "...")
            
            with col2:
                if auth_service.has_permission("posts:update"):
                    if st.button("✏️ Editar", key=f"edit_post_{post['id']}"):
                        st.info(f"Editando post: {post['title']}")
                
                if auth_service.has_permission("posts:delete"):
                    if st.button("🗑️ Deletar", key=f"delete_post_{post['id']}"):
                        st.warning(f"Post {post['title']} seria deletado.")
            
            st.divider()

def render_create_post():
    """Render create post functionality"""
    st.markdown("### ✏️ Criar Novo Post")
    
    with st.form("create_post_form"):
        title = st.text_input("Título do Post", placeholder="Digite o título...")
        content = st.text_area("Conteúdo", placeholder="Escreva o conteúdo do post...", height=200)
        
        col1, col2 = st.columns(2)
        with col1:
            status = st.selectbox("Status", ["draft", "published"])
        with col2:
            tags = st.text_input("Tags", placeholder="tag1, tag2, tag3")
        
        if st.form_submit_button("📝 Criar Post", use_container_width=True):
            if title and content:
                try:
                    response = api_client.create_post()
                    st.success(f"✅ Post '{title}' criado com sucesso!")
                    st.json(response)
                except APIException as e:
                    st.error(f"❌ Erro ao criar post: {e.message}")
            else:
                st.warning("⚠️ Por favor, preencha todos os campos obrigatórios.")

def render_settings_page():
    """Render settings example page"""
    st.title("⚙️ Configurações do Sistema")
    st.markdown("Esta página demonstra controle de acesso a configurações sensíveis.")
    
    # Check settings permission
    if not auth_service.has_permission("settings:read"):
        st.error("❌ Você não tem permissão para acessar as configurações.")
        return
    
    # Test settings API
    if st.button("🔄 Carregar Configurações"):
        try:
            response = api_client.access_settings()
            st.success("✅ Configurações carregadas com sucesso!")
            st.json(response)
        except APIException as e:
            st.error(f"❌ Erro ao carregar configurações: {e.message}")
    
    # Mock settings interface
    st.markdown("---")
    st.markdown("### 🛠️ Configurações Disponíveis")
    
    with st.expander("🔐 Configurações de Segurança"):
        if auth_service.has_permission("settings:update"):
            st.checkbox("Forçar autenticação 2FA", value=False, disabled=True)
            st.slider("Tempo de sessão (minutos)", 15, 240, 30, disabled=True)
            st.checkbox("Log de auditoria detalhado", value=True, disabled=True)
            st.info("💡 Configurações desabilitadas para demonstração")
        else:
            st.error("❌ Você não tem permissão para alterar configurações de segurança.")
    
    with st.expander("🎨 Configurações de Interface"):
        st.selectbox("Tema padrão", ["Claro", "Escuro", "Automático"], disabled=True)
        st.selectbox("Idioma", ["Português", "English", "Español"], disabled=True)
        st.info("💡 Configurações de interface disponíveis para todos os usuários")
    
    with st.expander("📧 Configurações de Email"):
        if auth_service.has_permission("settings:update"):
            st.text_input("Servidor SMTP", placeholder="smtp.exemplo.com", disabled=True)
            st.number_input("Porta", value=587, disabled=True)
            st.checkbox("Usar SSL", value=True, disabled=True)
            st.info("💡 Configurações desabilitadas para demonstração")
        else:
            st.error("❌ Você não tem permissão para alterar configurações de email.")

def render_api_tests():
    """Render API testing interface"""
    st.markdown("### 🧪 Teste de Endpoints da API")
    st.markdown("Use esta seção para testar diferentes endpoints e suas permissões.")
    
    # User info test
    st.markdown("**📊 Informações do Usuário:**")
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("👤 Meu Perfil"):
            try:
                response = api_client.get_profile()
                st.success("✅ Perfil carregado!")
                st.json(response)
            except APIException as e:
                st.error(f"❌ Erro: {e.message}")
    
    with col2:
        if st.button("🧪 Testar Token"):
            try:
                response = api_client.test_token()
                st.success("✅ Token válido!")
                st.json(response)
            except APIException as e:
                st.error(f"❌ Token inválido: {e.message}")
    
    # Protected endpoints test
    st.markdown("---")
    st.markdown("**🔒 Endpoints Protegidos:**")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("📝 Testar Posts"):
            try:
                response = api_client.read_posts()
                st.success("✅ Acesso liberado!")
                st.json(response)
            except APIException as e:
                st.error(f"❌ Acesso negado: {e.message}")
    
    with col2:
        if st.button("⚙️ Testar Configurações"):
            try:
                response = api_client.access_settings()
                st.success("✅ Acesso liberado!")
                st.json(response)
            except APIException as e:
                st.error(f"❌ Acesso negado: {e.message}")
    
    with col3:
        if st.button("✏️ Testar Criação"):
            try:
                response = api_client.create_post()
                st.success("✅ Criação permitida!")
                st.json(response)
            except APIException as e:
                st.error(f"❌ Criação negada: {e.message}")
    
    # Permission matrix
    st.markdown("---")
    st.markdown("**🔍 Matriz de Permissões:**")
    
    permissions_to_test = [
        "users:read", "users:create", "users:update", "users:delete",
        "roles:read", "roles:create", "roles:update", "roles:delete",
        "permissions:read", "permissions:create", "permissions:update", "permissions:delete",
        "posts:read", "posts:create", "posts:update", "posts:delete",
        "settings:read", "settings:update"
    ]
    
    # Create permission matrix table
    import pandas as pd
    
    matrix_data = []
    for perm in permissions_to_test:
        has_perm = auth_service.has_permission(perm)
        matrix_data.append({
            "Permissão": perm,
            "Status": "✅ Permitido" if has_perm else "❌ Negado",
            "Recurso": perm.split(":")[0],
            "Ação": perm.split(":")[1] if ":" in perm else "N/A"
        })
    
    df_matrix = pd.DataFrame(matrix_data)
    st.dataframe(df_matrix, use_container_width=True)
    
    # Current user summary
    st.markdown("---")
    st.markdown("**👤 Resumo do Usuário Atual:**")
    
    user = auth_service.get_current_user()
    if user:
        col1, col2 = st.columns(2)
        
        with col1:
            st.json({
                "username": user.get("username"),
                "email": user.get("email"),
                "full_name": user.get("full_name"),
                "provider": user.get("provider", "basic"),
                "is_active": user.get("is_active", False)
            })
        
        with col2:
            roles = user.get("roles", [])
            if roles:
                st.markdown("**Papéis:**")
                for role in roles:
                    st.write(f"🎭 {role.get('name', '')}")
                
                st.markdown("**Total de Permissões:**")
                all_permissions = []
                for role in roles:
                    for perm in role.get("permissions", []):
                        if perm.get("name") not in all_permissions:
                            all_permissions.append(perm.get("name"))
                
                st.metric("Permissões Ativas", len(all_permissions))
            else:
                st.info("Nenhum papel atribuído") 