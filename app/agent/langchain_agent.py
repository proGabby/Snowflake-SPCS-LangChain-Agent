"""
LangChain Agent for Snowflake SPCS with Gemini API
Simplified version that manually handles tool calls to avoid schema compatibility issues
"""
from typing import Dict, List, Any, Optional
import structlog
from datetime import datetime
import asyncio
import json
import re
import os

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.memory import ConversationBufferWindowMemory
from langchain.schema import HumanMessage, AIMessage

from app.tools.snowflake_tool import get_table_names, get_table_schema, execute_snowflake_query
from app.config.settings import config

logger = structlog.get_logger()


class LangChainAgent:
    """Simplified LangChain agent for Snowflake interaction with manual tool handling"""

    def __init__(self):
        self.conversations: Dict[str, Dict[str, Any]] = {}
        self.llm = None
        self.memory = None
        self._initialize_agent()

    def _initialize_agent(self):
        """Initialize the LangChain agent with Gemini"""
        try:
            # Initialize the LLM with Gemini
            self.llm = ChatGoogleGenerativeAI(
                model=config.vllm.model_name,
                google_api_key=os.getenv("GOOGLE_API_KEY"),  # Get API key from environment
                temperature=0.1,  # Low temperature for consistent SQL generation
                convert_system_message_to_human=True
            )
            
            # Create memory
            self.memory = ConversationBufferWindowMemory(
                k=config.app.max_conversation_history,
                memory_key="chat_history",
                return_messages=True,
                input_key="input"
            )
            
            logger.info("LangChain agent initialized successfully")

        except Exception as e:
            logger.error("Failed to initialize LangChain agent", error=str(e))
            raise

    async def process_query(
        self,
        query: str,
        conversation_id: str,
        user_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Process a user query through the LangChain agent workflow"""
        try:
            # Get conversation history
            chat_history = self.memory.chat_memory.messages
            
            # Create a system prompt that includes available tools
            system_prompt = """You are a helpful data analyst assistant with access to a Snowflake database.

Available tools:
1. get_table_names() - Returns list of available tables
2. get_table_schema(table_name) - Returns schema for a specific table
3. execute_snowflake_query(query) - Executes SQL query and returns results

Available tables: customers, products, sales, orders

When a user asks a question:
1. First, determine what information you need
2. Use the appropriate tools to gather data
3. Provide a clear, helpful response based on the data

Always use SELECT statements only. Be precise with your SQL queries.
If you need to count records, use COUNT(*). If you need aggregations, use appropriate functions.

To use a tool, respond with: TOOL_CALL: tool_name(arguments)
For example: TOOL_CALL: get_table_names() or TOOL_CALL: execute_snowflake_query("SELECT COUNT(*) FROM customers")

Provide clear, actionable insights based on the data you retrieve."""

            # Create the prompt
            messages = [("system", system_prompt)]
            
            # Add chat history
            for msg in chat_history:
                if isinstance(msg, HumanMessage):
                    messages.append(("human", msg.content))
                elif isinstance(msg, AIMessage):
                    messages.append(("assistant", msg.content))
            
            # Add current query
            messages.append(("human", query))
            
            # Get response from LLM
            response = await self.llm.ainvoke(messages)
            response_content = response.content
            
            # Check if the response contains tool calls
            if "TOOL_CALL:" in response_content:
                # Extract and execute tool calls using a more robust approach
                tool_call_pattern = r'TOOL_CALL:\s*(\w+)\((.*?)\)(?=\s*TOOL_CALL:|$)'
                tool_calls = re.findall(tool_call_pattern, response_content, re.DOTALL)
                
                for tool_name, args in tool_calls:
                    try:
                        if tool_name == "get_table_names":
                            result = get_table_names.invoke({})
                        elif tool_name == "get_table_schema":
                            # Extract table name from args
                            table_name = args.strip().strip('"\'')
                            result = get_table_schema.invoke({"table_name": table_name})
                        elif tool_name == "execute_snowflake_query":
                            # Extract query from args - handle quoted strings properly
                            sql_query = args.strip()
                            # Remove surrounding quotes if present
                            if (sql_query.startswith('"') and sql_query.endswith('"')) or \
                               (sql_query.startswith("'") and sql_query.endswith("'")):
                                sql_query = sql_query[1:-1]
                            result = execute_snowflake_query.invoke({"query": sql_query})
                        else:
                            result = f"Unknown tool: {tool_name}"
                        
                        # Add tool result to response with better formatting
                        if "Query result:" in result:
                            # Extract just the data part for cleaner display
                            data_part = result.split("Query result:")[1].strip()
                            response_content += f"\n\n{data_part}"
                        else:
                            response_content += f"\n\n{result}"
                        
                    except Exception as e:
                        response_content += f"\n\nTool Error: {str(e)}"
            
            # Update memory
            self.memory.chat_memory.add_user_message(query)
            self.memory.chat_memory.add_ai_message(response_content)
            
            logger.info(
                "LangChain agent processed query",
                conversation_id=conversation_id,
                query=query,
                response=response_content
            )

            return {
                "response": response_content,
                "conversation_id": conversation_id,
                "execution_time": 0.0,  # Agent executor handles timing internally
                "success": True,
                "timestamp": datetime.utcnow().isoformat()
            }

        except Exception as e:
            logger.error("LangChain agent query processing failed", error=str(e))
            return {
                "response": f"I encountered an error while processing your request: {str(e)}",
                "conversation_id": conversation_id,
                "execution_time": 0.0,
                "success": False,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }

    def get_conversation(self, conversation_id: str) -> Dict[str, Any]:
        """Get conversation data (simplified for LangChain)"""
        # Return basic conversation info for LangChain
        return {
            "conversation_id": conversation_id,
            "message_count": len(self.memory.chat_memory.messages),
            "last_activity": datetime.utcnow().isoformat()
        }

    def get_conversation_metrics(self, conversation_id: str) -> Dict[str, Any]:
        """Get metrics for a specific conversation (simplified for LangChain)"""
        # LangChain's memory doesn't expose detailed metrics like the simple agent
        return {"message": "Metrics not fully implemented for LangChain agent yet."}

    def clear_conversation(self, conversation_id: str) -> bool:
        """Clear a conversation (simplified for LangChain)"""
        # LangChain's memory is typically cleared per session or managed differently
        self.memory.clear()
        return True


# Global LangChain agent instance
langchain_agent = LangChainAgent()