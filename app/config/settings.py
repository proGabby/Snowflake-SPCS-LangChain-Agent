"""
Configuration management for the Snowflake SPCS LangChain Agent
Handles environment variables, secrets, and deployment settings
"""
from typing import Optional, List
from pydantic import Field
from pydantic_settings import BaseSettings
import os


class SnowflakeConfig(BaseSettings):
    """Snowflake connection and security configuration"""
    account: str = Field(..., alias="SNOWFLAKE_ACCOUNT")
    user: str = Field(..., alias="SNOWFLAKE_USER")
    password: str = Field(..., alias="SNOWFLAKE_PASSWORD")
    warehouse: str = Field(..., alias="SNOWFLAKE_WAREHOUSE")
    database: str = Field(..., alias="SNOWFLAKE_DATABASE")
    schema: str = Field(default="PUBLIC", alias="SNOWFLAKE_SCHEMA")
    role: str = Field(default="PUBLIC", alias="SNOWFLAKE_ROLE")
    
    # SQL execution limits and security boundaries
    max_query_rows: int = Field(default=10000, alias="SNOWFLAKE_MAX_QUERY_ROWS")
    max_query_timeout: int = Field(default=300, alias="SNOWFLAKE_MAX_TIMEOUT")  # 5 minutes
    allowed_tables: str = Field(default="", alias="SNOWFLAKE_ALLOWED_TABLES")
    blocked_operations: str = Field(
        default="DROP,DELETE,UPDATE,INSERT,CREATE,ALTER",
        alias="SNOWFLAKE_BLOCKED_OPERATIONS"
    )
    
    def get_allowed_tables_list(self) -> List[str]:
        """Convert comma-separated string to list"""
        if not self.allowed_tables:
            return []
        return [table.strip() for table in self.allowed_tables.split(",") if table.strip()]
    
    def get_blocked_operations_list(self) -> List[str]:
        """Convert comma-separated string to list"""
        if not self.blocked_operations:
            return ["DROP", "DELETE", "UPDATE", "INSERT", "CREATE", "ALTER"]
        return [op.strip() for op in self.blocked_operations.split(",") if op.strip()]
    
    model_config = {"env_file": ".env"}


class VLLMConfig(BaseSettings):
    """vLLM service configuration for SPCS"""
    base_url: str = Field(default="http://vllm-service:8000", alias="VLLM_BASE_URL")
    model_name: str = Field(default="meta-llama/Llama-2-7b-chat-hf", alias="VLLM_MODEL_NAME")
    max_tokens: int = Field(default=1000, alias="VLLM_MAX_TOKENS")
    temperature: float = Field(default=0.7, alias="VLLM_TEMPERATURE")
    timeout: int = Field(default=30, alias="VLLM_TIMEOUT")
    enabled: bool = Field(default=True, alias="VLLM_ENABLED")
    
    model_config = {"env_file": ".env"}


class AuthConfig(BaseSettings):
    """Authentication and ingress security configuration"""
    secret_key: str = Field(default="default-secret-key-for-testing", alias="SECRET_KEY")
    algorithm: str = Field(default="HS256", alias="AUTH_ALGORITHM")
    access_token_expire_minutes: int = Field(default=30, alias="ACCESS_TOKEN_EXPIRE_MINUTES")
    
    # API rate limiting
    rate_limit_requests: int = Field(default=100, alias="RATE_LIMIT_REQUESTS")
    rate_limit_window: int = Field(default=3600, alias="RATE_LIMIT_WINDOW")  # 1 hour
    
    # CORS settings for ingress
    allowed_origins: str = Field(default="*", alias="ALLOWED_ORIGINS")
    allowed_methods: str = Field(default="GET,POST", alias="ALLOWED_METHODS")
    
    def get_allowed_origins_list(self) -> List[str]:
        """Convert comma-separated string to list"""
        if not self.allowed_origins:
            return ["*"]
        return [origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()]
    
    def get_allowed_methods_list(self) -> List[str]:
        """Convert comma-separated string to list"""
        if not self.allowed_methods:
            return ["GET", "POST"]
        return [method.strip() for method in self.allowed_methods.split(",") if method.strip()]
    
    model_config = {"env_file": ".env"}


class GrafanaConfig(BaseSettings):
    """Grafana monitoring configuration"""
    base_url: str = Field(default="http://grafana:3000", alias="GRAFANA_BASE_URL")
    api_key: str = Field(default="default-api-key", alias="GRAFANA_API_KEY")
    dashboard_id: int = Field(default=1, alias="GRAFANA_DASHBOARD_ID")
    datasource_name: str = Field(default="prometheus", alias="GRAFANA_DATASOURCE")
    enabled: bool = Field(default=True, alias="GRAFANA_ENABLED")
    
    model_config = {"env_file": ".env"}


class AppConfig(BaseSettings):
    """Main application configuration"""
    app_name: str = "Snowflake SPCS LangChain Agent"
    version: str = "1.0.0"
    debug: bool = Field(default=False, alias="DEBUG")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    
    # Agent configuration
    max_conversation_history: int = Field(default=10, alias="MAX_CONVERSATION_HISTORY")
    agent_timeout: int = Field(default=60, alias="AGENT_TIMEOUT")
    
    # Monitoring
    metrics_port: int = Field(default=8001, alias="METRICS_PORT")
    health_check_interval: int = Field(default=30, alias="HEALTH_CHECK_INTERVAL")
    
    model_config = {"env_file": ".env"}


# Global configuration instances
config = AppConfig()
snowflake_config = SnowflakeConfig()
vllm_config = VLLMConfig()
auth_config = AuthConfig()
grafana_config = GrafanaConfig()

# Create a combined config object
class CombinedConfig:
    def __init__(self):
        self.app = config
        self.snowflake = snowflake_config
        self.vllm = vllm_config
        self.auth = auth_config
        self.grafana = grafana_config
        
        # Add app config attributes directly
        for attr in dir(config):
            if not attr.startswith('_'):
                setattr(self, attr, getattr(config, attr))

# Use the combined config
config = CombinedConfig()