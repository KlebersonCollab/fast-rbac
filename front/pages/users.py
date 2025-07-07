import streamlit as st
import pandas as pd
from front.services.auth_service import auth_service
from front.services.api_client import api_client, APIException
from front.utils.helpers import format_datetime, format_role_badge, confirm_action, create_data_table
from front.components.auth import check_permission_ui

def render_users_page():
    """Render users management page"""
    st.title("👥 Gerenciamento de Usuários")
    
    # Check permissions
    if not check_permission_ui("users:read"):
        return
    
    try:
        # Load data
        users_data = api_client.get_users()
        roles_data = api_client.get_roles() if auth_service.has_permission("roles:read") else []
        
        # Page tabs
        tab1, tab2, tab3 = st.tabs(["📋 Lista de Usuários", "➕ Novo Usuário", "📊 Estatísticas"])
        
        with tab1:
            render_users_list(users_data, roles_data)
        
        with tab2:
            if auth_service.has_permission("users:create"):
                render_create_user_form(roles_data)
            else:
                st.error("Você não tem permissão para criar usuários.")
        
        with tab3:
            render_users_statistics(users_data, roles_data)
            
    except APIException as e:
        st.error(f"Erro ao carregar dados: {e.message}")
    except Exception as e:
        st.error(f"Erro inesperado: {str(e)}")

def render_users_list(users_data, roles_data):
    """Render users list with search and filters"""
    st.markdown("### 📋 Lista de Usuários")
    
    if not users_data:
        st.info("Nenhum usuário encontrado.")
        return
    
    # Search and filters
    col1, col2, col3 = st.columns([3, 1, 1])
    
    with col1:
        search_term = st.text_input("🔍 Buscar usuários", placeholder="Digite o nome, email ou usuário...")
    
    with col2:
        # Provider filter
        providers = list(set([user.get('provider', 'basic') for user in users_data]))
        selected_provider = st.selectbox("Provedor", ["Todos"] + providers)
    
    with col3:
        # Status filter
        selected_status = st.selectbox("Status", ["Todos", "Ativo", "Inativo"])
    
    # Filter users
    filtered_users = users_data
    
    if search_term:
        filtered_users = [
            user for user in filtered_users
            if (search_term.lower() in user.get('username', '').lower() or
                search_term.lower() in user.get('email', '').lower() or
                search_term.lower() in user.get('full_name', '').lower())
        ]
    
    if selected_provider != "Todos":
        filtered_users = [
            user for user in filtered_users
            if user.get('provider', 'basic') == selected_provider
        ]
    
    if selected_status != "Todos":
        active_filter = selected_status == "Ativo"
        filtered_users = [
            user for user in filtered_users
            if user.get('is_active', False) == active_filter
        ]
    
    st.info(f"Encontrados {len(filtered_users)} usuário(s) de {len(users_data)} total.")
    
    # Users table
    if filtered_users:
        for i, user in enumerate(filtered_users):
            with st.container():
                render_user_card(user, roles_data, i)
                st.divider()

def render_user_card(user, roles_data, index):
    """Render individual user card"""
    col1, col2, col3, col4 = st.columns([2, 2, 2, 1])
    
    with col1:
        # User basic info
        st.markdown(f"**{user.get('username')}**")
        st.caption(f"📧 {user.get('email', 'N/A')}")
        if user.get('full_name'):
            st.caption(f"👤 {user.get('full_name')}")
        
        # Provider badge
        provider = user.get('provider', 'basic')
        if provider != 'basic':
            st.markdown(f"🌐 **{provider.title()}**")
    
    with col2:
        # Roles
        roles = user.get('roles', [])
        if roles:
            st.markdown("**Papéis:**")
            for role in roles:
                role_name = role.get('name', '')
                st.markdown(format_role_badge(role_name))
        else:
            st.markdown(":gray[Nenhum papel atribuído]")
    
    with col3:
        # Status and dates
        status = "🟢 Ativo" if user.get('is_active') else "🔴 Inativo"
        st.markdown(f"**Status:** {status}")
        
        if user.get('created_at'):
            st.caption(f"Criado: {format_datetime(user.get('created_at'))}")
        
        if user.get('last_login'):
            st.caption(f"Último login: {format_datetime(user.get('last_login'))}")
    
    with col4:
        # Actions
        if auth_service.has_permission("users:update"):
            if st.button("✏️ Editar", key=f"edit_user_{index}"):
                st.session_state[f'editing_user_{user.get("id")}'] = True
                st.rerun()
        
        if auth_service.has_permission("users:delete"):
            if user.get('username') != 'admin':  # Protect admin user
                if confirm_action("Deletar", f"delete_user_{index}"):
                    try:
                        # Note: Delete user endpoint not implemented in backend
                        st.warning("Funcionalidade de deletar usuário não implementada no backend.")
                    except APIException as e:
                        st.error(f"Erro ao deletar usuário: {e.message}")
    
    # Render edit form if editing
    if st.session_state.get(f'editing_user_{user.get("id")}', False):
        render_edit_user_form(user, roles_data)

