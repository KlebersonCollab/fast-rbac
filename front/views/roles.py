import streamlit as st
import pandas as pd
from datetime import datetime
from front.services.auth_service import auth_service
from front.services.api_client import api_client, APIException
from front.utils.helpers import format_datetime, format_permission_badge, confirm_action
from front.components.auth import check_permission_ui

def render_roles_page():
    """Render roles management page"""
    st.title("🎭 Gerenciamento de Papéis")
    
    # Check permissions
    if not check_permission_ui("roles:read"):
        return
    
    try:
        # Load data
        roles_data = api_client.get_roles()
        permissions_data = api_client.get_permissions() if auth_service.has_permission("permissions:read") else []
        
        # Page tabs
        tab1, tab2, tab3 = st.tabs(["📋 Lista de Papéis", "➕ Novo Papel", "📊 Estatísticas"])
        
        with tab1:
            render_roles_list(roles_data, permissions_data)
        
        with tab2:
            if auth_service.has_permission("roles:create"):
                render_create_role_form(permissions_data)
            else:
                st.error("Você não tem permissão para criar papéis.")
        
        with tab3:
            render_roles_statistics(roles_data, permissions_data)
            
    except APIException as e:
        st.error(f"Erro ao carregar dados: {e.message}")
    except Exception as e:
        st.error(f"Erro inesperado: {str(e)}")

def render_roles_list(roles_data, permissions_data):
    """Render roles list"""
    st.markdown("### 📋 Lista de Papéis")
    
    if not roles_data:
        st.info("Nenhum papel encontrado.")
        return
    
    # Search filter
    search_term = st.text_input("🔍 Buscar papéis", placeholder="Digite o nome ou descrição...")
    
    # Filter roles
    filtered_roles = roles_data
    if search_term:
        filtered_roles = [
            role for role in filtered_roles
            if (search_term.lower() in role.get('name', '').lower() or
                search_term.lower() in role.get('description', '').lower())
        ]
    
    st.info(f"Encontrados {len(filtered_roles)} papel(éis) de {len(roles_data)} total.")
    
    # Roles table
    if filtered_roles:
        for i, role in enumerate(filtered_roles):
            with st.container():
                render_role_card(role, permissions_data, i)
                st.divider()

def render_role_card(role, permissions_data, index):
    """Render individual role card"""
    col1, col2, col3, col4 = st.columns([2, 3, 2, 1])
    
    with col1:
        # Role basic info
        role_name = role.get('name', '')
        st.markdown(f"**🎭 {role_name.title()}**")
        
        description = role.get('description', 'Sem descrição')
        st.caption(description)
        
        # Status
        status = "🟢 Ativo" if role.get('is_active') else "🔴 Inativo"
        st.markdown(f"**Status:** {status}")
    
    with col2:
        # Permissions
        permissions = role.get('permissions', [])
        if permissions:
            st.markdown(f"**Permissões ({len(permissions)}):**")
            
            # Show first few permissions
            for perm in permissions[:3]:
                perm_name = perm.get('name', '')
                st.markdown(f"• {format_permission_badge(perm_name)}")
            
            if len(permissions) > 3:
                remaining = len(permissions) - 3
                st.caption(f"... e mais {remaining} permissão(ões)")
        else:
            st.markdown(":gray[Nenhuma permissão atribuída]")
    
    with col3:
        # Dates and stats
        if role.get('created_at'):
            st.caption(f"Criado: {format_datetime(role.get('created_at'))}")
        
        # Mock user count (would be calculated from actual user data)
        mock_user_counts = {'admin': 2, 'manager': 5, 'editor': 12, 'viewer': 25}
        user_count = mock_user_counts.get(role_name, 8)
        st.caption(f"👥 {user_count} usuário(s)")
    
    with col4:
        # Actions
        if auth_service.has_permission("roles:update"):
            if st.button("✏️ Editar", key=f"edit_role_{index}"):
                st.session_state[f'editing_role_{role.get("id")}'] = True
                st.rerun()
        
        if auth_service.has_permission("roles:delete"):
            # Protect system roles
            if role_name not in ['admin', 'manager', 'editor', 'viewer']:
                if confirm_action("Deletar", f"delete_role_{index}"):
                    try:
                        api_client.delete_role(role.get('id'))
                        st.success(f"Papel {role_name} deletado com sucesso!")
                        st.rerun()
                    except APIException as e:
                        st.error(f"Erro ao deletar papel: {e.message}")
            else:
                st.caption("🔒 Papel protegido")
    
    # Render edit form if editing
    if st.session_state.get(f'editing_role_{role.get("id")}', False):
        render_edit_role_form(role, permissions_data)

