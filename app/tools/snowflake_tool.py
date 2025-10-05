"""
LangChain Snowflake Tools for SQL execution
Provides proper LangChain tool interface for Snowflake operations with Gemini compatibility
"""
from typing import Dict, List, Any, Optional
from langchain_core.tools import tool
import structlog
from datetime import datetime

from app.integrations.snowflake import snowflake_connector

logger = structlog.get_logger()


@tool
def get_table_names() -> str:
    """Returns a comma-separated list of all table names in the Snowflake database."""
    try:
        tables = snowflake_connector.get_available_tables()
        return ", ".join(tables)
    except Exception as e:
        return f"Error getting table names: {str(e)}"


@tool
def get_table_schema(table_name: str) -> str:
    """
    Returns the schema of a specific table in the Snowflake database.
    Input should be a table name (string).
    """
    try:
        schema_info = snowflake_connector.get_table_schema(table_name)
        if schema_info and schema_info.get('schema'):
            response = f"Schema for table '{table_name}':\n"
            for column in schema_info['schema']:
                response += f"- {column['COLUMN_NAME']}: {column['DATA_TYPE']}"
                if column.get('IS_NULLABLE') == 'NO':
                    response += " (NOT NULL)"
                response += "\n"
            return response
        else:
            return f"Table '{table_name}' not found or no schema information available."
    except Exception as e:
        return f"Error getting schema for table {table_name}: {str(e)}"


@tool
def execute_snowflake_query(query: str) -> str:
    """
    Executes a SQL query against the Snowflake database and returns the results.
    Input should be a valid SQL SELECT query.
    """
    try:
        result = snowflake_connector.execute_query(query)
        if result and result.get('data'):
            data = result['data']
            row_count = len(data)
            
            if row_count == 1 and len(data[0]) == 1:
                value = list(data[0].values())[0]
                return f"Query result: {value}"
            elif row_count <= 10:
                # Format as a simple table
                response = f"Query returned {row_count} rows:\n\n"
                for i, row in enumerate(data, 1):
                    response += f"Row {i}:\n"
                    for key, value in row.items():
                        response += f"  {key}: {value}\n"
                    response += "\n"
                return response
            else:
                # Format sample data as a table
                response = f"Query returned {row_count} rows. Sample data:\n\n"
                for i, row in enumerate(data[:5], 1):
                    response += f"Row {i}:\n"
                    for key, value in row.items():
                        response += f"  {key}: {value}\n"
                    response += "\n"
                response += f"... and {row_count - 5} more rows"
                return response
        else:
            return "Query executed successfully but returned no data."
    except Exception as e:
        return f"Error executing query: {str(e)}"


# Export tools for use in the agent
snowflake_tools = [get_table_names, get_table_schema, execute_snowflake_query]