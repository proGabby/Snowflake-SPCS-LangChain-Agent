"""
Snowflake integration with SQL execution limits and data access boundaries
Handles secure query execution within Snowflake SPCS environment
"""
import snowflake.connector
from snowflake.connector import DictCursor
from typing import Dict, List, Any, Optional, Tuple
import structlog
from datetime import datetime
import re
import time

from app.config.settings import config

logger = structlog.get_logger()


class SnowflakeSecurityValidator:
    """Validates SQL queries for security and execution limits"""
    
    def __init__(self):
        self.blocked_operations = config.snowflake.get_blocked_operations_list()
        self.allowed_tables = config.snowflake.get_allowed_tables_list()
        self.max_rows = config.snowflake.max_query_rows
        self.max_timeout = config.snowflake.max_query_timeout
    
    def validate_query(self, query: str) -> Tuple[bool, str]:
        """Validate SQL query for security and compliance"""
        query_upper = query.upper().strip()
        
        # Check for blocked operations
        for operation in self.blocked_operations:
            if operation.upper() in query_upper:
                return False, f"Operation '{operation}' is not allowed"
        
        # Check table access if restrictions are set
        if self.allowed_tables:
            table_pattern = r'FROM\s+(\w+\.\w+|\w+)'
            tables = re.findall(table_pattern, query_upper)
            for table in tables:
                table_clean = table.replace('"', '').replace("'", '')
                if table_clean.upper() not in [t.upper() for t in self.allowed_tables]:
                    return False, f"Access to table '{table_clean}' is not allowed"
        
        # Check for suspicious patterns
        suspicious_patterns = [
            r'DROP\s+TABLE',
            r'DELETE\s+FROM',
            r'UPDATE\s+\w+\s+SET',
            r'INSERT\s+INTO',
            r'CREATE\s+TABLE',
            r'ALTER\s+TABLE',
            r'TRUNCATE',
            r';\s*--',
            r'/\*.*\*/'
        ]
        
        for pattern in suspicious_patterns:
            if re.search(pattern, query_upper, re.IGNORECASE):
                return False, f"Query contains suspicious pattern: {pattern}"
        
        return True, "Query is valid"
    
    def add_safety_limits(self, query: str) -> str:
        """Add safety limits to SELECT queries"""
        query_upper = query.upper().strip()
        
        # Skip safety limits for system queries and aggregation queries
        skip_conditions = [
            'COUNT(' in query_upper,
            'SUM(' in query_upper, 
            'AVG(' in query_upper,
            'MIN(' in query_upper,
            'MAX(' in query_upper,
            'INFORMATION_SCHEMA' in query_upper,  # Skip schema queries
            'SHOW ' in query_upper,  # Skip SHOW commands
            'DESCRIBE ' in query_upper,  # Skip DESCRIBE commands
            'LIMIT' in query_upper  # Already has LIMIT
        ]
        
        # Add LIMIT if not present and it's a SELECT query (but not system/aggregation queries)
        if (query_upper.startswith('SELECT') and not any(skip_conditions)):
            # Handle ORDER BY clause - use regex for more precise replacement
            import re
            if 'ORDER BY' in query_upper:
                # Use regex to find ORDER BY and insert LIMIT before it
                pattern = r'(\s+ORDER\s+BY\s+)'
                query = re.sub(pattern, f' LIMIT {self.max_rows} \\1', query, flags=re.IGNORECASE)
            else:
                # Add LIMIT at the end
                query = f"{query.rstrip(';')} LIMIT {self.max_rows}"
        
        return query


class SnowflakeConnector:
    """Secure Snowflake connector with built-in safety measures"""
    
    def __init__(self):
        self.config = config.snowflake
        self.validator = SnowflakeSecurityValidator()
        self._connection = None
    
    def get_connection(self):
        """Get or create Snowflake connection"""
        if self._connection is None or self._connection.is_closed():
            try:
                self._connection = snowflake.connector.connect(
                    account=self.config.account,
                    user=self.config.user,
                    password=self.config.password,
                    warehouse=self.config.warehouse,
                    database=self.config.database,
                    schema=self.config.schema,
                    role=self.config.role,
                    autocommit=True,
                    client_session_keep_alive=True
                )
                logger.info("Snowflake connection established")
            except Exception as e:
                logger.error("Failed to connect to Snowflake", error=str(e))
                raise
        
        return self._connection
    
    def execute_query(self, query: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """Execute a validated SQL query with safety limits"""
        start_time = time.time()
        
        # Validate query security
        is_valid, message = self.validator.validate_query(query)
        if not is_valid:
            logger.warning("Query validation failed", query=query, reason=message)
            raise ValueError(f"Query validation failed: {message}")
        
        # Add safety limits
        safe_query = self.validator.add_safety_limits(query)
        
        try:
            connection = self.get_connection()
            cursor = connection.cursor(DictCursor)
            
            # Set query timeout
            cursor.execute(f"ALTER SESSION SET STATEMENT_TIMEOUT_IN_SECONDS = {self.config.max_query_timeout}")
            
            # Execute the query
            if params:
                cursor.execute(safe_query, params)
            else:
                cursor.execute(safe_query)
            
            # Fetch results
            results = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description] if cursor.description else []
            
            execution_time = time.time() - start_time
            
            logger.info(
                "Query executed successfully",
                query=safe_query,
                row_count=len(results),
                execution_time=execution_time
            )
            
            return {
                "data": results,
                "columns": columns,
                "row_count": len(results),
                "execution_time": execution_time,
                "query": safe_query,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(
                "Query execution failed",
                query=safe_query,
                error=str(e),
                execution_time=execution_time
            )
            raise
    
    def get_table_schema(self, table_name: str) -> Dict[str, Any]:
        """Get schema information for a table"""
        query = """
        SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE, COLUMN_DEFAULT
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_NAME = %s AND TABLE_SCHEMA = %s
        ORDER BY ORDINAL_POSITION
        """
        
        try:
            result = self.execute_query(query, (table_name.upper(), self.config.schema))
            return {
                "table_name": table_name,
                "schema": result["data"],
                "column_count": len(result["data"])
            }
        except Exception as e:
            logger.error("Failed to get table schema", table_name=table_name, error=str(e))
            raise
    
    def get_available_tables(self) -> List[str]:
        """Get list of available tables in the schema"""
        try:
            connection = self.get_connection()
            cursor = connection.cursor()
            cursor.execute("SHOW TABLES")
            tables = [row[1] for row in cursor.fetchall()]  # Table name is in second column
            cursor.close()
            return tables
        except Exception as e:
            logger.error("Failed to get available tables", error=str(e))
            return []
    
    def close(self):
        """Close the Snowflake connection"""
        if self._connection and not self._connection.is_closed():
            self._connection.close()
            logger.info("Snowflake connection closed")


# Global Snowflake connector instance
snowflake_connector = SnowflakeConnector()