def render_edit_role_form(role, permissions_data):
    """Render edit role form"""
    st.markdown("### ✏️ Editar Papel")
    
    with st.form(f"edit_role_form_{role.get('id')}"):
        col1, col2 = st.columns(2)
        
        with col1:
            new_name = st.text_input("Nome do Papel", value=role.get('name', ''))
            new_is_active = st.checkbox("Papel Ativo", value=role.get('is_active', False))
        
        with col2:
            new_description = st.text_area("Descrição", value=role.get('description', ''))
        
        # Permission management
        st.markdown("**Gerenciar Permissões:**")
        
        current_permission_ids = [perm.get('id') for perm in role.get('permissions', [])]
        role_id = role.get('id')
        
        if permissions_data and auth_service.has_permission("roles:update"):
            # Group permissions by resource
            permissions_by_resource = {}
            for perm in permissions_data:
                resource = perm.get('resource', 'other')
                if resource not in permissions_by_resource:
                    permissions_by_resource[resource] = []
                permissions_by_resource[resource].append(perm)
            
            for resource, perms in permissions_by_resource.items():
                with st.expander(f"📁 {resource.title()}"):
                    for perm in perms:
                        perm_id = perm.get('id')
                        perm_name = perm.get('name', '')
                        has_permission = perm_id in current_permission_ids
                        
                        col1, col2 = st.columns([3, 1])
                        
                        with col1:
                            st.markdown(f"**{perm_name}**")
                            st.caption(perm.get('description', 'Sem descrição'))
                        
                        with col2:
                            new_has_permission = st.checkbox(
                                "Atribuída", 
                                value=has_permission, 
                                key=f"perm_{perm_id}_{role_id}"
                            )
                            
                            # Handle permission assignment changes
                            if new_has_permission != has_permission:
                                if new_has_permission and not has_permission:
                                    # Assign permission
                                    try:
                                        api_client.assign_permission_to_role(role_id, perm_id)
                                        st.success(f"Permissão {perm_name} atribuída!")
                                        st.rerun()
                                    except APIException as e:
                                        st.error(f"Erro ao atribuir permissão: {e.message}")
                                elif has_permission and not new_has_permission:
                                    # Remove permission
                                    try:
                                        api_client.remove_permission_from_role(role_id, perm_id)
                                        st.success(f"Permissão {perm_name} removida!")
                                        st.rerun()
                                    except APIException as e:
                                        st.error(f"Erro ao remover permissão: {e.message}")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.form_submit_button("💾 Salvar Alterações", use_container_width=True):
                try:
                    api_client.update_role(
                        role_id, 
                        name=new_name, 
                        description=new_description, 
                        is_active=new_is_active
                    )
                    st.success("Papel atualizado com sucesso!")
                    st.session_state[f'editing_role_{role.get("id")}'] = False
                    st.rerun()
                except APIException as e:
                    st.error(f"Erro ao atualizar papel: {e.message}")
        
        with col2:
            if st.form_submit_button("❌ Cancelar", use_container_width=True):
                st.session_state[f'editing_role_{role.get("id")}'] = False
                st.rerun()

