import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from front.services.auth_service import auth_service
from front.services.api_client import api_client, APIException
from front.utils.helpers import format_datetime, format_role_badge

def render_dashboard():
    """Render main dashboard"""
    st.title("📊 Dashboard Administrativo")
    
    # Welcome message
    user = auth_service.get_current_user()
    if user:
        st.markdown(f"### Bem-vindo, {user.get('full_name', user.get('username'))}! 👋")
    
    # Load dashboard data
    try:
        # Get all data in parallel
        users_data = api_client.get_users() if auth_service.has_permission("users:read") else []
        roles_data = api_client.get_roles() if auth_service.has_permission("roles:read") else []
        permissions_data = api_client.get_permissions() if auth_service.has_permission("permissions:read") else []
        
        # Render dashboard sections
        render_metrics_cards(users_data, roles_data, permissions_data)
        
        col1, col2 = st.columns(2)
        
        with col1:
            render_users_overview(users_data)
            render_recent_activity()
        
        with col2:
            render_roles_chart(roles_data)
            render_permissions_overview(permissions_data)
        
        # System status
        render_system_status()
        
    except APIException as e:
        st.error(f"Erro ao carregar dados do dashboard: {e.message}")
    except Exception as e:
        st.error(f"Erro inesperado: {str(e)}")

def render_metrics_cards(users_data, roles_data, permissions_data):
    """Render key metrics cards"""
    st.markdown("### 📈 Métricas Principais")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_users = len(users_data)
        active_users = len([u for u in users_data if u.get('is_active', False)])
        
        st.metric(
            label="👥 Usuários Totais",
            value=total_users,
            delta=f"{active_users} ativos"
        )
    
    with col2:
        total_roles = len(roles_data)
        active_roles = len([r for r in roles_data if r.get('is_active', False)])
        
        st.metric(
            label="🎭 Papéis",
            value=total_roles,
            delta=f"{active_roles} ativos"
        )
    
    with col3:
        total_permissions = len(permissions_data)
        
        st.metric(
            label="🔐 Permissões",
            value=total_permissions,
            delta="Sistema RBAC"
        )
    
    with col4:
        # Calculate OAuth users
        oauth_users = len([u for u in users_data if u.get('provider') != 'basic'])
        oauth_percentage = (oauth_users / total_users * 100) if total_users > 0 else 0
        
        st.metric(
            label="🌐 OAuth Users",
            value=oauth_users,
            delta=f"{oauth_percentage:.1f}%"
        )

def render_users_overview(users_data):
    """Render users overview"""
    st.markdown("### 👥 Visão Geral dos Usuários")
    
    if not users_data:
        st.info("Nenhum dado de usuário disponível.")
        return
    
    # Users by provider
    provider_counts = {}
    for user in users_data:
        provider = user.get('provider', 'basic')
        provider_counts[provider] = provider_counts.get(provider, 0) + 1
    
    # Create pie chart
    if provider_counts:
        df_providers = pd.DataFrame([
            {"Provider": provider.title(), "Usuários": count}
            for provider, count in provider_counts.items()
        ])
        
        fig = px.pie(
            df_providers, 
            values='Usuários', 
            names='Provider',
            title="Usuários por Provedor"
        )
        fig.update_layout(height=300)
        st.plotly_chart(fig, use_container_width=True)
    
    # Recent users table
    st.markdown("**Usuários Recentes:**")
    
    # Sort users by creation date (most recent first)
    sorted_users = sorted(
        users_data, 
        key=lambda x: x.get('created_at', ''), 
        reverse=True
    )[:5]
    
    for user in sorted_users:
        with st.container():
            col1, col2, col3 = st.columns([2, 2, 1])
            
            with col1:
                st.write(f"**{user.get('username')}**")
                st.caption(user.get('email', 'N/A'))
            
            with col2:
                roles = user.get('roles', [])
                if roles:
                    role_names = [role.get('name', '') for role in roles]
                    st.write(" ".join([format_role_badge(role) for role in role_names]))
                else:
                    st.write(":gray[Sem papéis]")
            
            with col3:
                status = "🟢" if user.get('is_active') else "🔴"
                st.write(status)
            
            st.divider()

