"""
Main FastAPI application for Snowflake SPCS LangChain Agent
Entry point for the containerized agentic QA workflow
"""
from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer
from contextlib import asynccontextmanager
import structlog
import uuid
from typing import Dict, List, Any, Optional

from app.config.settings import config
from app.auth.security import get_current_user, check_rate_limit, get_cors_config
from app.agent.langchain_agent import langchain_agent as snowflake_agent
from app.integrations.metrics import metrics_collector, grafana_integration
from app.models.schemas import (
    QueryRequest, QueryResponse, ConversationMetrics,
    HealthResponse, AgentStatus
)

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    # Startup
    logger.info("Starting Snowflake SPCS LangChain Agent")
    
    # Start metrics server
    metrics_collector.start_metrics_server()
    
    # Initialize Grafana dashboard (if enabled)
    if config.grafana.enabled:
        try:
            await grafana_integration.create_dashboard()
            logger.info("Grafana dashboard initialized")
        except Exception as e:
            logger.warning("Failed to initialize Grafana dashboard", error=str(e))
    else:
        logger.info("Grafana integration disabled")
    
    # Health checks (if vLLM enabled)
    if config.vllm.enabled:
        try:
            from app.integrations.vllm import vllm_client
            health = await vllm_client.health_check()
            if health["status"] == "healthy":
                logger.info("vLLM service is healthy")
            else:
                logger.warning("vLLM service is unhealthy", health=health)
        except Exception as e:
            logger.warning("vLLM health check failed", error=str(e))
    else:
        logger.info("vLLM integration disabled")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Snowflake SPCS LangChain Agent")
    
    # Close Snowflake connection
    try:
        from app.integrations.snowflake import snowflake_connector
        snowflake_connector.close()
    except Exception as e:
        logger.warning("Failed to close Snowflake connection", error=str(e))


# Create FastAPI application
app = FastAPI(
    title=config.app_name,
    version=config.version,
    description="Containerized LangChain agent for Snowflake SPCS with vLLM integration",
    lifespan=lifespan
)

# Add CORS middleware for ingress security
cors_config = get_cors_config()
app.add_middleware(
    CORSMiddleware,
    **cors_config
)

# Security
security = HTTPBearer()


@app.get("/", response_model=Dict[str, str])
async def root():
    """Root endpoint"""
    return {
        "message": "Snowflake SPCS LangChain Agent",
        "version": config.version,
        "status": "running"
    }


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    try:
        # Check vLLM service (if enabled)
        vllm_status = "disabled"
        if config.vllm.enabled:
            from app.integrations.vllm import vllm_client
            vllm_health = await vllm_client.health_check()
            vllm_status = vllm_health["status"]
        
        # Check Snowflake connection
        from app.integrations.snowflake import snowflake_connector
        snowflake_connector.get_connection()  # This will raise if connection fails
        
        # Check agent status
        active_conversations = len(snowflake_agent.conversations)
        metrics_collector.update_active_conversations(active_conversations)
        
        return HealthResponse(
            status="healthy",
            vllm_service=vllm_status,
            snowflake_connection="connected",
            active_conversations=active_conversations,
            uptime="running"
        )
        
    except Exception as e:
        logger.error("Health check failed", error=str(e))
        raise HTTPException(status_code=503, detail=f"Service unhealthy: {str(e)}")


@app.get("/status", response_model=AgentStatus)
async def get_agent_status(current_user: dict = Depends(get_current_user)):
    """Get agent status and configuration"""
    return AgentStatus(
        agent_type="Real LangChain Snowflake Agent with Tools",
        model=config.vllm.model_name,
        max_conversation_history=config.max_conversation_history,
        allowed_tables=config.snowflake.get_allowed_tables_list(),
        blocked_operations=config.snowflake.get_blocked_operations_list(),
        max_query_rows=config.snowflake.max_query_rows
    )


@app.post("/query", response_model=QueryResponse)
async def process_query(
    request: QueryRequest,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
    rate_limit_check: bool = Depends(check_rate_limit)
):
    """Process a natural language query through the agentic workflow"""
    try:
        # Generate conversation ID if not provided
        conversation_id = request.conversation_id or str(uuid.uuid4())
        
        logger.info(
            "Processing query",
            conversation_id=conversation_id,
            user=current_user["username"],
            query_length=len(request.query)
        )
        
        # Process the query through the agent
        result = await snowflake_agent.process_query(
            query=request.query,
            conversation_id=conversation_id,
            user_context=request.context
        )
        
        # Record metrics
        metrics_collector.record_query(
            status="success" if result["success"] else "error",
            conversation_id=conversation_id,
            duration=result["execution_time"],
            query_type="user_query"
        )
        
        # Update conversation metrics
        conversation = snowflake_agent.get_conversation(conversation_id)
        metrics_collector.update_conversation_length(
            conversation_id=conversation_id,
            length=len(conversation.get("messages", []))
        )
        
        # Background task to update Grafana dashboard
        background_tasks.add_task(
            update_grafana_metrics,
            conversation_id,
            result
        )
        
        return QueryResponse(
            response=result["response"],
            conversation_id=conversation_id,
            execution_time=result["execution_time"],
            success=result["success"],
            timestamp=result["timestamp"]
        )
        
    except Exception as e:
        logger.error("Query processing failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Query processing failed: {str(e)}")


@app.get("/conversations/{conversation_id}/metrics", response_model=ConversationMetrics)
async def get_conversation_metrics(
    conversation_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get metrics for a specific conversation"""
    try:
        metrics = snowflake_agent.get_conversation_metrics(conversation_id)
        
        if "error" in metrics:
            raise HTTPException(status_code=404, detail=metrics["error"])
        
        return ConversationMetrics(**metrics)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get conversation metrics", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/conversations/{conversation_id}")
async def clear_conversation(
    conversation_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Clear a conversation"""
    try:
        success = snowflake_agent.clear_conversation(conversation_id)
        
        if success:
            return {"message": f"Conversation {conversation_id} cleared successfully"}
        else:
            raise HTTPException(status_code=404, detail="Conversation not found")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to clear conversation", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/tables")
async def get_available_tables(current_user: dict = Depends(get_current_user)):
    """Get list of available tables"""
    try:
        from app.integrations.snowflake import snowflake_connector
        tables = snowflake_connector.get_available_tables()
        
        return {
            "tables": tables,
            "count": len(tables),
            "schema": config.snowflake.schema
        }
        
    except Exception as e:
        logger.error("Failed to get available tables", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/tables/{table_name}/schema")
async def get_table_schema(
    table_name: str,
    current_user: dict = Depends(get_current_user)
):
    """Get schema for a specific table"""
    try:
        from app.integrations.snowflake import snowflake_connector
        schema_info = snowflake_connector.get_table_schema(table_name)
        
        return schema_info
        
    except Exception as e:
        logger.error("Failed to get table schema", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


async def update_grafana_metrics(conversation_id: str, query_result: Dict[str, Any]):
    """Background task to update Grafana metrics"""
    try:
        # Update dashboard with latest metrics
        await grafana_integration.update_dashboard(
            config.grafana.dashboard_id,
            {"time": {"from": "now-1h", "to": "now"}}
        )
        
    except Exception as e:
        logger.warning("Failed to update Grafana metrics", error=str(e))


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=config.debug,
        log_level=config.log_level.lower()
    )