def render_create_role_form(permissions_data):
    """Render create role form"""
    st.markdown("### ➕ Criar Novo Papel")
    
    with st.form("create_role_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            name = st.text_input("Nome do Papel *", placeholder="Nome único do papel")
            is_active = st.checkbox("Papel Ativo", value=True)
        
        with col2:
            description = st.text_area("Descrição", placeholder="Descrição do papel e suas responsabilidades")
        
        # Permission selection
        st.markdown("**Permissões (opcional):**")
        selected_permissions = []
        
        if permissions_data:
            # Group permissions by resource
            permissions_by_resource = {}
            for perm in permissions_data:
                resource = perm.get('resource', 'other')
                if resource not in permissions_by_resource:
                    permissions_by_resource[resource] = []
                permissions_by_resource[resource].append(perm)
            
            for resource, perms in permissions_by_resource.items():
                with st.expander(f"📁 {resource.title()}"):
                    for perm in perms:
                        if st.checkbox(
                            f"**{perm.get('name', '')}**", 
                            key=f"new_role_perm_{perm.get('id')}"
                        ):
                            selected_permissions.append(perm.get('id'))
                        st.caption(perm.get('description', 'Sem descrição'))
        
        if st.form_submit_button("✅ Criar Papel", use_container_width=True):
            # Validation
            if not name:
                st.error("Por favor, preencha o nome do papel.")
            else:
                try:
                    # Create role
                    response = api_client.create_role(name, description, is_active)
                    
                    if response:
                        st.success(f"Papel {name} criado com sucesso!")
                        
                        # Assign permissions if selected
                        if selected_permissions:
                            role_id = response.get('id')
                            if role_id:
                                for perm_id in selected_permissions:
                                    try:
                                        api_client.assign_permission_to_role(role_id, perm_id)
                                    except APIException as e:
                                        st.warning(f"Erro ao atribuir permissão: {e.message}")
                        
                        st.rerun()
                        
                except APIException as e:
                    st.error(f"Erro ao criar papel: {e.message}")

def render_roles_statistics(roles_data, permissions_data):
    """Render roles statistics"""
    st.markdown("### 📊 Estatísticas de Papéis")
    
    if not roles_data:
        st.info("Nenhum dado disponível para estatísticas.")
        return
    
    # Basic stats
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_roles = len(roles_data)
        st.metric("Total de Papéis", total_roles)
    
    with col2:
        active_roles = len([r for r in roles_data if r.get('is_active', False)])
        st.metric("Papéis Ativos", active_roles)
    
    with col3:
        # Calculate average permissions per role
        total_permissions = sum(len(role.get('permissions', [])) for role in roles_data)
        avg_permissions = total_permissions / total_roles if total_roles > 0 else 0
        st.metric("Média de Permissões", f"{avg_permissions:.1f}")
    
    with col4:
        # Roles without permissions
        roles_without_perms = len([r for r in roles_data if not r.get('permissions')])
        st.metric("Sem Permissões", roles_without_perms)
    
    # Detailed analysis
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Roles by permission count
        st.markdown("**Papéis por Quantidade de Permissões:**")
        role_perm_data = []
        for role in roles_data:
            role_perm_data.append({
                "Papel": role.get('name', '').title(),
                "Permissões": len(role.get('permissions', [])),
                "Status": "Ativo" if role.get('is_active') else "Inativo"
            })
        
        if role_perm_data:
            df_role_perms = pd.DataFrame(role_perm_data)
            st.dataframe(df_role_perms, use_container_width=True)
    
    with col2:
        # Most used permissions
        if permissions_data:
            st.markdown("**Permissões Mais Utilizadas:**")
            perm_usage = {}
            
            for role in roles_data:
                for perm in role.get('permissions', []):
                    perm_name = perm.get('name', '')
                    perm_usage[perm_name] = perm_usage.get(perm_name, 0) + 1
            
            if perm_usage:
                # Sort by usage count
                sorted_perms = sorted(perm_usage.items(), key=lambda x: x[1], reverse=True)[:10]
                
                df_perm_usage = pd.DataFrame([
                    {"Permissão": perm, "Usos": count}
                    for perm, count in sorted_perms
                ])
                st.dataframe(df_perm_usage, use_container_width=True)
    
    # Role hierarchy visualization
    st.markdown("---")
    st.markdown("**Hierarquia de Papéis (por quantidade de permissões):**")
    
    # Sort roles by permission count
    sorted_roles = sorted(
        roles_data,
        key=lambda x: len(x.get('permissions', [])),
        reverse=True
    )
    
    for i, role in enumerate(sorted_roles):
        role_name = role.get('name', '')
        perm_count = len(role.get('permissions', []))
        status_icon = "🟢" if role.get('is_active') else "🔴"
        
        # Create visual hierarchy
        hierarchy_level = "█" * (perm_count // 2) if perm_count > 0 else "▫"
        
        col1, col2, col3, col4 = st.columns([1, 2, 1, 2])
        
        with col1:
            st.write(f"{i+1}.")
        
        with col2:
            st.write(f"{status_icon} **{role_name.title()}**")
        
        with col3:
            st.write(f"{perm_count} permissões")
        
        with col4:
            st.write(f":blue[{hierarchy_level}]")
    
    # Export functionality
    st.markdown("---")
    if st.button("📥 Exportar Lista de Papéis (CSV)"):
        try:
            # Prepare data for export
            export_data = []
            for role in roles_data:
                permissions_str = ", ".join([perm.get('name', '') for perm in role.get('permissions', [])])
                export_data.append({
                    'Papel': role.get('name', ''),
                    'Descrição': role.get('description', ''),
                    'Ativo': 'Sim' if role.get('is_active') else 'Não',
                    'Quantidade de Permissões': len(role.get('permissions', [])),
                    'Permissões': permissions_str or 'Nenhuma',
                    'Criado em': format_datetime(role.get('created_at', ''))
                })
            
            df_export = pd.DataFrame(export_data)
            csv = df_export.to_csv(index=False)
            
            st.download_button(
                label="📥 Baixar CSV",
                data=csv,
                file_name=f"papeis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )
            
        except Exception as e:
            st.error(f"Erro ao exportar dados: {str(e)}") 