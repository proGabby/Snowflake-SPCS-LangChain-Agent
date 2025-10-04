"""
Pydantic models for API request/response schemas
Defines data structures for the Snowflake agent workflow
"""
from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime


class QueryRequest(BaseModel):
    """Request model for natural language queries"""
    query: str = Field(..., description="Natural language query to process")
    conversation_id: Optional[str] = Field(None, description="Conversation ID for context")
    context: Optional[Dict[str, Any]] = Field(None, description="Additional context for the query")
    
    class Config:
        schema_extra = {
            "example": {
                "query": "What were the top 5 products by sales last quarter?",
                "conversation_id": "conv-123",
                "context": {"user_role": "analyst", "department": "sales"}
            }
        }


class QueryResponse(BaseModel):
    """Response model for query processing results"""
    response: str = Field(..., description="Agent's response to the query")
    conversation_id: str = Field(..., description="Conversation ID")
    execution_time: float = Field(..., description="Time taken to process the query")
    success: bool = Field(..., description="Whether the query was processed successfully")
    timestamp: str = Field(..., description="ISO timestamp of the response")
    
    class Config:
        schema_extra = {
            "example": {
                "response": "Based on the data analysis, the top 5 products by sales in Q4 were...",
                "conversation_id": "conv-123",
                "execution_time": 2.5,
                "success": True,
                "timestamp": "2024-01-15T10:30:00Z"
            }
        }


class ConversationMetrics(BaseModel):
    """Metrics for a conversation"""
    total_queries: int = Field(..., description="Total number of queries in the conversation")
    successful_queries: int = Field(..., description="Number of successful queries")
    failed_queries: int = Field(..., description="Number of failed queries")
    total_execution_time: float = Field(..., description="Total execution time for all queries")
    queries: List[Dict[str, Any]] = Field(..., description="Detailed query history")
    
    class Config:
        schema_extra = {
            "example": {
                "total_queries": 5,
                "successful_queries": 4,
                "failed_queries": 1,
                "total_execution_time": 12.5,
                "queries": [
                    {
                        "query": "Show me sales data",
                        "success": True,
                        "execution_time": 2.1,
                        "timestamp": "2024-01-15T10:30:00Z"
                    }
                ]
            }
        }


class HealthResponse(BaseModel):
    """Health check response model"""
    status: str = Field(..., description="Overall service status")
    vllm_service: str = Field(..., description="vLLM service status")
    snowflake_connection: str = Field(..., description="Snowflake connection status")
    active_conversations: int = Field(..., description="Number of active conversations")
    uptime: str = Field(..., description="Service uptime status")
    
    class Config:
        schema_extra = {
            "example": {
                "status": "healthy",
                "vllm_service": "healthy",
                "snowflake_connection": "connected",
                "active_conversations": 3,
                "uptime": "running"
            }
        }


class AgentStatus(BaseModel):
    """Agent status and configuration"""
    agent_type: str = Field(..., description="Type of agent")
    model: str = Field(..., description="LLM model being used")
    max_conversation_history: int = Field(..., description="Maximum conversation history length")
    allowed_tables: List[str] = Field(..., description="List of allowed tables")
    blocked_operations: List[str] = Field(..., description="List of blocked SQL operations")
    max_query_rows: int = Field(..., description="Maximum rows returned per query")
    
    class Config:
        schema_extra = {
            "example": {
                "agent_type": "LangChain Snowflake Agent",
                "model": "meta-llama/Llama-2-7b-chat-hf",
                "max_conversation_history": 10,
                "allowed_tables": ["sales", "customers", "products"],
                "blocked_operations": ["DROP", "DELETE", "UPDATE"],
                "max_query_rows": 10000
            }
        }


class TableSchema(BaseModel):
    """Table schema information"""
    table_name: str = Field(..., description="Name of the table")
    schema: List[Dict[str, Any]] = Field(..., description="Table schema information")
    column_count: int = Field(..., description="Number of columns in the table")
    
    class Config:
        schema_extra = {
            "example": {
                "table_name": "sales",
                "schema": [
                    {
                        "COLUMN_NAME": "id",
                        "DATA_TYPE": "NUMBER",
                        "IS_NULLABLE": "NO",
                        "COLUMN_DEFAULT": None
                    }
                ],
                "column_count": 5
            }
        }


class AvailableTables(BaseModel):
    """Available tables response"""
    tables: List[str] = Field(..., description="List of available table names")
    count: int = Field(..., description="Number of available tables")
    schema: str = Field(..., description="Snowflake schema name")
    
    class Config:
        schema_extra = {
            "example": {
                "tables": ["sales", "customers", "products"],
                "count": 3,
                "schema": "PUBLIC"
            }
        }


class ErrorResponse(BaseModel):
    """Error response model"""
    error: str = Field(..., description="Error message")
    detail: Optional[str] = Field(None, description="Detailed error information")
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    
    class Config:
        schema_extra = {
            "example": {
                "error": "Query execution failed",
                "detail": "Table 'invalid_table' does not exist",
                "timestamp": "2024-01-15T10:30:00Z"
            }
        }

