import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import json
from typing import Dict, List, Any
from front.services.logs_analyzer import LogAnalyzer
from front.services.auth_service import auth_service


def show_logs_dashboard():
    """Exibe dashboard de logs em tempo real"""
    
    # Verificação de permissão
    if not auth_service.has_permission("logs:view"):
        st.error("🚫 Você não tem permissão para visualizar os logs do sistema.")
        return
    
    st.title("📊 Dashboard de Logs em Tempo Real")
    st.markdown("---")
    
    # Inicializa analyzer
    analyzer = LogAnalyzer()
    
    # ========== SIDEBAR - FILTROS ==========
    with st.sidebar:
        st.header("🎛️ Configurações")
        
        # Range de tempo
        time_options = {
            "Última 1 hora": 1,
            "Últimas 6 horas": 6,
            "Últimas 24 horas": 24,
            "Últimos 3 dias": 72,
            "Última semana": 168
        }
        
        selected_time = st.selectbox(
            "📅 Período de Análise:",
            options=list(time_options.keys()),
            index=2  # 24 horas por padrão
        )
        time_range_hours = time_options[selected_time]
        
        # Auto-refresh
        auto_refresh = st.checkbox("🔄 Auto-refresh (30s)", value=True)
        
        if auto_refresh:
            import time
            if 'last_refresh' not in st.session_state:
                st.session_state.last_refresh = time.time()
            
            # Refresh a cada 30 segundos
            if time.time() - st.session_state.last_refresh > 30:
                st.session_state.last_refresh = time.time()
                st.rerun()
        
        # Refresh manual
        if st.button("🔄 Atualizar Agora"):
            st.rerun()
    
    # ========== ALERTAS EM TEMPO REAL ==========
    st.subheader("🚨 Alertas em Tempo Real")
    
    alerts = analyzer.get_real_time_alerts()
    
    if alerts:
        alert_cols = st.columns(len(alerts) if len(alerts) <= 3 else 3)
        
        for i, alert in enumerate(alerts[:3]):  # Máximo 3 alertas
            with alert_cols[i % 3]:
                alert_level = alert.get("level", "low")
                
                if alert_level == "high":
                    alert_color = "🔴"
                    container_type = "error"
                elif alert_level == "medium":
                    alert_color = "🟡"
                    container_type = "warning"
                else:
                    alert_color = "🟢"
                    container_type = "info"
                
                with st.container():
                    if container_type == "error":
                        st.error(f"{alert_color} **{alert['type'].title()}**\n\n{alert['message']}")
                    elif container_type == "warning":
                        st.warning(f"{alert_color} **{alert['type'].title()}**\n\n{alert['message']}")
                    else:
                        st.info(f"{alert_color} **{alert['type'].title()}**\n\n{alert['message']}")
    else:
        st.success("✅ Nenhum alerta ativo no momento!")
    
    st.markdown("---")
    
    # ========== MÉTRICAS PRINCIPAIS ==========
    st.subheader("📈 Visão Geral")
    
    with st.spinner("Carregando resumo dos logs..."):
        summary = analyzer.get_logs_summary(time_range_hours)
    
    # Métricas em colunas
    metric_cols = st.columns(4)
    
    with metric_cols[0]:
        st.metric(
            label="📝 Total de Entradas",
            value=f"{summary['total_entries']:,}",
            delta=None
        )
    
    with metric_cols[1]:
        error_count = summary['by_level'].get('ERROR', 0) + summary['by_level'].get('CRITICAL', 0)
        st.metric(
            label="❌ Erros",
            value=error_count,
            delta=None
        )
    
    with metric_cols[2]:
        avg_response = summary['performance_stats']['avg_response_time']
        st.metric(
            label="⏱️ Tempo Resp. Médio",
            value=f"{avg_response:.3f}s" if avg_response > 0 else "N/A",
            delta=None
        )
    
    with metric_cols[3]:
        slow_requests = summary['performance_stats']['slow_requests']
        st.metric(
            label="🐌 Requests Lentos",
            value=slow_requests,
            delta=None
        )
    
    st.markdown("---")
    
    # ========== GRÁFICOS ==========
    tab1, tab2, tab3, tab4 = st.tabs([
        "📊 Visão Geral", 
        "🔍 Análise Detalhada", 
        "👥 Atividade de Usuários", 
        "🔧 Performance"
    ])
    
    # ===== TAB 1: VISÃO GERAL =====
    with tab1:
        col1, col2 = st.columns(2)
        
        # Gráfico de logs por nível
        with col1:
            st.subheader("📊 Logs por Nível")
            
            if summary['by_level']:
                levels_data = dict(summary['by_level'])
                
                # Define cores para cada nível
                color_map = {
                    'DEBUG': '#E8F4FD',
                    'INFO': '#4A90E2',
                    'WARNING': '#F5A623',
                    'ERROR': '#D0021B',
                    'CRITICAL': '#8B0000'
                }
                
                fig_levels = px.pie(
                    values=list(levels_data.values()),
                    names=list(levels_data.keys()),
                    color=list(levels_data.keys()),
                    color_discrete_map=color_map,
                    title=f"Distribuição nos últimos {selected_time.lower()}"
                )
                
                fig_levels.update_traces(textposition='inside', textinfo='percent+label')
                fig_levels.update_layout(height=400)
                st.plotly_chart(fig_levels, use_container_width=True)
            else:
                st.info("Nenhum dado de nível disponível para o período selecionado.")
        
        # Gráfico de logs por categoria
        with col2:
            st.subheader("🗂️ Logs por Categoria")
            
            if summary['by_category']:
                categories_data = dict(summary['by_category'])
                
                fig_categories = px.bar(
                    x=list(categories_data.keys()),
                    y=list(categories_data.values()),
                    color=list(categories_data.values()),
                    color_continuous_scale="viridis",
                    title=f"Volume por categoria"
                )
                
                fig_categories.update_layout(
                    xaxis_title="Categoria",
                    yaxis_title="Número de Logs",
                    height=400
                )
                st.plotly_chart(fig_categories, use_container_width=True)
            else:
                st.info("Nenhum dado de categoria disponível para o período selecionado.")
        
        # Timeline de atividade
        st.subheader("📈 Timeline de Atividade")
        
        if summary['by_hour']:
            hours_data = dict(summary['by_hour'])
            
            # Ordena por hora
            sorted_hours = sorted(hours_data.items())
            hours = [item[0] for item in sorted_hours]
            counts = [item[1] for item in sorted_hours]
            
            fig_timeline = px.line(
                x=hours,
                y=counts,
                title="Atividade por hora",
                markers=True
            )
            
            fig_timeline.update_layout(
                xaxis_title="Hora",
                yaxis_title="Número de Logs",
                height=300
            )
            st.plotly_chart(fig_timeline, use_container_width=True)
        else:
            st.info("Nenhum dado de timeline disponível para o período selecionado.")
    
    # ===== TAB 2: ANÁLISE DETALHADA =====
    with tab2:
        st.subheader("🔍 Explorador de Logs")
        
        # Filtros avançados
        filter_col1, filter_col2, filter_col3 = st.columns(3)
        
        with filter_col1:
            # Categoria
            available_files = analyzer.get_available_log_files()
            all_categories = list(available_files.keys())
            selected_category = st.selectbox("Categoria:", ["Todas"] + all_categories)
            
        with filter_col2:
            # Nível
            levels = ["Todos", "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
            selected_level = st.selectbox("Nível:", levels)
            
        with filter_col3:
            # Termo de busca
            search_term = st.text_input("🔍 Buscar:", placeholder="Digite para filtrar...")
        
        # Máximo de entradas
        max_entries = st.slider("Máximo de entradas:", 50, 1000, 200, 50)
        
        # Aplica filtros
        category_filter = None if selected_category == "Todas" else selected_category
        level_filter = None if selected_level == "Todos" else selected_level
        search_filter = search_term if search_term.strip() else None
        
        with st.spinner("Carregando logs filtrados..."):
            filtered_logs = analyzer.get_filtered_logs(
                category=category_filter,
                level=level_filter,
                search_term=search_filter,
                time_range_hours=time_range_hours,
                max_entries=max_entries
            )
        
        st.info(f"📋 Mostrando {len(filtered_logs)} logs de {max_entries} possíveis")
        
        # Exibe logs em tabela
        if filtered_logs:
            logs_df = pd.DataFrame(filtered_logs)
            
            # Seleciona colunas principais para exibição
            display_columns = ['timestamp', 'level', 'category', 'message']
            available_columns = [col for col in display_columns if col in logs_df.columns]
            
            if available_columns:
                display_df = logs_df[available_columns].copy()
                
                # Formata timestamp
                if 'timestamp' in display_df.columns:
                    display_df['timestamp'] = pd.to_datetime(display_df['timestamp']).dt.strftime('%Y-%m-%d %H:%M:%S')
                
                # Trunca mensagens longas
                if 'message' in display_df.columns:
                    display_df['message'] = display_df['message'].astype(str).str[:100] + '...'
                
                st.dataframe(
                    display_df,
                    use_container_width=True,
                    height=400
                )
                
                # Detalhes de log selecionado
                if st.checkbox("📋 Mostrar detalhes JSON"):
                    selected_idx = st.number_input(
                        "Índice do log (0-based):", 
                        min_value=0, 
                        max_value=len(filtered_logs)-1, 
                        value=0
                    )
                    
                    if 0 <= selected_idx < len(filtered_logs):
                        st.json(filtered_logs[selected_idx])
            else:
                st.warning("Não foi possível exibir os logs - colunas esperadas não encontradas.")
        else:
            st.warning("Nenhum log encontrado com os filtros aplicados.")
    
    # ===== TAB 3: ATIVIDADE DE USUÁRIOS =====
    with tab3:
        st.subheader("👥 Análise de Usuários")
        
        with st.spinner("Carregando estatísticas de usuários..."):
            user_stats = analyzer.get_user_activity_stats(time_range_hours)
        
        user_col1, user_col2 = st.columns(2)
        
        with user_col1:
            st.metric(
                "👥 Usuários Ativos",
                len(user_stats.get('active_users', []))
            )
            
            # Top usuários por atividade
            if user_stats.get('user_actions'):
                st.subheader("🏆 Top Usuários por Atividade")
                
                user_activity = {}
                for user, actions in user_stats['user_actions'].items():
                    user_activity[user] = sum(actions.values())
                
                top_users = sorted(user_activity.items(), key=lambda x: x[1], reverse=True)[:10]
                
                if top_users:
                    users, activities = zip(*top_users)
                    
                    fig_users = px.bar(
                        x=list(activities),
                        y=list(users),
                        orientation='h',
                        title="Ações por usuário"
                    )
                    fig_users.update_layout(height=300)
                    st.plotly_chart(fig_users, use_container_width=True)
        
        with user_col2:
            # Estatísticas de login
            total_attempts = sum(user_stats.get('login_attempts', {}).values())
            successful_logins = sum(user_stats.get('successful_logins', {}).values())
            failed_logins = sum(user_stats.get('failed_logins', {}).values())
            
            st.metric("🔑 Tentativas de Login", total_attempts)
            st.metric("✅ Logins Bem-sucedidos", successful_logins)
            st.metric("❌ Logins Falhas", failed_logins)
            
            # Success rate
            if total_attempts > 0:
                success_rate = (successful_logins / total_attempts) * 100
                st.metric("📊 Taxa de Sucesso", f"{success_rate:.1f}%")
        
        # Page views
        if user_stats.get('page_views'):
            st.subheader("📄 Páginas Mais Visitadas")
            
            page_views = dict(user_stats['page_views'])
            pages = list(page_views.keys())
            views = list(page_views.values())
            
            fig_pages = px.pie(
                values=views,
                names=pages,
                title="Distribuição de page views"
            )
            fig_pages.update_layout(height=400)
            st.plotly_chart(fig_pages, use_container_width=True)
    
    # ===== TAB 4: PERFORMANCE =====
    with tab4:
        st.subheader("⚡ Análise de Performance")
        
        with st.spinner("Carregando métricas de performance..."):
            perf_metrics = analyzer.get_performance_metrics(time_range_hours)
        
        perf_col1, perf_col2 = st.columns(2)
        
        with perf_col1:
            # Top endpoints por requests
            if perf_metrics.get('request_count_by_endpoint'):
                st.subheader("🔥 Endpoints Mais Acessados")
                
                endpoint_counts = dict(perf_metrics['request_count_by_endpoint'])
                top_endpoints = sorted(endpoint_counts.items(), key=lambda x: x[1], reverse=True)[:10]
                
                if top_endpoints:
                    endpoints, counts = zip(*top_endpoints)
                    
                    fig_endpoints = px.bar(
                        x=list(counts),
                        y=list(endpoints),
                        orientation='h',
                        title="Requests por endpoint"
                    )
                    fig_endpoints.update_layout(height=400)
                    st.plotly_chart(fig_endpoints, use_container_width=True)
        
        with perf_col2:
            # Status codes
            if perf_metrics.get('status_codes'):
                st.subheader("📊 Status Codes")
                
                status_codes = dict(perf_metrics['status_codes'])
                
                # Define cores para status codes
                colors = []
                for code in status_codes.keys():
                    if 200 <= code < 300:
                        colors.append('#4CAF50')  # Verde para 2xx
                    elif 300 <= code < 400:
                        colors.append('#FF9800')  # Laranja para 3xx
                    elif 400 <= code < 500:
                        colors.append('#F44336')  # Vermelho para 4xx
                    else:
                        colors.append('#9C27B0')  # Roxo para 5xx
                
                fig_status = px.pie(
                    values=list(status_codes.values()),
                    names=[f"{code}" for code in status_codes.keys()],
                    title="Distribuição de Status Codes",
                    color_discrete_sequence=colors
                )
                fig_status.update_layout(height=400)
                st.plotly_chart(fig_status, use_container_width=True)
        
        # Requests lentos
        if perf_metrics.get('slow_requests'):
            st.subheader("🐌 Requests Mais Lentos")
            
            slow_requests = perf_metrics['slow_requests'][:10]  # Top 10
            
            if slow_requests:
                slow_df = pd.DataFrame(slow_requests)
                
                # Formata timestamp
                if 'timestamp' in slow_df.columns:
                    slow_df['timestamp'] = pd.to_datetime(slow_df['timestamp']).dt.strftime('%H:%M:%S')
                
                # Formata duração
                if 'duration' in slow_df.columns:
                    slow_df['duration'] = slow_df['duration'].round(3)
                
                st.dataframe(
                    slow_df[['endpoint', 'duration', 'status_code', 'timestamp']],
                    use_container_width=True,
                    height=300
                )
        
        # Tempo de resposta médio por endpoint
        if perf_metrics.get('avg_response_time_by_endpoint'):
            st.subheader("⏱️ Tempo de Resposta Médio por Endpoint")
            
            response_times = dict(perf_metrics['avg_response_time_by_endpoint'])
            
            # Filtra apenas numéricos
            numeric_times = {k: v for k, v in response_times.items() if isinstance(v, (int, float))}
            
            if numeric_times:
                endpoints = list(numeric_times.keys())
                times = list(numeric_times.values())
                
                fig_response_times = px.bar(
                    x=times,
                    y=endpoints,
                    orientation='h',
                    title="Tempo médio de resposta (segundos)",
                    color=times,
                    color_continuous_scale="Reds"
                )
                fig_response_times.update_layout(height=400)
                st.plotly_chart(fig_response_times, use_container_width=True)
    
    # ========== ERROS RECENTES ==========
    if summary.get('recent_errors'):
        st.markdown("---")
        st.subheader("🚨 Erros Recentes")
        
        errors_df = pd.DataFrame(summary['recent_errors'])
        
        if not errors_df.empty:
            # Formata timestamp
            errors_df['timestamp'] = pd.to_datetime(errors_df['timestamp']).dt.strftime('%Y-%m-%d %H:%M:%S')
            
            # Trunca mensagens muito longas
            errors_df['message'] = errors_df['message'].astype(str).str[:150] + '...'
            
            st.dataframe(
                errors_df[['timestamp', 'level', 'category', 'logger', 'message']],
                use_container_width=True,
                height=200
            )
    
    # ========== FOOTER ==========
    st.markdown("---")
    st.caption(f"🔄 Última atualização: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | "
               f"📊 Período: {selected_time} | "
               f"💾 Cache: {'Ativo' if auto_refresh else 'Desabilitado'}")


if __name__ == "__main__":
    show_logs_dashboard() 