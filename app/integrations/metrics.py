"""
Metrics collection and Grafana integration for monitoring the deployed workflow
Handles Prometheus metrics and Grafana dashboard updates
"""
from prometheus_client import Counter, Histogram, Gauge, Info, start_http_server
from typing import Dict, Any, Optional
import structlog
from datetime import datetime
import asyncio
import httpx

from app.config.settings import config

logger = structlog.get_logger()


class MetricsCollector:
    """Collects and exposes metrics for the Snowflake agent workflow"""
    
    def __init__(self):
        # Query metrics
        self.query_counter = Counter(
            'snowflake_agent_queries_total',
            'Total number of queries processed',
            ['status', 'conversation_id']
        )
        
        self.query_duration = Histogram(
            'snowflake_agent_query_duration_seconds',
            'Time spent processing queries',
            ['query_type']
        )
        
        # Snowflake metrics
        self.snowflake_queries = Counter(
            'snowflake_queries_total',
            'Total Snowflake queries executed',
            ['status', 'table']
        )
        
        self.snowflake_query_duration = Histogram(
            'snowflake_query_duration_seconds',
            'Snowflake query execution time',
            ['table']
        )
        
        # vLLM metrics
        self.vllm_requests = Counter(
            'vllm_requests_total',
            'Total vLLM requests',
            ['status', 'model']
        )
        
        self.vllm_tokens = Counter(
            'vllm_tokens_total',
            'Total tokens processed by vLLM',
            ['type', 'model']
        )
        
        self.vllm_request_duration = Histogram(
            'vllm_request_duration_seconds',
            'vLLM request duration',
            ['model']
        )
        
        # Agent metrics
        self.agent_tool_usage = Counter(
            'agent_tool_usage_total',
            'Agent tool usage count',
            ['tool_name', 'status']
        )
        
        self.conversation_length = Gauge(
            'agent_conversation_length',
            'Number of messages in conversation',
            ['conversation_id']
        )
        
        # System metrics
        self.active_conversations = Gauge(
            'agent_active_conversations',
            'Number of active conversations'
        )
        
        self.system_info = Info(
            'snowflake_agent_info',
            'Agent system information'
        )
        
        # Set system info
        self.system_info.info({
            'version': config.version,
            'model': config.vllm.model_name,
            'environment': 'spcs'
        })
    
    def record_query(self, status: str, conversation_id: str, duration: float, query_type: str = "general"):
        """Record query metrics"""
        self.query_counter.labels(status=status, conversation_id=conversation_id).inc()
        self.query_duration.labels(query_type=query_type).observe(duration)
    
    def record_snowflake_query(self, status: str, table: str, duration: float):
        """Record Snowflake query metrics"""
        self.snowflake_queries.labels(status=status, table=table).inc()
        self.snowflake_query_duration.labels(table=table).observe(duration)
    
    def record_vllm_request(self, status: str, model: str, duration: float, tokens: Dict[str, int]):
        """Record vLLM request metrics"""
        self.vllm_requests.labels(status=status, model=model).inc()
        self.vllm_request_duration.labels(model=model).observe(duration)
        
        # Record token usage
        for token_type, count in tokens.items():
            self.vllm_tokens.labels(type=token_type, model=model).inc(count)
    
    def record_tool_usage(self, tool_name: str, status: str):
        """Record agent tool usage"""
        self.agent_tool_usage.labels(tool_name=tool_name, status=status).inc()
    
    def update_conversation_length(self, conversation_id: str, length: int):
        """Update conversation length metric"""
        self.conversation_length.labels(conversation_id=conversation_id).set(length)
    
    def update_active_conversations(self, count: int):
        """Update active conversations count"""
        self.active_conversations.set(count)
    
    def start_metrics_server(self):
        """Start Prometheus metrics server"""
        try:
            start_http_server(config.metrics_port)
            logger.info("Metrics server started", port=config.metrics_port)
        except Exception as e:
            logger.error("Failed to start metrics server", error=str(e))


