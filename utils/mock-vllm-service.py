#!/usr/bin/env python3
"""
Lightweight mock vLLM service that simulates the vLLM API
This avoids downloading large models while providing realistic responses
"""
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import json
import time
import random
import uvicorn
from datetime import datetime

app = FastAPI(title="Mock vLLM Service", version="1.0.0")

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatCompletionRequest(BaseModel):
    model: str
    messages: List[ChatMessage]
    max_tokens: Optional[int] = 500
    temperature: Optional[float] = 0.7
    stream: Optional[bool] = False

class ChatCompletionResponse(BaseModel):
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: List[Dict[str, Any]]
    usage: Dict[str, int]

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "mock-vllm",
        "version": "1.0.0"
    }

@app.post("/v1/chat/completions")
async def chat_completions(request: ChatCompletionRequest):
    """Mock chat completions endpoint"""
    
    # Simulate processing time
    await asyncio.sleep(random.uniform(0.5, 1.5))
    
    # Get the last user message
    user_message = None
    for message in reversed(request.messages):
        if message.role == "user":
            user_message = message.content
            break
    
    if not user_message:
        raise HTTPException(status_code=400, detail="No user message found")
    
    # Generate response based on the query
    response_content = generate_intelligent_response(user_message, request.messages)
    
    # Create response
    response = ChatCompletionResponse(
        id=f"chatcmpl-{int(time.time())}",
        created=int(time.time()),
        model=request.model,
        choices=[
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": response_content
                },
                "finish_reason": "stop"
            }
        ],
        usage={
            "prompt_tokens": sum(len(msg.content.split()) for msg in request.messages),
            "completion_tokens": len(response_content.split()),
            "total_tokens": 0
        }
    )
    
    # Calculate total tokens
    response.usage["total_tokens"] = response.usage["prompt_tokens"] + response.usage["completion_tokens"]
    
    return response

def generate_intelligent_response(user_message: str, conversation: List[ChatMessage]) -> str:
    """Generate intelligent responses based on the user message"""
    message_lower = user_message.lower()
    
    # SQL Generation
    if any(keyword in message_lower for keyword in ["sql", "query", "select", "table", "database"]):
        return generate_sql_response(user_message)
    
    # Data Analysis
    elif any(keyword in message_lower for keyword in ["analyze", "analysis", "insights", "data", "results"]):
        return generate_analysis_response(user_message)
    
    # Table-related queries
    elif "table" in message_lower and "available" in message_lower:
        return "Based on your database schema, you have access to the following tables: CUSTOMERS, PRODUCTS, SALES, and ORDERS. Each table contains relevant business data for analysis."
    
    # Count queries
    elif "count" in message_lower:
        if "customer" in message_lower:
            return "There are 10 customers in your database, representing a diverse customer base across different geographic regions."
        elif "product" in message_lower:
            return "Your product catalog contains 10 different products across various categories including Electronics, Furniture, Appliances, and Accessories."
        elif "sale" in message_lower:
            return "There are 15 sales transactions recorded, showing active business operations with varying transaction amounts and dates."
        else:
            return "I can help you count records in any of your tables. Please specify which table you'd like to count (customers, products, sales, or orders)."
    
    # Customer analysis
    elif "customer" in message_lower:
        return "Your customer data includes 10 customers with information about their names, email addresses, cities, and countries. Most customers are located in major US cities like New York, Los Angeles, and Chicago."
    
    # Product analysis
    elif "product" in message_lower:
        return "Your product inventory includes 10 products with prices ranging from $15.99 to $1299.99. Categories include Electronics (Laptops, Mice, Headphones, Monitors, Keyboards), Furniture (Chairs, Lamps), Appliances (Coffee Maker), and Accessories (Water Bottles, Notebooks)."
    
    # Sales analysis
    elif "sale" in message_lower or "revenue" in message_lower:
        return "Your sales data shows 15 transactions with total revenue information. Sales are distributed across different customers and products, with electronics being the highest-value category. Recent sales activity indicates healthy business performance."
    
    # General business questions
    elif any(keyword in message_lower for keyword in ["business", "performance", "overview", "summary"]):
        return """Based on your data analysis:

**Business Overview:**
- **Customers**: 10 active customers across major US cities
- **Products**: 10 products across 4 categories (Electronics, Furniture, Appliances, Accessories)
- **Sales**: 15 transactions with diverse product mix
- **Revenue**: Strong performance with electronics leading in value

**Key Insights:**
- Electronics category drives highest transaction values
- Geographic distribution shows national reach
- Product diversity supports various customer needs
- Recent transaction activity indicates healthy business growth

**Recommendations:**
- Focus marketing on high-value electronics
- Expand product offerings in popular categories
- Analyze customer patterns for targeted campaigns"""
    
    # Default response
    else:
        return f"I understand you're asking about: '{user_message}'. I can help you analyze your business data including customers, products, and sales. What specific information would you like to explore?"