def render_edit_user_form(user, roles_data):
    """Render edit user form"""
    st.markdown("### ✏️ Editar Usuário")
    
    with st.form(f"edit_user_form_{user.get('id')}"):
        # Basic info (read-only for some fields)
        st.text_input("Usuário", value=user.get('username', ''), disabled=True)
        st.text_input("Email", value=user.get('email', ''), disabled=True)
        
        # Editable fields
        new_full_name = st.text_input("Nome Completo", value=user.get('full_name', ''))
        new_is_active = st.checkbox("Usuário Ativo", value=user.get('is_active', False))
        
        # Role management
        st.markdown("**Gerenciar Papéis:**")
        
        current_role_ids = [role.get('id') for role in user.get('roles', [])]
        user_id = user.get('id')
        role_changes = []  # Track role changes
        
        if roles_data and auth_service.has_permission("users:update"):
            for role in roles_data:
                role_id = role.get('id')
                role_name = role.get('name', '')
                has_role = role_id in current_role_ids
                
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    st.markdown(f"🎭 **{role_name.title()}**")
                    st.caption(role.get('description', 'Sem descrição'))
                
                with col2:
                    new_has_role = st.checkbox("Atribuído", value=has_role, key=f"role_{role_id}_{user_id}")
                    
                    # Track role changes for processing when form is submitted
                    if new_has_role != has_role:
                        role_changes.append({
                            'role_id': role_id,
                            'role_name': role_name,
                            'action': 'assign' if new_has_role else 'remove'
                        })
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.form_submit_button("💾 Salvar Alterações", use_container_width=True):
                try:
                    # Process role changes
                    role_errors = []
                    role_successes = []
                    
                    for change in role_changes:
                        try:
                            if change['action'] == 'assign':
                                api_client.assign_role_to_user(user_id, change['role_id'])
                                role_successes.append(f"Papel {change['role_name']} atribuído!")
                            else:  # remove
                                api_client.remove_role_from_user(user_id, change['role_id'])
                                role_successes.append(f"Papel {change['role_name']} removido!")
                        except APIException as e:
                            role_errors.append(f"Erro ao {change['action'] == 'assign' and 'atribuir' or 'remover'} papel {change['role_name']}: {e.message}")
                    
                    # Show results
                    if role_successes:
                        for success in role_successes:
                            st.success(success)
                    
                    if role_errors:
                        for error in role_errors:
                            st.error(error)
                    
                    if role_changes and not role_errors:
                        st.session_state[f'editing_user_{user.get("id")}'] = False
                        st.rerun()
                    elif not role_changes:
                        # No role changes, just close edit mode
                        st.info("Nenhuma alteração detectada nos papéis.")
                        st.session_state[f'editing_user_{user.get("id")}'] = False
                        st.rerun()
                        
                except Exception as e:
                    st.error(f"Erro inesperado: {str(e)}")
        
        with col2:
            if st.form_submit_button("❌ Cancelar", use_container_width=True):
                st.session_state[f'editing_user_{user.get("id")}'] = False
                st.rerun()