class GrafanaIntegration:
    """Integration with Grafana for dashboard management"""
    
    def __init__(self):
        self.base_url = config.grafana.base_url
        self.api_key = config.grafana.api_key
        self.dashboard_id = config.grafana.dashboard_id
        self.datasource_name = config.grafana.datasource_name
    
    async def create_dashboard(self) -> Dict[str, Any]:
        """Create Grafana dashboard for the Snowflake agent"""
        dashboard_config = {
            "dashboard": {
                "id": None,
                "title": "Snowflake SPCS LangChain Agent",
                "tags": ["snowflake", "langchain", "spcs"],
                "timezone": "browser",
                "panels": [
                    self._create_query_metrics_panel(),
                    self._create_snowflake_metrics_panel(),
                    self._create_vllm_metrics_panel(),
                    self._create_agent_metrics_panel(),
                    self._create_system_metrics_panel()
                ],
                "time": {
                    "from": "now-1h",
                    "to": "now"
                },
                "refresh": "30s"
            }
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/api/dashboards/db",
                    json=dashboard_config,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    }
                )
                response.raise_for_status()
                
                result = response.json()
                logger.info("Grafana dashboard created", dashboard_id=result.get("id"))
                return result
                
        except Exception as e:
            logger.error("Failed to create Grafana dashboard", error=str(e))
            raise
    
    def _create_query_metrics_panel(self) -> Dict[str, Any]:
        """Create panel for query metrics"""
        return {
            "id": 1,
            "title": "Query Metrics",
            "type": "stat",
            "gridPos": {"h": 8, "w": 6, "x": 0, "y": 0},
            "targets": [
                {
                    "expr": "sum(rate(snowflake_agent_queries_total[5m]))",
                    "legendFormat": "Queries/sec"
                }
            ],
            "fieldConfig": {
                "defaults": {
                    "color": {"mode": "palette-classic"},
                    "unit": "reqps"
                }
            }
        }
    
    def _create_snowflake_metrics_panel(self) -> Dict[str, Any]:
        """Create panel for Snowflake metrics"""
        return {
            "id": 2,
            "title": "Snowflake Query Performance",
            "type": "graph",
            "gridPos": {"h": 8, "w": 6, "x": 6, "y": 0},
            "targets": [
                {
                    "expr": "histogram_quantile(0.95, rate(snowflake_query_duration_seconds_bucket[5m]))",
                    "legendFormat": "95th percentile"
                },
                {
                    "expr": "histogram_quantile(0.50, rate(snowflake_query_duration_seconds_bucket[5m]))",
                    "legendFormat": "50th percentile"
                }
            ]
        }
    
    def _create_vllm_metrics_panel(self) -> Dict[str, Any]:
        """Create panel for vLLM metrics"""
        return {
            "id": 3,
            "title": "vLLM Performance",
            "type": "graph",
            "gridPos": {"h": 8, "w": 6, "x": 12, "y": 0},
            "targets": [
                {
                    "expr": "rate(vllm_requests_total[5m])",
                    "legendFormat": "{{status}} - {{model}}"
                }
            ]
        }
    
    def _create_agent_metrics_panel(self) -> Dict[str, Any]:
        """Create panel for agent metrics"""
        return {
            "id": 4,
            "title": "Agent Tool Usage",
            "type": "piechart",
            "gridPos": {"h": 8, "w": 6, "x": 18, "y": 0},
            "targets": [
                {
                    "expr": "sum by (tool_name) (agent_tool_usage_total)",
                    "legendFormat": "{{tool_name}}"
                }
            ]
        }
    
    def _create_system_metrics_panel(self) -> Dict[str, Any]:
        """Create panel for system metrics"""
        return {
            "id": 5,
            "title": "System Overview",
            "type": "stat",
            "gridPos": {"h": 4, "w": 24, "x": 0, "y": 8},
            "targets": [
                {
                    "expr": "agent_active_conversations",
                    "legendFormat": "Active Conversations"
                }
            ]
        }
    
    async def update_dashboard(self, dashboard_id: int, updates: Dict[str, Any]) -> bool:
        """Update existing Grafana dashboard"""
        try:
            # Get current dashboard
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/api/dashboards/id/{dashboard_id}",
                    headers={"Authorization": f"Bearer {self.api_key}"}
                )
                response.raise_for_status()
                
                dashboard = response.json()["dashboard"]
                
                # Apply updates
                dashboard.update(updates)
                
                # Save updated dashboard
                save_response = await client.post(
                    f"{self.base_url}/api/dashboards/db",
                    json={"dashboard": dashboard},
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    }
                )
                save_response.raise_for_status()
                
                logger.info("Grafana dashboard updated", dashboard_id=dashboard_id)
                return True
                
        except Exception as e:
            logger.error("Failed to update Grafana dashboard", error=str(e))
            return False


# Global instances
metrics_collector = MetricsCollector()
grafana_integration = GrafanaIntegration()

