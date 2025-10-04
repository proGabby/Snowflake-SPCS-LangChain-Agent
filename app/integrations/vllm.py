"""
vLLM integration for running LLMs inside Snowflake containers
Handles communication with vLLM service deployed in SPCS
"""
import httpx
import asyncio
from typing import Dict, List, Any, Optional, AsyncGenerator
import structlog
from datetime import datetime
import json

from app.config.settings import config

logger = structlog.get_logger()


class VLLMClient:
    """Client for communicating with vLLM service in SPCS"""
    
    def __init__(self):
        self.base_url = config.vllm.base_url
        self.model_name = config.vllm.model_name
        self.max_tokens = config.vllm.max_tokens
        self.temperature = config.vllm.temperature
        self.timeout = config.vllm.timeout
    
    async def generate_response(
        self, 
        prompt: str, 
        context: Optional[Dict[str, Any]] = None,
        stream: bool = False
    ) -> Dict[str, Any]:
        """Generate response using vLLM service"""
        start_time = datetime.utcnow()
        
        # Prepare the request payload for OpenAI chat completions API
        payload = {
            "model": self.model_name,
            "messages": [
                {
                    "role": "system",
                    "content": "You are a helpful data analyst assistant."
                },
                {
                    "role": "user", 
                    "content": prompt
                }
            ],
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "stream": stream
        }
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/v1/chat/completions",
                    json=payload,
                    headers={"Content-Type": "application/json"}
                )
                response.raise_for_status()
                
                result = response.json()
                execution_time = (datetime.utcnow() - start_time).total_seconds()
                
                # Extract response from OpenAI chat completions format
                response_text = result.get("choices", [{}])[0].get("message", {}).get("content", "")
                usage_info = result.get("usage", {})
                
                logger.info(
                    "vLLM response generated",
                    model=self.model_name,
                    prompt_length=len(prompt),
                    response_length=len(response_text),
                    execution_time=execution_time,
                    tokens_used=usage_info.get("total_tokens", 0)
                )
                
                return {
                    "text": response_text,
                    "usage": usage_info,
                    "execution_time": execution_time,
                    "model": self.model_name,
                    "timestamp": datetime.utcnow().isoformat()
                }
                
        except httpx.TimeoutException:
            logger.error("vLLM request timed out", timeout=self.timeout)
            raise Exception("vLLM service request timed out")
        except httpx.HTTPStatusError as e:
            logger.error("vLLM HTTP error", status_code=e.response.status_code, error=str(e))
            raise Exception(f"vLLM service error: {e.response.status_code}")
        except Exception as e:
            logger.error("vLLM request failed", error=str(e))
            raise
    
    async def generate_stream(
        self, 
        prompt: str, 
        context: Optional[Dict[str, Any]] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Generate streaming response from vLLM service"""
        payload = {
            "model": self.model_name,
            "messages": [
                {
                    "role": "system",
                    "content": "You are a helpful data analyst assistant."
                },
                {
                    "role": "user", 
                    "content": prompt
                }
            ],
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "stream": True
        }
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                async with client.stream(
                    "POST",
                    f"{self.base_url}/v1/chat/completions",
                    json=payload,
                    headers={"Content-Type": "application/json"}
                ) as response:
                    response.raise_for_status()
                    
                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            try:
                                data = json.loads(line[6:])
                                if data.get("text"):
                                    yield {
                                        "text": data["text"],
                                        "finished": data.get("finished", False),
                                        "timestamp": datetime.utcnow().isoformat()
                                    }
                            except json.JSONDecodeError:
                                continue
                                
        except Exception as e:
            logger.error("vLLM streaming failed", error=str(e))
            raise
    
    async def analyze_data(
        self, 
        data: List[Dict[str, Any]], 
        question: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Analyze structured data and provide insights"""
        
        # Format data for analysis
        data_summary = self._format_data_for_analysis(data)
        
        analysis_prompt = f"""
        You are a data analyst. Based on the following data and question, provide a comprehensive analysis.
        
        Question: {question}
        
        Data Summary:
        {data_summary}
        
        Please provide:
        1. Key insights from the data
        2. Trends or patterns observed
        3. Specific answers to the question
        4. Any limitations or caveats
        
        Context: {context or "No additional context provided"}
        
        Format your response in a clear, structured way.
        """
        
        return await self.generate_response(analysis_prompt, context)
    
    def _format_data_for_analysis(self, data: List[Dict[str, Any]]) -> str:
        """Format data for LLM analysis"""
        if not data:
            return "No data available"
        
        # Limit data size for analysis
        max_rows = min(50, len(data))
        sample_data = data[:max_rows]
        
        formatted = f"Total rows: {len(data)}\n"
        formatted += f"Sample data (first {max_rows} rows):\n"
        
        for i, row in enumerate(sample_data):
            formatted += f"Row {i+1}: {row}\n"
        
        if len(data) > max_rows:
            formatted += f"... and {len(data) - max_rows} more rows"
        
        return formatted
    
    async def generate_sql(
        self, 
        question: str, 
        schema_info: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Generate SQL query based on natural language question"""
        
        schema_text = ""
        if schema_info:
            schema_text = f"""
            Available tables and schemas:
            {json.dumps(schema_info, indent=2)}
            """
        
        sql_prompt = f"""
        You are a SQL expert. Generate a secure SELECT query to answer the following question.
        
        Question: {question}
        
        {schema_text}
        
        Requirements:
        1. Use only SELECT statements
        2. Include proper WHERE clauses for filtering
        3. Use appropriate JOINs if needed
        4. Include ORDER BY for sorting when relevant
        5. Add LIMIT clause to restrict results
        6. Use parameterized queries where possible
        
        Context: {context or "No additional context"}
        
        Return only the SQL query, no explanations.
        """
        
        result = await self.generate_response(sql_prompt, context)
        sql_query = result["text"].strip()
        
        # Clean up the SQL query
        sql_query = sql_query.replace("```sql", "").replace("```", "").strip()
        
        return {
            "sql": sql_query,
            "usage": result["usage"],
            "execution_time": result["execution_time"]
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """Check vLLM service health"""
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                response = await client.get(f"{self.base_url}/health")
                response.raise_for_status()
                
                return {
                    "status": "healthy",
                    "response_time": response.elapsed.total_seconds(),
                    "timestamp": datetime.utcnow().isoformat()
                }
        except Exception as e:
            logger.error("vLLM health check failed", error=str(e))
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }


# Global vLLM client instance
vllm_client = VLLMClient()