def render_create_user_form(roles_data):
    """Render create user form"""
    st.markdown("### ➕ Criar Novo Usuário")
    
    with st.form("create_user_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            username = st.text_input("Usuário *", placeholder="Nome de usuário único")
            email = st.text_input("Email *", placeholder="email@exemplo.com")
            password = st.text_input("Senha *", type="password", placeholder="Senha segura")
        
        with col2:
            full_name = st.text_input("Nome Completo", placeholder="Nome completo do usuário")
            password_confirm = st.text_input("Confirmar Senha *", type="password", placeholder="Confirme a senha")
            is_active = st.checkbox("Usuário Ativo", value=True)
        
        # Role selection
        st.markdown("**Papéis (opcional):**")
        selected_roles = []
        
        if roles_data:
            for role in roles_data:
                if st.checkbox(f"🎭 {role.get('name', '').title()}", key=f"new_user_role_{role.get('id')}"):
                    selected_roles.append(role.get('id'))
        
        if st.form_submit_button("✅ Criar Usuário", use_container_width=True):
            # Validation
            if not all([username, email, password]):
                st.error("Por favor, preencha todos os campos obrigatórios.")
            elif password != password_confirm:
                st.error("As senhas não coincidem!")
            elif len(password) < 6:
                st.error("A senha deve ter pelo menos 6 caracteres.")
            else:
                try:
                    # Create user
                    response = api_client.register(username, email, password, full_name)
                    
                    if response:
                        st.success(f"Usuário {username} criado com sucesso!")
                        
                        # Assign roles if selected
                        if selected_roles:
                            user_id = response.get('id')
                            if user_id:
                                for role_id in selected_roles:
                                    try:
                                        api_client.assign_role_to_user(user_id, role_id)
                                    except APIException as e:
                                        st.warning(f"Erro ao atribuir papel: {e.message}")
                        
                        st.rerun()
                        
                except APIException as e:
                    st.error(f"Erro ao criar usuário: {e.message}")

def render_users_statistics(users_data, roles_data):
    """Render users statistics"""
    st.markdown("### 📊 Estatísticas de Usuários")
    
    if not users_data:
        st.info("Nenhum dado disponível para estatísticas.")
        return
    
    # Basic stats
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_users = len(users_data)
        st.metric("Total de Usuários", total_users)
    
    with col2:
        active_users = len([u for u in users_data if u.get('is_active', False)])
        st.metric("Usuários Ativos", active_users)
    
    with col3:
        oauth_users = len([u for u in users_data if u.get('provider', 'basic') != 'basic'])
        st.metric("Usuários OAuth", oauth_users)
    
    with col4:
        users_with_roles = len([u for u in users_data if u.get('roles')])
        st.metric("Com Papéis", users_with_roles)
    
    # Detailed analysis
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Users by provider
        provider_counts = {}
        for user in users_data:
            provider = user.get('provider', 'basic')
            provider_counts[provider] = provider_counts.get(provider, 0) + 1
        
        if provider_counts:
            st.markdown("**Usuários por Provedor:**")
            df_providers = pd.DataFrame([
                {"Provedor": provider.title(), "Quantidade": count}
                for provider, count in provider_counts.items()
            ])
            st.dataframe(df_providers, use_container_width=True)
    
    with col2:
        # Users by role
        role_counts = {}
        for user in users_data:
            user_roles = user.get('roles', [])
            if not user_roles:
                role_counts['Sem papel'] = role_counts.get('Sem papel', 0) + 1
            else:
                for role in user_roles:
                    role_name = role.get('name', 'Desconhecido')
                    role_counts[role_name] = role_counts.get(role_name, 0) + 1
        
        if role_counts:
            st.markdown("**Usuários por Papel:**")
            df_roles = pd.DataFrame([
                {"Papel": role, "Quantidade": count}
                for role, count in role_counts.items()
            ])
            st.dataframe(df_roles, use_container_width=True)
    
    # Recent registrations
    st.markdown("---")
    st.markdown("**Registros Recentes:**")
    
    # Sort by creation date
    sorted_users = sorted(
        users_data,
        key=lambda x: x.get('created_at', ''),
        reverse=True
    )[:10]
    
    for user in sorted_users:
        col1, col2, col3 = st.columns([2, 2, 1])
        
        with col1:
            st.write(f"**{user.get('username')}**")
        
        with col2:
            st.write(user.get('email', 'N/A'))
        
        with col3:
            st.write(format_datetime(user.get('created_at', '')))
    
    # Export functionality
    st.markdown("---")
    if st.button("📥 Exportar Lista de Usuários (CSV)"):
        try:
            # Prepare data for export
            export_data = []
            for user in users_data:
                roles_str = ", ".join([role.get('name', '') for role in user.get('roles', [])])
                export_data.append({
                    'Usuário': user.get('username', ''),
                    'Email': user.get('email', ''),
                    'Nome Completo': user.get('full_name', ''),
                    'Provedor': user.get('provider', 'basic'),
                    'Ativo': 'Sim' if user.get('is_active') else 'Não',
                    'Papéis': roles_str or 'Nenhum',
                    'Criado em': format_datetime(user.get('created_at', ''))
                })
            
            df_export = pd.DataFrame(export_data)
            csv = df_export.to_csv(index=False)
            
            st.download_button(
                label="📥 Baixar CSV",
                data=csv,
                file_name=f"usuarios_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )
            
        except Exception as e:
            st.error(f"Erro ao exportar dados: {str(e)}") 