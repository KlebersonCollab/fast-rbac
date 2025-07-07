import streamlit as st
import pandas as pd
from datetime import datetime
from front.services.auth_service import auth_service
from front.services.api_client import api_client, APIException
from front.utils.helpers import format_datetime, format_permission_badge
from front.components.auth import check_permission_ui

def render_permissions_page():
    """Render permissions management page"""
    st.title("🔐 Gerenciamento de Permissões")
    
    # Check permissions
    if not check_permission_ui("permissions:read"):
        return
    
    try:
        # Load data
        permissions_data = api_client.get_permissions()
        roles_data = api_client.get_roles() if auth_service.has_permission("roles:read") else []
        
        # Page tabs
        tab1, tab2, tab3 = st.tabs(["📋 Lista de Permissões", "➕ Nova Permissão", "📊 Estatísticas"])
        
        with tab1:
            render_permissions_list(permissions_data, roles_data)
        
        with tab2:
            if auth_service.has_permission("permissions:create"):
                render_create_permission_form()
            else:
                st.error("Você não tem permissão para criar permissões.")
        
        with tab3:
            render_permissions_statistics(permissions_data, roles_data)
            
    except APIException as e:
        st.error(f"Erro ao carregar dados: {e.message}")
    except Exception as e:
        st.error(f"Erro inesperado: {str(e)}")

def render_permissions_list(permissions_data, roles_data):
    """Render permissions list"""
    st.markdown("### 📋 Lista de Permissões")
    
    if not permissions_data:
        st.info("Nenhuma permissão encontrada.")
        return
    
    # Search and filters
    col1, col2, col3 = st.columns([3, 1, 1])
    
    with col1:
        search_term = st.text_input("🔍 Buscar permissões", placeholder="Digite o nome, recurso ou ação...")
    
    with col2:
        # Resource filter
        resources = list(set([perm.get('resource', 'other') for perm in permissions_data]))
        selected_resource = st.selectbox("Recurso", ["Todos"] + sorted(resources))
    
    with col3:
        # Action filter
        actions = list(set([perm.get('action', 'other') for perm in permissions_data]))
        selected_action = st.selectbox("Ação", ["Todos"] + sorted(actions))
    
    # Filter permissions
    filtered_permissions = permissions_data
    
    if search_term:
        filtered_permissions = [
            perm for perm in filtered_permissions
            if (search_term.lower() in perm.get('name', '').lower() or
                search_term.lower() in perm.get('resource', '').lower() or
                search_term.lower() in perm.get('action', '').lower() or
                search_term.lower() in perm.get('description', '').lower())
        ]
    
    if selected_resource != "Todos":
        filtered_permissions = [
            perm for perm in filtered_permissions
            if perm.get('resource', 'other') == selected_resource
        ]
    
    if selected_action != "Todos":
        filtered_permissions = [
            perm for perm in filtered_permissions
            if perm.get('action', 'other') == selected_action
        ]
    
    st.info(f"Encontradas {len(filtered_permissions)} permissão(ões) de {len(permissions_data)} total.")
    
    # Group permissions by resource for better organization
    permissions_by_resource = {}
    for perm in filtered_permissions:
        resource = perm.get('resource', 'other')
        if resource not in permissions_by_resource:
            permissions_by_resource[resource] = []
        permissions_by_resource[resource].append(perm)
    
    # Display permissions grouped by resource
    for resource, perms in sorted(permissions_by_resource.items()):
        with st.expander(f"📁 {resource.title()} ({len(perms)} permissões)", expanded=True):
            for i, perm in enumerate(perms):
                render_permission_card(perm, roles_data, f"{resource}_{i}")

def render_permission_card(permission, roles_data, index):
    """Render individual permission card"""
    col1, col2, col3, col4 = st.columns([2, 2, 2, 1])
    
    with col1:
        # Permission basic info
        perm_name = permission.get('name', '')
        st.markdown(f"**{format_permission_badge(perm_name)}**")
        
        # Resource and action
        resource = permission.get('resource', 'N/A')
        action = permission.get('action', 'N/A')
        st.caption(f"📁 {resource} → 🎯 {action}")
    
    with col2:
        # Description
        description = permission.get('description', 'Sem descrição')
        st.markdown(f"**Descrição:**")
        st.caption(description)
    
    with col3:
        # Usage in roles
        st.markdown("**Usado em:**")
        
        # Calculate which roles use this permission
        using_roles = []
        for role in roles_data:
            role_permissions = role.get('permissions', [])
            for role_perm in role_permissions:
                if role_perm.get('id') == permission.get('id'):
                    using_roles.append(role.get('name', ''))
                    break
        
        if using_roles:
            for role_name in using_roles[:3]:  # Show first 3 roles
                st.caption(f"🎭 {role_name}")
            if len(using_roles) > 3:
                st.caption(f"... e mais {len(using_roles) - 3} papel(éis)")
        else:
            st.caption(":gray[Não utilizada]")
    
    with col4:
        # Actions (limited for permissions as they're more sensitive)
        if auth_service.has_permission("permissions:delete"):
            # Only allow deletion of custom permissions (not system ones)
            if not is_system_permission(permission):
                if st.button("🗑️", key=f"delete_perm_{index}", help="Deletar permissão"):
                    if st.session_state.get(f'confirm_delete_perm_{index}', False):
                        try:
                            # Note: Delete permission endpoint not implemented in backend
                            st.warning("Funcionalidade de deletar permissão não implementada no backend.")
                            st.session_state[f'confirm_delete_perm_{index}'] = False
                        except APIException as e:
                            st.error(f"Erro ao deletar permissão: {e.message}")
                    else:
                        st.session_state[f'confirm_delete_perm_{index}'] = True
                        st.rerun()
            else:
                st.caption("🔒 Sistema")
    
    # Creation date
    if permission.get('created_at'):
        st.caption(f"Criado: {format_datetime(permission.get('created_at'))}")
    
    st.divider()