def render_roles_chart(roles_data):
    """Render roles distribution chart"""
    st.markdown("### 🎭 Distribuição de Papéis")
    
    if not roles_data:
        st.info("Nenhum dado de papéis disponível.")
        return
    
    # Count users per role
    role_user_counts = []
    for role in roles_data:
        # This would need to be calculated from users data in a real scenario
        # For now, we'll use mock data based on role names
        role_name = role.get('name', '')
        
        # Mock user counts based on typical distribution
        mock_counts = {
            'admin': 2,
            'manager': 5,
            'editor': 12,
            'viewer': 25
        }
        
        user_count = mock_counts.get(role_name, 8)  # Default count
        
        role_user_counts.append({
            'Papel': role_name.title(),
            'Usuários': user_count,
            'Ativo': role.get('is_active', False)
        })
    
    if role_user_counts:
        df_roles = pd.DataFrame(role_user_counts)
        
        # Create bar chart
        fig = px.bar(
            df_roles,
            x='Papel',
            y='Usuários',
            color='Ativo',
            title="Usuários por Papel",
            color_discrete_map={True: '#2E8B57', False: '#CD5C5C'}
        )
        fig.update_layout(height=300)
        st.plotly_chart(fig, use_container_width=True)
    
    # Role details
    st.markdown("**Detalhes dos Papéis:**")
    for role in roles_data:
        with st.expander(f"🎭 {role.get('name', '').title()}"):
            st.write(f"**Descrição:** {role.get('description', 'N/A')}")
            st.write(f"**Status:** {'Ativo' if role.get('is_active') else 'Inativo'}")
            st.write(f"**Criado em:** {format_datetime(role.get('created_at', ''))}")
            
            permissions = role.get('permissions', [])
            if permissions:
                st.write(f"**Permissões ({len(permissions)}):**")
                for perm in permissions[:5]:  # Show first 5
                    st.write(f"- {perm.get('name', '')}")
                if len(permissions) > 5:
                    st.write(f"... e mais {len(permissions) - 5} permissões")

def render_permissions_overview(permissions_data):
    """Render permissions overview"""
    st.markdown("### 🔐 Visão Geral das Permissões")
    
    if not permissions_data:
        st.info("Nenhum dado de permissões disponível.")
        return
    
    # Group permissions by resource
    resource_counts = {}
    action_counts = {}
    
    for perm in permissions_data:
        resource = perm.get('resource', 'unknown')
        action = perm.get('action', 'unknown')
        
        resource_counts[resource] = resource_counts.get(resource, 0) + 1
        action_counts[action] = action_counts.get(action, 0) + 1
    
    # Create charts
    col1, col2 = st.columns(2)
    
    with col1:
        if resource_counts:
            df_resources = pd.DataFrame([
                {"Recurso": resource.title(), "Permissões": count}
                for resource, count in resource_counts.items()
            ])
            
            fig = px.bar(
                df_resources,
                x='Recurso',
                y='Permissões',
                title="Permissões por Recurso"
            )
            fig.update_layout(height=250)
            st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        if action_counts:
            df_actions = pd.DataFrame([
                {"Ação": action.title(), "Permissões": count}
                for action, count in action_counts.items()
            ])
            
            fig = px.pie(
                df_actions,
                values='Permissões',
                names='Ação',
                title="Permissões por Ação"
            )
            fig.update_layout(height=250)
            st.plotly_chart(fig, use_container_width=True)

def render_recent_activity():
    """Render recent activity (mock data for demo)"""
    st.markdown("### 📝 Atividade Recente")
    
    # Mock recent activity data
    activities = [
        {
            "time": datetime.now() - timedelta(minutes=5),
            "user": "admin",
            "action": "Criou papel 'moderator'",
            "icon": "🎭"
        },
        {
            "time": datetime.now() - timedelta(minutes=15),
            "user": "manager01",
            "action": "Atualizou usuário 'editor01'",
            "icon": "👥"
        },
        {
            "time": datetime.now() - timedelta(hours=1),
            "user": "admin",
            "action": "Criou permissão 'posts:moderate'",
            "icon": "🔐"
        },
        {
            "time": datetime.now() - timedelta(hours=2),
            "user": "editor01",
            "action": "Login realizado",
            "icon": "🚪"
        },
        {
            "time": datetime.now() - timedelta(hours=3),
            "user": "admin",
            "action": "Registrou novo usuário",
            "icon": "✨"
        }
    ]
    
    for activity in activities:
        time_str = activity["time"].strftime("%H:%M")
        
        with st.container():
            col1, col2 = st.columns([1, 4])
            
            with col1:
                st.write(f"{activity['icon']} {time_str}")
            
            with col2:
                st.write(f"**{activity['user']}** {activity['action']}")
            
            st.divider()

def render_system_status():
    """Render system status"""
    st.markdown("### ⚙️ Status do Sistema")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("**🔗 API Backend**")
        try:
            health_data = api_client.health_check()
            if health_data.get("status") == "healthy":
                st.success("✅ Online")
            else:
                st.warning("⚠️ Instável")
        except:
            st.error("❌ Offline")
    
    with col2:
        st.markdown("**🔐 Autenticação**")
        if auth_service.is_authenticated():
            st.success("✅ Autenticado")
        else:
            st.error("❌ Não autenticado")
    
    with col3:
        st.markdown("**🎭 RBAC**")
        user = auth_service.get_current_user()
        if user and user.get('roles'):
            st.success("✅ Configurado")
        else:
            st.warning("⚠️ Sem papéis")
    
    # System info
    with st.expander("ℹ️ Informações do Sistema"):
        st.markdown(f"""
        **Versão:** 1.0.0  
        **Uptime:** Simulado - {datetime.now().strftime('%H:%M:%S')}  
        **Última atualização:** {datetime.now().strftime('%d/%m/%Y %H:%M')}  
        **Usuário atual:** {user.get('username') if user else 'N/A'}  
        **Permissões ativas:** {len(auth_service.get_user_permissions())}  
        """) 