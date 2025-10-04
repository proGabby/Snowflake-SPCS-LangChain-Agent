"""
Simple agent implementation for testing purposes
Bypasses complex LangChain setup to get the application running
"""
from typing import Dict, List, Any, Optional
import structlog
from datetime import datetime
import asyncio

logger = structlog.get_logger()


class SimpleAgent:
    """Simple agent for testing the application"""
    
    def __init__(self):
        self.conversations: Dict[str, Dict[str, Any]] = {}
    
    def get_conversation(self, conversation_id: str) -> Dict[str, Any]:
        """Get or create conversation"""
        if conversation_id not in self.conversations:
            self.conversations[conversation_id] = {
                "messages": [],
                "metrics": {
                    "total_queries": 0,
                    "successful_queries": 0,
                    "failed_queries": 0,
                    "total_execution_time": 0.0,
                    "queries": []
                }
            }
        return self.conversations[conversation_id]
    
    def get_history(self) -> List[Dict[str, Any]]:
        """Get conversation history for compatibility"""
        return []
    
    async def process_query(
        self, 
        query: str, 
        conversation_id: str,
        user_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Process a user query through the simple workflow"""
        start_time = datetime.utcnow()
        
        # Get conversation
        conversation = self.get_conversation(conversation_id)
        
        # Add user query to history
        conversation["messages"].append({"type": "human", "content": query})
        
        try:
            # Check if this is a database-related query
            query_lower = query.lower()
            
            # Enhanced agent with vLLM integration
            try:
                from app.integrations.snowflake import snowflake_connector
                from app.integrations.vllm import vllm_client
                
                # Get available tables for context
                tables = snowflake_connector.get_available_tables()
                schema_info = {"tables": tables} if tables else {}
                
                # Generate SQL using vLLM
                sql_result = await vllm_client.generate_sql(query, schema_info)
                sql_query = sql_result.get("sql", "")
                
                logger.info("Generated SQL query", sql_query=sql_query, original_query=query)
                
                # Execute the SQL query
                if sql_query and sql_query.upper().strip().startswith(("SELECT", "SHOW")):
                    result = snowflake_connector.execute_query(sql_query)
                    
                    if result and result.get('data'):
                        # Analyze results using vLLM
                        analysis_result = await vllm_client.analyze_data(
                            data=result['data'],
                            question=query,
                            context={"sql_query": sql_query, "execution_time": result.get('execution_time', 0)}
                        )
                        response = analysis_result.get("text", "Analysis completed successfully.")
                    else:
                        response = "Query executed successfully but returned no data."
                else:
                    # Fallback for non-SELECT queries or when SQL generation fails
                    if 'table' in query_lower and 'available' in query_lower:
                        if tables:
                            response = f"Available tables in your database: {', '.join(tables)}"
                        else:
                            response = "No tables found in the database."
                    elif 'count' in query_lower and any(table in query_lower for table in ['customer', 'product', 'sale', 'order']):
                        # Get counts for specific tables
                        if 'customer' in query_lower:
                            result = snowflake_connector.execute_query("SELECT COUNT(*) FROM customers")
                            if result and result.get('data'):
                                response = f"There are {result['data'][0]['COUNT(*)']} customers in the database."
                        elif 'product' in query_lower:
                            result = snowflake_connector.execute_query("SELECT COUNT(*) FROM products")
                            if result and result.get('data'):
                                response = f"There are {result['data'][0]['COUNT(*)']} products in the database."
                        elif 'sale' in query_lower:
                            result = snowflake_connector.execute_query("SELECT COUNT(*) FROM sales")
                            if result and result.get('data'):
                                response = f"There are {result['data'][0]['COUNT(*)']} sales transactions in the database."
                        else:
                            response = f"I can help you analyze your data. Available tables: {', '.join(tables) if tables else 'customers, products, sales, orders'}."
                    else:
                        # Use vLLM for general responses
                        general_result = await vllm_client.generate_response(
                            f"Answer this question about data analysis: {query}",
                            context={"available_tables": tables}
                        )
                        response = general_result.get("text", f"I received your query: '{query}'. I can help you analyze your data. Available tables: {', '.join(tables) if tables else 'customers, products, sales, orders'}.")
                        
            except Exception as e:
                logger.error("Error in enhanced agent processing", error=str(e))
                # Fallback to simple responses
                try:
                    from app.integrations.snowflake import snowflake_connector
                    
                    if 'table' in query_lower and 'available' in query_lower:
                        tables = snowflake_connector.get_available_tables()
                        response = f"Available tables in your database: {', '.join(tables)}" if tables else "No tables found in the database."
                    else:
                        response = f"I received your query: '{query}'. There was an issue with the advanced processing, but I can help you with basic queries. Available tables: customers, products, sales, orders."
                except Exception as fallback_error:
                    response = f"I received your query: '{query}'. There was an issue connecting to the services: {str(e)}"
            
            # Add AI response to history
            conversation["messages"].append({"type": "ai", "content": response})
            
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            
            # Update metrics
            query_info = {
                "query": query,
                "response": response,
                "success": True,
                "execution_time": execution_time,
                "timestamp": datetime.utcnow().isoformat()
            }
            conversation["metrics"]["total_queries"] += 1
            conversation["metrics"]["successful_queries"] += 1
            conversation["metrics"]["total_execution_time"] += execution_time
            conversation["metrics"]["queries"].append(query_info)
            
            logger.info(
                "Query processed successfully",
                conversation_id=conversation_id,
                query_length=len(query),
                response_length=len(response),
                execution_time=execution_time
            )
            
            return {
                "response": response,
                "conversation_id": conversation_id,
                "execution_time": execution_time,
                "success": True,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            
            error_response = f"I encountered an error while processing your request: {str(e)}"
            conversation["messages"].append({"type": "ai", "content": error_response})
            
            # Update metrics
            query_info = {
                "query": query,
                "response": error_response,
                "success": False,
                "execution_time": execution_time,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
            conversation["metrics"]["total_queries"] += 1
            conversation["metrics"]["failed_queries"] += 1
            conversation["metrics"]["total_execution_time"] += execution_time
            conversation["metrics"]["queries"].append(query_info)
            
            logger.error(
                "Query processing failed",
                conversation_id=conversation_id,
                error=str(e),
                execution_time=execution_time
            )
            
            return {
                "response": error_response,
                "conversation_id": conversation_id,
                "execution_time": execution_time,
                "success": False,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    def get_conversation_metrics(self, conversation_id: str) -> Dict[str, Any]:
        """Get metrics for a specific conversation"""
        if conversation_id not in self.conversations:
            return {"error": "Conversation not found"}
        
        conversation = self.conversations[conversation_id]
        return conversation["metrics"]
    
    def clear_conversation(self, conversation_id: str) -> bool:
        """Clear a conversation"""
        if conversation_id in self.conversations:
            del self.conversations[conversation_id]
            return True
        return False


# Global simple agent instance
simple_agent = SimpleAgent()
