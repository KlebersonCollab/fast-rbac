import json
import os
import re
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import streamlit as st


class LogAnalyzer:
    """Serviço para análise de logs em tempo real"""

    def __init__(self):
        self.logs_dir = Path("logs")
        self.backend_logs_dir = self.logs_dir / "backend"
        self.frontend_logs_dir = self.logs_dir / "frontend"
        self.system_logs_dir = self.logs_dir / "system"

    def get_available_log_files(self) -> Dict[str, List[str]]:
        """Retorna todos os arquivos de log disponíveis organizados por categoria"""
        categories = {"Backend": [], "Frontend": [], "System": []}

        # Backend logs
        if self.backend_logs_dir.exists():
            for log_file in self.backend_logs_dir.rglob("*.log"):
                rel_path = str(log_file.relative_to(self.backend_logs_dir))
                categories["Backend"].append(rel_path)

        # Frontend logs
        if self.frontend_logs_dir.exists():
            for log_file in self.frontend_logs_dir.rglob("*.log"):
                rel_path = str(log_file.relative_to(self.frontend_logs_dir))
                categories["Frontend"].append(rel_path)

        # System logs
        if self.system_logs_dir.exists():
            for log_file in self.system_logs_dir.rglob("*.log"):
                rel_path = str(log_file.relative_to(self.system_logs_dir))
                categories["System"].append(rel_path)

        return categories

    def read_log_file(
        self, category: str, filename: str, max_lines: int = 1000
    ) -> List[Dict[str, Any]]:
        """Lê arquivo de log e retorna lista de entries"""
        try:
            if category.lower() == "backend":
                log_path = self.backend_logs_dir / filename
            elif category.lower() == "frontend":
                log_path = self.frontend_logs_dir / filename
            elif category.lower() == "system":
                log_path = self.system_logs_dir / filename
            else:
                return []

            if not log_path.exists():
                return []

            entries = []
            with open(log_path, "r", encoding="utf-8") as file:
                lines = file.readlines()

                # Pega as últimas N linhas
                recent_lines = lines[-max_lines:] if len(lines) > max_lines else lines

                for line in recent_lines:
                    line = line.strip()
                    if not line:
                        continue

                    # Tenta parsear como JSON primeiro
                    try:
                        entry = json.loads(line)
                        entry["raw_line"] = line
                        entry["log_file"] = filename
                        entry["category"] = category
                        entries.append(entry)
                    except json.JSONDecodeError:
                        # Se não for JSON, tenta parsear formato texto
                        parsed = self._parse_text_log(line)
                        if parsed:
                            parsed["raw_line"] = line
                            parsed["log_file"] = filename
                            parsed["category"] = category
                            entries.append(parsed)

            return entries

        except Exception as e:
            st.error(f"Erro ao ler arquivo {filename}: {str(e)}")
            return []

    def _parse_text_log(self, line: str) -> Optional[Dict[str, Any]]:
        """Parse de logs em formato texto (não JSON)"""
        # Pattern para logs do sistema (formato básico)
        pattern = (
            r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) - ([^-]+) - (\w+) - ([^-]+) - (.+)"
        )
        match = re.match(pattern, line)

        if match:
            timestamp_str, logger, level, location, message = match.groups()
            try:
                timestamp = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
                return {
                    "timestamp": timestamp.isoformat(),
                    "level": level.strip(),
                    "logger": logger.strip(),
                    "message": message.strip(),
                    "module": location.split(":")[0] if ":" in location else location,
                    "function": location.split(":")[1] if ":" in location else "",
                    "line": location.split(":")[2] if location.count(":") >= 2 else "",
                }
            except ValueError:
                pass

        return None

    def get_logs_summary(self, time_range_hours: int = 24) -> Dict[str, Any]:
        """Retorna resumo geral dos logs"""
        cutoff_time = datetime.now() - timedelta(hours=time_range_hours)

        summary = {
            "total_entries": 0,
            "by_level": defaultdict(int),
            "by_category": defaultdict(int),
            "by_hour": defaultdict(int),
            "recent_errors": [],
            "top_endpoints": defaultdict(int),
            "top_users": defaultdict(int),
            "performance_stats": {
                "avg_response_time": 0,
                "slow_requests": 0,
                "total_requests": 0,
            },
        }

        # Analisa todos os arquivos de log
        categories = self.get_available_log_files()
        all_entries = []

        for category, files in categories.items():
            for filename in files:
                entries = self.read_log_file(category, filename, max_lines=5000)
                all_entries.extend(entries)

        # Processa entradas
        response_times = []

        for entry in all_entries:
            try:
                # Converte timestamp
                if "timestamp" in entry:
                    timestamp_str = entry["timestamp"]
                    if timestamp_str.endswith("Z"):
                        timestamp_str = timestamp_str[:-1]

                    entry_time = datetime.fromisoformat(
                        timestamp_str.replace("Z", "+00:00").replace("+00:00", "")
                    )

                    # Filtra por período
                    if entry_time < cutoff_time:
                        continue

                    # Estatísticas básicas
                    summary["total_entries"] += 1
                    summary["by_level"][entry.get("level", "UNKNOWN")] += 1
                    summary["by_category"][entry.get("category", "UNKNOWN")] += 1

                    # Por hora
                    hour_key = entry_time.strftime("%H:00")
                    summary["by_hour"][hour_key] += 1

                    # Erros recentes
                    if entry.get("level") in ["ERROR", "CRITICAL"]:
                        summary["recent_errors"].append(
                            {
                                "timestamp": timestamp_str,
                                "message": entry.get("message", ""),
                                "logger": entry.get("logger", ""),
                                "category": entry.get("category", ""),
                            }
                        )

                    # Endpoints
                    endpoint = entry.get("endpoint")
                    if endpoint:
                        summary["top_endpoints"][endpoint] += 1

                    # Usuários
                    username = entry.get("username")
                    if username and username != "null":
                        summary["top_users"][username] += 1

                    # Performance
                    duration = entry.get("duration")
                    if duration and isinstance(duration, (int, float)):
                        response_times.append(duration)
                        summary["performance_stats"]["total_requests"] += 1

                        if duration > 1.0:  # > 1 segundo
                            summary["performance_stats"]["slow_requests"] += 1

            except Exception as e:
                continue  # Ignora entradas com erro

        # Calcula estatísticas de performance
        if response_times:
            summary["performance_stats"]["avg_response_time"] = sum(
                response_times
            ) / len(response_times)

        # Ordena e limita resultados
        summary["recent_errors"] = sorted(
            summary["recent_errors"][-20:], key=lambda x: x["timestamp"], reverse=True
        )

        return dict(summary)

    def get_filtered_logs(
        self,
        category: str = None,
        log_file: str = None,
        level: str = None,
        username: str = None,
        search_term: str = None,
        time_range_hours: int = 24,
        max_entries: int = 500,
    ) -> List[Dict[str, Any]]:
        """Retorna logs filtrados por critérios específicos"""
        cutoff_time = datetime.now() - timedelta(hours=time_range_hours)

        # Determina quais arquivos ler
        if category and log_file:
            files_to_read = [(category, log_file)]
        else:
            files_to_read = []
            categories = self.get_available_log_files()

            for cat, files in categories.items():
                if category and cat.lower() != category.lower():
                    continue
                for filename in files:
                    files_to_read.append((cat, filename))

        # Lê e filtra logs
        filtered_entries = []

        for cat, filename in files_to_read:
            entries = self.read_log_file(cat, filename, max_lines=2000)

            for entry in entries:
                try:
                    # Filtro por tempo
                    if "timestamp" in entry:
                        timestamp_str = entry["timestamp"]
                        if timestamp_str.endswith("Z"):
                            timestamp_str = timestamp_str[:-1]

                        entry_time = datetime.fromisoformat(
                            timestamp_str.replace("Z", "+00:00").replace("+00:00", "")
                        )

                        if entry_time < cutoff_time:
                            continue

                    # Filtro por nível
                    if level and entry.get("level", "").upper() != level.upper():
                        continue

                    # Filtro por usuário
                    if username and entry.get("username", "") != username:
                        continue

                    # Filtro por termo de busca
                    if search_term:
                        search_term_lower = search_term.lower()
                        searchable_text = " ".join(
                            [
                                str(entry.get("message", "")),
                                str(entry.get("endpoint", "")),
                                str(entry.get("action", "")),
                                str(entry.get("logger", "")),
                            ]
                        ).lower()

                        if search_term_lower not in searchable_text:
                            continue

                    filtered_entries.append(entry)

                except Exception:
                    continue

        # Ordena por timestamp (mais recente primeiro)
        filtered_entries.sort(key=lambda x: x.get("timestamp", ""), reverse=True)

        # Limita resultados
        return filtered_entries[:max_entries]

    def get_performance_metrics(self, time_range_hours: int = 24) -> Dict[str, Any]:
        """Retorna métricas de performance detalhadas"""
        metrics = {
            "request_count_by_endpoint": defaultdict(int),
            "avg_response_time_by_endpoint": defaultdict(list),
            "status_codes": defaultdict(int),
            "error_rate_by_hour": defaultdict(lambda: {"total": 0, "errors": 0}),
            "slow_requests": [],
            "top_error_messages": defaultdict(int),
        }

        # Analisa logs de API
        api_entries = self.read_log_file("Backend", "api/access.log", max_lines=5000)
        cutoff_time = datetime.now() - timedelta(hours=time_range_hours)

        for entry in api_entries:
            try:
                if "timestamp" in entry:
                    timestamp_str = entry["timestamp"]
                    entry_time = datetime.fromisoformat(
                        timestamp_str.replace("Z", "+00:00").replace("+00:00", "")
                    )

                    if entry_time < cutoff_time:
                        continue

                    endpoint = entry.get("endpoint", "unknown")
                    duration = entry.get("duration", 0)
                    status_code = entry.get("status_code", 0)

                    # Contadores
                    metrics["request_count_by_endpoint"][endpoint] += 1
                    metrics["status_codes"][status_code] += 1

                    # Tempos de resposta
                    if isinstance(duration, (int, float)) and duration > 0:
                        metrics["avg_response_time_by_endpoint"][endpoint].append(
                            duration
                        )

                        # Requests lentos (> 2 segundos)
                        if duration > 2.0:
                            metrics["slow_requests"].append(
                                {
                                    "endpoint": endpoint,
                                    "duration": duration,
                                    "timestamp": timestamp_str,
                                    "status_code": status_code,
                                }
                            )

                    # Taxa de erro por hora
                    hour_key = entry_time.strftime("%H:00")
                    metrics["error_rate_by_hour"][hour_key]["total"] += 1

                    if status_code >= 400:
                        metrics["error_rate_by_hour"][hour_key]["errors"] += 1

                        # Mensagens de erro
                        message = entry.get("message", "")
                        if message:
                            metrics["top_error_messages"][message] += 1

            except Exception:
                continue

        # Calcula médias
        for endpoint, times in metrics["avg_response_time_by_endpoint"].items():
            if times:
                metrics["avg_response_time_by_endpoint"][endpoint] = sum(times) / len(
                    times
                )

        # Ordena requests lentos
        metrics["slow_requests"] = sorted(
            metrics["slow_requests"][-50:], key=lambda x: x["duration"], reverse=True
        )

        return dict(metrics)

    def get_user_activity_stats(self, time_range_hours: int = 24) -> Dict[str, Any]:
        """Retorna estatísticas de atividade dos usuários"""
        stats = {
            "active_users": set(),
            "login_attempts": defaultdict(int),
            "successful_logins": defaultdict(int),
            "failed_logins": defaultdict(int),
            "user_actions": defaultdict(lambda: defaultdict(int)),
            "page_views": defaultdict(int),
            "permission_checks": defaultdict(lambda: {"granted": 0, "denied": 0}),
        }

        cutoff_time = datetime.now() - timedelta(hours=time_range_hours)

        # Analisa logs de ações do usuário
        user_entries = self.read_log_file(
            "Frontend", "user_actions/actions.log", max_lines=3000
        )

        for entry in user_entries:
            try:
                if "timestamp" in entry:
                    timestamp_str = entry["timestamp"]
                    entry_time = datetime.fromisoformat(
                        timestamp_str.replace("Z", "+00:00").replace("+00:00", "")
                    )

                    if entry_time < cutoff_time:
                        continue

                    username = entry.get("username", "unknown")
                    action = entry.get("action", "")
                    page = entry.get("page", "")
                    success = entry.get("success", True)

                    if username and username != "null":
                        stats["active_users"].add(username)

                        # Login tracking
                        if action == "login_attempt":
                            stats["login_attempts"][username] += 1
                        elif action == "login" and success:
                            stats["successful_logins"][username] += 1
                        elif action in ["login_failed", "login_error"]:
                            stats["failed_logins"][username] += 1

                        # Ações por usuário
                        stats["user_actions"][username][action] += 1

                        # Page views
                        if action == "page_navigation" and page:
                            stats["page_views"][page] += 1

            except Exception:
                continue

        # Analisa logs de permissões
        perm_entries = self.read_log_file(
            "Frontend", "permissions/permissions.log", max_lines=2000
        )

        for entry in perm_entries:
            try:
                if "timestamp" in entry:
                    timestamp_str = entry["timestamp"]
                    entry_time = datetime.fromisoformat(
                        timestamp_str.replace("Z", "+00:00").replace("+00:00", "")
                    )

                    if entry_time < cutoff_time:
                        continue

                    permission = entry.get("permission", "")
                    granted = entry.get("granted", False)

                    if permission:
                        if granted:
                            stats["permission_checks"][permission]["granted"] += 1
                        else:
                            stats["permission_checks"][permission]["denied"] += 1

            except Exception:
                continue

        # Converte sets para listas para serialização
        stats["active_users"] = list(stats["active_users"])

        return dict(stats)

    def get_real_time_alerts(self) -> List[Dict[str, Any]]:
        """Retorna alertas baseados na análise dos logs recentes"""
        alerts = []

        # Analisa logs da última hora
        summary = self.get_logs_summary(time_range_hours=1)

        # Alert 1: Muitos erros
        error_count = summary["by_level"].get("ERROR", 0) + summary["by_level"].get(
            "CRITICAL", 0
        )
        if error_count > 10:
            alerts.append(
                {
                    "level": "high",
                    "type": "errors",
                    "message": f"Alto número de erros na última hora: {error_count}",
                    "count": error_count,
                    "timestamp": datetime.now().isoformat(),
                }
            )

        # Alert 2: Requests lentos
        perf_stats = summary["performance_stats"]
        if perf_stats["slow_requests"] > 5:
            alerts.append(
                {
                    "level": "medium",
                    "type": "performance",
                    "message": f"Detectados {perf_stats['slow_requests']} requests lentos na última hora",
                    "count": perf_stats["slow_requests"],
                    "timestamp": datetime.now().isoformat(),
                }
            )

        # Alert 3: Múltiplas tentativas de login falhadas
        user_stats = self.get_user_activity_stats(time_range_hours=1)
        failed_attempts = sum(user_stats["failed_logins"].values())
        if failed_attempts > 5:
            alerts.append(
                {
                    "level": "high",
                    "type": "security",
                    "message": f"Múltiplas tentativas de login falhadas: {failed_attempts}",
                    "count": failed_attempts,
                    "timestamp": datetime.now().isoformat(),
                }
            )

        # Alert 4: Tempo de resposta médio alto
        if perf_stats["avg_response_time"] > 0.5:  # > 500ms
            alerts.append(
                {
                    "level": "medium",
                    "type": "performance",
                    "message": f"Tempo de resposta médio alto: {perf_stats['avg_response_time']:.3f}s",
                    "value": perf_stats["avg_response_time"],
                    "timestamp": datetime.now().isoformat(),
                }
            )

        return alerts
