import time
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

import streamlit as st


def format_datetime(dt_str: str) -> str:
    """Format datetime string for display"""
    try:
        dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
        return dt.strftime("%d/%m/%Y %H:%M")
    except:
        return dt_str


def show_success_message(message: str, duration: int = 3):
    """Show success message"""
    success_placeholder = st.empty()
    success_placeholder.success(message)
    time.sleep(duration)
    success_placeholder.empty()


def show_error_message(message: str, duration: int = 5):
    """Show error message"""
    error_placeholder = st.empty()
    error_placeholder.error(message)
    time.sleep(duration)
    error_placeholder.empty()


def show_warning_message(message: str, duration: int = 4):
    """Show warning message"""
    warning_placeholder = st.empty()
    warning_placeholder.warning(message)
    time.sleep(duration)
    warning_placeholder.empty()


def format_role_badge(role_name: str) -> str:
    """Format role as colored badge"""
    color_map = {
        "admin": "red",
        "manager": "orange",
        "editor": "blue",
        "viewer": "gray",
    }
    color = color_map.get(role_name.lower(), "gray")
    return f":{color}[{role_name}]"


def format_permission_badge(permission: str) -> str:
    """Format permission as colored badge"""
    if "create" in permission:
        return f":green[{permission}]"
    elif "read" in permission:
        return f":blue[{permission}]"
    elif "update" in permission:
        return f":orange[{permission}]"
    elif "delete" in permission:
        return f":red[{permission}]"
    else:
        return f":gray[{permission}]"


def check_session_timeout() -> bool:
    """Check if session has expired"""
    if "last_activity" not in st.session_state:
        return True

    last_activity = st.session_state.last_activity
    now = datetime.now()

    # Import here to avoid circular import
    from front.config.settings import settings

    timeout_minutes = settings.SESSION_TIMEOUT

    if now - last_activity > timedelta(minutes=timeout_minutes):
        return True

    # Update last activity
    st.session_state.last_activity = now
    return False


def clear_session():
    """Clear all session state"""
    keys_to_keep = ["page"]  # Keep page navigation
    for key in list(st.session_state.keys()):
        if key not in keys_to_keep:
            del st.session_state[key]


def init_session_state():
    """Initialize session state variables"""
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if "user" not in st.session_state:
        st.session_state.user = None
    if "token" not in st.session_state:
        st.session_state.token = None
    if "last_activity" not in st.session_state:
        st.session_state.last_activity = datetime.now()
    if "page" not in st.session_state:
        st.session_state.page = "Dashboard"


def create_data_table(data: list, columns: list, key_prefix: str = "table"):
    """Create interactive data table"""
    if not data:
        st.info("Nenhum dado encontrado.")
        return None

    import pandas as pd

    df = pd.DataFrame(data)

    # Filter columns if specified
    if columns and len(columns) > 0:
        available_cols = [col for col in columns if col in df.columns]
        if available_cols:
            df = df[available_cols]

    # Display with pagination
    page_size = 10
    total_rows = len(df)

    if total_rows > page_size:
        # Pagination controls
        col1, col2, col3 = st.columns([1, 2, 1])

        with col2:
            page = st.selectbox(
                "Página",
                range(1, (total_rows // page_size) + 2),
                key=f"{key_prefix}_page",
            )

        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        df_page = df.iloc[start_idx:end_idx]

        st.info(
            f"Mostrando {start_idx + 1}-{min(end_idx, total_rows)} de {total_rows} registros"
        )
    else:
        df_page = df

    return st.dataframe(df_page, use_container_width=True, key=f"{key_prefix}_df")


def confirm_action(message: str, key: str) -> bool:
    """Show confirmation dialog"""
    if f"confirm_{key}" not in st.session_state:
        st.session_state[f"confirm_{key}"] = False

    if not st.session_state[f"confirm_{key}"]:
        if st.button(f"❌ {message}", key=f"btn_{key}"):
            st.session_state[f"confirm_{key}"] = True
            st.rerun()
        return False
    else:
        col1, col2 = st.columns(2)
        with col1:
            if st.button("✅ Confirmar", key=f"confirm_yes_{key}"):
                st.session_state[f"confirm_{key}"] = False
                return True
        with col2:
            if st.button("❌ Cancelar", key=f"confirm_no_{key}"):
                st.session_state[f"confirm_{key}"] = False
                st.rerun()
        return False


# Aliases para as funções esperadas pelas views do nível 5
def show_success(message: str):
    """Show success message - alias for compatibility"""
    st.success(message)


def show_error(message: str):
    """Show error message - alias for compatibility"""
    st.error(message)


def show_warning(message: str):
    """Show warning message - alias for compatibility"""
    st.warning(message)


def convert_timestamp_with_timezone(timestamp_data):
    """Convert timestamp with timezone handling - works with strings or pandas Series"""
    if timestamp_data is None:
        return "N/A"

    import pandas as pd

    # Se for uma Series do pandas, aplicar a função elemento por elemento
    if isinstance(timestamp_data, pd.Series):
        return timestamp_data.apply(lambda x: _convert_single_timestamp(x))

    # Se for uma string, processar diretamente
    return _convert_single_timestamp(timestamp_data)


def _convert_single_timestamp(timestamp_str: str) -> str:
    """Convert a single timestamp string"""
    if not timestamp_str or pd.isna(timestamp_str):
        return "N/A"

    try:
        import pandas as pd

        # Use pandas para parsing robusto de timestamps ISO8601
        dt = pd.to_datetime(timestamp_str, format="ISO8601")
        return dt.strftime("%d/%m/%Y %H:%M")
    except Exception:
        try:
            # Fallback para parsing manual
            clean_timestamp = str(timestamp_str).replace("Z", "+00:00")
            dt = datetime.fromisoformat(clean_timestamp)
            return dt.strftime("%d/%m/%Y %H:%M")
        except Exception:
            return str(timestamp_str)


def safe_json_loads(data, default=None):
    """
    Safely parse JSON data that might already be a Python object
    
    Args:
        data: Data that might be a JSON string or already parsed object
        default: Default value if parsing fails or data is None
        
    Returns:
        Parsed data or default value
    """
    if default is None:
        default = []
        
    if data is None:
        return default
        
    # If already a list or dict, return as is
    if isinstance(data, (list, dict)):
        return data
        
    # If string, try to parse as JSON
    if isinstance(data, str):
        try:
            import json
            return json.loads(data)
        except (json.JSONDecodeError, ValueError):
            return default
            
    return default