def generate_sql_response(user_message: str) -> str:
    """Generate SQL queries based on natural language"""
    message_lower = user_message.lower()
    
    # Complex analytical queries
    if "top" in message_lower and "customer" in message_lower and ("spending" in message_lower or "revenue" in message_lower):
        return "SELECT c.customer_name, SUM(s.total_amount) as total_spent FROM customers c JOIN sales s ON c.customer_id = s.customer_id GROUP BY c.customer_name ORDER BY total_spent DESC LIMIT 5"
    elif "monthly" in message_lower and ("trend" in message_lower or "sales" in message_lower):
        return "SELECT DATE_TRUNC('month', sale_date) as month, SUM(total_amount) as monthly_revenue FROM sales GROUP BY month ORDER BY month DESC LIMIT 6"
    elif "analytics" in message_lower or "insights" in message_lower or "performance" in message_lower:
        return "SELECT 'Customer Count' as metric, COUNT(*) as value FROM customers UNION ALL SELECT 'Total Revenue', SUM(total_amount) FROM sales UNION ALL SELECT 'Product Count', COUNT(*) FROM products UNION ALL SELECT 'Average Order Value', AVG(total_amount) FROM sales"
    elif "correlation" in message_lower and "price" in message_lower:
        return "SELECT p.price, COUNT(s.sale_id) as sales_count FROM products p JOIN sales s ON p.product_id = s.product_id GROUP BY p.price ORDER BY p.price"
    elif "lifetime value" in message_lower:
        return "SELECT c.customer_name, SUM(s.total_amount) as lifetime_value, COUNT(s.sale_id) as total_orders FROM customers c JOIN sales s ON c.customer_id = s.customer_id GROUP BY c.customer_name ORDER BY lifetime_value DESC"
    elif "seasonal" in message_lower or "pattern" in message_lower:
        return "SELECT EXTRACT(MONTH FROM sale_date) as month, SUM(total_amount) as revenue FROM sales GROUP BY month ORDER BY month"
    elif "churn" in message_lower or "inactive" in message_lower:
        return "SELECT c.customer_name FROM customers c WHERE c.customer_id NOT IN (SELECT DISTINCT customer_id FROM sales WHERE sale_date > CURRENT_DATE - INTERVAL '30 days')"
    
    # Simple queries
    elif "customer" in message_lower and "count" in message_lower:
        return "SELECT COUNT(*) FROM customers"
    elif "product" in message_lower and "count" in message_lower:
        return "SELECT COUNT(*) FROM products"
    elif "sale" in message_lower and "count" in message_lower:
        return "SELECT COUNT(*) FROM sales"
    elif "customer" in message_lower and "list" in message_lower:
        return "SELECT customer_id, customer_name, email, city, country FROM customers ORDER BY customer_name LIMIT 10"
    elif "product" in message_lower and "list" in message_lower:
        return "SELECT product_id, product_name, category, price FROM products ORDER BY price DESC LIMIT 10"
    elif "sale" in message_lower and ("recent" in message_lower or "latest" in message_lower):
        return "SELECT s.sale_id, c.customer_name, p.product_name, s.total_amount, s.sale_date FROM sales s JOIN customers c ON s.customer_id = c.customer_id JOIN products p ON s.product_id = s.product_id ORDER BY s.sale_date DESC LIMIT 10"
    elif "revenue" in message_lower or "total sales" in message_lower:
        return "SELECT SUM(total_amount) as total_revenue FROM sales"
    elif "top customer" in message_lower:
        return "SELECT c.customer_name, SUM(s.total_amount) as total_spent FROM customers c JOIN sales s ON c.customer_id = s.customer_id GROUP BY c.customer_name ORDER BY total_spent DESC LIMIT 5"
    elif "top product" in message_lower:
        return "SELECT p.product_name, COUNT(s.sale_id) as times_sold, SUM(s.total_amount) as total_revenue FROM products p JOIN sales s ON p.product_id = s.product_id GROUP BY p.product_name ORDER BY total_revenue DESC LIMIT 5"
    else:
        return "SELECT COUNT(*) FROM customers"

def generate_analysis_response(user_message: str) -> str:
    """Generate data analysis responses"""
    message_lower = user_message.lower()
    
    if "customer" in message_lower:
        return """**Customer Analysis:**
- **Total Customers**: 10
- **Geographic Distribution**: Primarily US-based with customers in major cities
- **Customer Segments**: Mix of individual and business customers
- **Key Markets**: New York, Los Angeles, Chicago, Houston, Phoenix

**Insights:**
- Strong national presence across major metropolitan areas
- Diverse customer base supports business stability
- Geographic distribution indicates good market penetration"""
    
    elif "product" in message_lower:
        return """**Product Analysis:**
- **Total Products**: 10 across 4 categories
- **Price Range**: $15.99 - $1299.99
- **Category Breakdown**: Electronics (5), Furniture (2), Appliances (1), Accessories (2)
- **Top Categories**: Electronics dominates with premium products

**Insights:**
- Electronics category offers highest value products
- Price diversity caters to different customer segments
- Product mix supports various business needs"""
    
    elif "sale" in message_lower or "revenue" in message_lower:
        return """**Sales Analysis:**
- **Total Transactions**: 15
- **Revenue Distribution**: Varied across different products and customers
- **Sales Performance**: Consistent activity across all product categories
- **Customer Engagement**: Multiple customers showing repeat business patterns

**Insights:**
- Healthy sales volume indicates strong customer demand
- Revenue diversity reduces dependency on single products
- Sales distribution shows balanced business performance"""
    
    else:
        return """**General Business Analysis:**
Your business shows strong performance across all key metrics:
- **Customer Base**: Growing with 10 active customers
- **Product Portfolio**: Diverse 10-product catalog
- **Sales Activity**: 15 transactions showing consistent performance
- **Market Position**: Strong presence in major US markets

**Recommendations:**
1. Continue focusing on electronics category growth
2. Expand customer base in underserved geographic areas
3. Consider adding more products in high-performing categories
4. Implement customer retention programs for repeat business"""

if __name__ == "__main__":
    import asyncio
    print("🚀 Starting Mock vLLM Service...")
    print("📡 Service will be available at: http://localhost:8001")
    print("🔗 Health check: http://localhost:8001/health")
    print("💬 Chat completions: http://localhost:8001/v1/chat/completions")
    
    uvicorn.run(app, host="0.0.0.0", port=8000)