def is_system_permission(permission):
    """Check if permission is a system permission that shouldn't be deleted"""
    system_permissions = [
        'users:create', 'users:read', 'users:update', 'users:delete',
        'roles:create', 'roles:read', 'roles:update', 'roles:delete',
        'permissions:create', 'permissions:read', 'permissions:update', 'permissions:delete',
        'posts:create', 'posts:read', 'posts:update', 'posts:delete'
    ]
    return permission.get('name', '') in system_permissions

def render_create_permission_form():
    """Render create permission form"""
    st.markdown("### ➕ Criar Nova Permissão")
    
    with st.form("create_permission_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            # Resource selection
            st.markdown("**Recurso:**")
            resource_options = [
                "users", "roles", "permissions", "posts", "settings", 
                "reports", "dashboard", "logs", "notifications", "outros"
            ]
            selected_resource = st.selectbox("Selecione o recurso", resource_options)
            
            if selected_resource == "outros":
                custom_resource = st.text_input("Recurso personalizado", placeholder="nome_do_recurso")
                resource = custom_resource if custom_resource else "custom"
            else:
                resource = selected_resource
        
        with col2:
            # Action selection
            st.markdown("**Ação:**")
            action_options = ["create", "read", "update", "delete", "list", "view", "manage", "outros"]
            selected_action = st.selectbox("Selecione a ação", action_options)
            
            if selected_action == "outros":
                custom_action = st.text_input("Ação personalizada", placeholder="nome_da_acao")
                action = custom_action if custom_action else "custom"
            else:
                action = selected_action
        
        # Auto-generate permission name
        if resource and action:
            suggested_name = f"{resource}:{action}"
        else:
            suggested_name = ""
        
        # Permission details
        st.markdown("**Detalhes da Permissão:**")
        name = st.text_input("Nome da Permissão *", value=suggested_name, placeholder="recurso:acao")
        description = st.text_area("Descrição", placeholder="Descreva o que esta permissão permite fazer")
        
        # Permission preview
        if name:
            st.markdown("**Preview:**")
            st.markdown(f"Permissão: {format_permission_badge(name)}")
            st.caption(f"Recurso: {resource} | Ação: {action}")
        
        if st.form_submit_button("✅ Criar Permissão", use_container_width=True):
            # Validation
            if not all([name, resource, action]):
                st.error("Por favor, preencha todos os campos obrigatórios.")
            elif ":" not in name:
                st.error("O nome da permissão deve seguir o formato 'recurso:acao'.")
            else:
                try:
                    response = api_client.create_permission(name, resource, action, description)
                    
                    if response:
                        st.success(f"Permissão {name} criada com sucesso!")
                        st.rerun()
                        
                except APIException as e:
                    st.error(f"Erro ao criar permissão: {e.message}")

def render_permissions_statistics(permissions_data, roles_data):
    """Render permissions statistics"""
    st.markdown("### 📊 Estatísticas de Permissões")
    
    if not permissions_data:
        st.info("Nenhum dado disponível para estatísticas.")
        return
    
    # Basic stats
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_permissions = len(permissions_data)
        st.metric("Total de Permissões", total_permissions)
    
    with col2:
        # Unique resources
        unique_resources = len(set(perm.get('resource', 'other') for perm in permissions_data))
        st.metric("Recursos", unique_resources)
    
    with col3:
        # Unique actions
        unique_actions = len(set(perm.get('action', 'other') for perm in permissions_data))
        st.metric("Ações", unique_actions)
    
    with col4:
        # Usage in roles
        used_permissions = set()
        for role in roles_data:
            for perm in role.get('permissions', []):
                used_permissions.add(perm.get('id'))
        st.metric("Utilizadas", len(used_permissions))
    
    # Detailed analysis
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Permissions by resource
        st.markdown("**Permissões por Recurso:**")
        resource_counts = {}
        for perm in permissions_data:
            resource = perm.get('resource', 'other')
            resource_counts[resource] = resource_counts.get(resource, 0) + 1
        
        if resource_counts:
            df_resources = pd.DataFrame([
                {"Recurso": resource.title(), "Quantidade": count}
                for resource, count in sorted(resource_counts.items())
            ])
            st.dataframe(df_resources, use_container_width=True)
    
    with col2:
        # Permissions by action
        st.markdown("**Permissões por Ação:**")
        action_counts = {}
        for perm in permissions_data:
            action = perm.get('action', 'other')
            action_counts[action] = action_counts.get(action, 0) + 1
        
        if action_counts:
            df_actions = pd.DataFrame([
                {"Ação": action.title(), "Quantidade": count}
                for action, count in sorted(action_counts.items())
            ])
            st.dataframe(df_actions, use_container_width=True)
    
    # Permission usage analysis
    st.markdown("---")
    st.markdown("**Análise de Uso das Permissões:**")
    
    # Calculate usage for each permission
    permission_usage = {}
    for perm in permissions_data:
        perm_id = perm.get('id')
        perm_name = perm.get('name', '')
        usage_count = 0
        
        for role in roles_data:
            for role_perm in role.get('permissions', []):
                if role_perm.get('id') == perm_id:
                    usage_count += 1
                    break
        
        permission_usage[perm_name] = usage_count
    
    # Split into used and unused
    used_perms = {k: v for k, v in permission_usage.items() if v > 0}
    unused_perms = {k: v for k, v in permission_usage.items() if v == 0}
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**Permissões Mais Utilizadas:**")
        if used_perms:
            sorted_used = sorted(used_perms.items(), key=lambda x: x[1], reverse=True)[:10]
            for perm_name, count in sorted_used:
                st.write(f"• {format_permission_badge(perm_name)} - {count} papel(éis)")
        else:
            st.info("Nenhuma permissão está sendo utilizada.")
    
    with col2:
        st.markdown("**Permissões Não Utilizadas:**")
        if unused_perms:
            st.warning(f"{len(unused_perms)} permissão(ões) não estão sendo utilizadas:")
            for perm_name in list(unused_perms.keys())[:10]:
                st.write(f"• {format_permission_badge(perm_name)}")
            if len(unused_perms) > 10:
                st.caption(f"... e mais {len(unused_perms) - 10} permissão(ões)")
        else:
            st.success("Todas as permissões estão sendo utilizadas!")
    
    # CRUD patterns analysis
    st.markdown("---")
    st.markdown("**Padrões CRUD por Recurso:**")
    
    crud_analysis = {}
    crud_actions = ['create', 'read', 'update', 'delete']
    
    for perm in permissions_data:
        resource = perm.get('resource', 'other')
        action = perm.get('action', 'other')
        
        if resource not in crud_analysis:
            crud_analysis[resource] = {action: False for action in crud_actions}
        
        if action in crud_actions:
            crud_analysis[resource][action] = True
    
    for resource, actions in crud_analysis.items():
        crud_complete = all(actions.values())
        crud_count = sum(actions.values())
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.write(f"**{resource.title()}**")
            status_icons = []
            for action in crud_actions:
                icon = "✅" if actions[action] else "❌"
                status_icons.append(f"{icon} {action}")
            st.caption(" | ".join(status_icons))
        
        with col2:
            if crud_complete:
                st.success("CRUD Completo")
            else:
                st.info(f"{crud_count}/4 operações")
    
    # Export functionality
    st.markdown("---")
    if st.button("📥 Exportar Lista de Permissões (CSV)"):
        try:
            # Prepare data for export
            export_data = []
            for perm in permissions_data:
                # Count usage
                usage_count = 0
                using_roles = []
                for role in roles_data:
                    for role_perm in role.get('permissions', []):
                        if role_perm.get('id') == perm.get('id'):
                            usage_count += 1
                            using_roles.append(role.get('name', ''))
                            break
                
                export_data.append({
                    'Nome': perm.get('name', ''),
                    'Recurso': perm.get('resource', ''),
                    'Ação': perm.get('action', ''),
                    'Descrição': perm.get('description', ''),
                    'Usado em Papéis': usage_count,
                    'Papéis': ', '.join(using_roles) if using_roles else 'Nenhum',
                    'Criado em': format_datetime(perm.get('created_at', ''))
                })
            
            df_export = pd.DataFrame(export_data)
            csv = df_export.to_csv(index=False)
            
            st.download_button(
                label="📥 Baixar CSV",
                data=csv,
                file_name=f"permissoes_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )
            
        except Exception as e:
            st.error(f"Erro ao exportar dados: {str(e)}") 