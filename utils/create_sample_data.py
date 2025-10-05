#!/usr/bin/env python3
"""
Create sample data in Snowflake for testing the agent
"""
from dotenv import load_dotenv
import os
from snowflake.connector import connect

def create_sample_data():
    """Create sample tables and data in Snowflake"""
    load_dotenv()
    
    try:
        # Connect to Snowflake
        connection = connect(
            account=os.getenv('SNOWFLAKE_ACCOUNT'),
            user=os.getenv('SNOWFLAKE_USER'),
            password=os.getenv('SNOWFLAKE_PASSWORD'),
            warehouse=os.getenv('SNOWFLAKE_WAREHOUSE'),
            database=os.getenv('SNOWFLAKE_DATABASE'),
            schema=os.getenv('SNOWFLAKE_SCHEMA'),
            role=os.getenv('SNOWFLAKE_ROLE')
        )
        
        cursor = connection.cursor()
        
        print("Creating sample data in Snowflake...")
        
        # Create CUSTOMERS table
        print(" Creating CUSTOMERS table...")
        cursor.execute("""
            CREATE OR REPLACE TABLE customers (
                customer_id INT,
                customer_name VARCHAR(100),
                email VARCHAR(100),
                city VARCHAR(50),
                country VARCHAR(50),
                created_date DATE
            )
        """)
        
        # Insert sample customers
        customers_data = [
            (1, 'John Doe', 'john.doe@email.com', 'New York', 'USA', '2024-01-15'),
            (2, 'Jane Smith', 'jane.smith@email.com', 'Los Angeles', 'USA', '2024-01-16'),
            (3, 'Bob Johnson', 'bob.johnson@email.com', 'Chicago', 'USA', '2024-01-17'),
            (4, 'Alice Brown', 'alice.brown@email.com', 'Houston', 'USA', '2024-01-18'),
            (5, 'Charlie Wilson', 'charlie.wilson@email.com', 'Phoenix', 'USA', '2024-01-19'),
            (6, 'Diana Davis', 'diana.davis@email.com', 'Philadelphia', 'USA', '2024-01-20'),
            (7, 'Eve Miller', 'eve.miller@email.com', 'San Antonio', 'USA', '2024-01-21'),
            (8, 'Frank Garcia', 'frank.garcia@email.com', 'San Diego', 'USA', '2024-01-22'),
            (9, 'Grace Lee', 'grace.lee@email.com', 'Dallas', 'USA', '2024-01-23'),
            (10, 'Henry Taylor', 'henry.taylor@email.com', 'San Jose', 'USA', '2024-01-24')
        ]
        
        cursor.executemany(
            "INSERT INTO customers VALUES (%s, %s, %s, %s, %s, %s)",
            customers_data
        )
        
        # Create PRODUCTS table
        print(" Creating PRODUCTS table...")
        cursor.execute("""
            CREATE OR REPLACE TABLE products (
                product_id INT,
                product_name VARCHAR(100),
                category VARCHAR(50),
                price DECIMAL(10,2),
                stock_quantity INT,
                created_date DATE
            )
        """)
        
        # Insert sample products
        products_data = [
            (101, 'Laptop Pro 15"', 'Electronics', 1299.99, 50, '2024-01-01'),
            (102, 'Wireless Mouse', 'Electronics', 29.99, 200, '2024-01-02'),
            (103, 'Office Chair', 'Furniture', 299.99, 75, '2024-01-03'),
            (104, 'Coffee Maker', 'Appliances', 89.99, 100, '2024-01-04'),
            (105, 'Notebook Set', 'Stationery', 19.99, 300, '2024-01-05'),
            (106, 'Desk Lamp', 'Furniture', 49.99, 150, '2024-01-06'),
            (107, 'Bluetooth Headphones', 'Electronics', 199.99, 80, '2024-01-07'),
            (108, 'Water Bottle', 'Accessories', 15.99, 250, '2024-01-08'),
            (109, 'Monitor 27"', 'Electronics', 399.99, 60, '2024-01-09'),
            (110, 'Keyboard Mechanical', 'Electronics', 149.99, 90, '2024-01-10')
        ]
        
        cursor.executemany(
            "INSERT INTO products VALUES (%s, %s, %s, %s, %s, %s)",
            products_data
        )
        
        # Create SALES table
        print(" Creating SALES table...")
        cursor.execute("""
            CREATE OR REPLACE TABLE sales (
                sale_id INT,
                customer_id INT,
                product_id INT,
                quantity INT,
                unit_price DECIMAL(10,2),
                total_amount DECIMAL(10,2),
                sale_date DATE,
                salesperson VARCHAR(100)
            )
        """)
        
        # Insert sample sales
        sales_data = [
            (1001, 1, 101, 1, 1299.99, 1299.99, '2024-02-01', 'Alice Johnson'),
            (1002, 2, 102, 2, 29.99, 59.98, '2024-02-02', 'Bob Smith'),
            (1003, 3, 103, 1, 299.99, 299.99, '2024-02-03', 'Alice Johnson'),
            (1004, 4, 104, 1, 89.99, 89.99, '2024-02-04', 'Charlie Brown'),
            (1005, 5, 105, 3, 19.99, 59.97, '2024-02-05', 'Bob Smith'),
            (1006, 1, 106, 1, 49.99, 49.99, '2024-02-06', 'Alice Johnson'),
            (1007, 6, 107, 1, 199.99, 199.99, '2024-02-07', 'Charlie Brown'),
            (1008, 7, 108, 2, 15.99, 31.98, '2024-02-08', 'Bob Smith'),
            (1009, 2, 109, 1, 399.99, 399.99, '2024-02-09', 'Alice Johnson'),
            (1010, 8, 110, 1, 149.99, 149.99, '2024-02-10', 'Charlie Brown'),
            (1011, 3, 101, 1, 1299.99, 1299.99, '2024-02-11', 'Bob Smith'),
            (1012, 9, 102, 1, 29.99, 29.99, '2024-02-12', 'Alice Johnson'),
            (1013, 10, 103, 2, 299.99, 599.98, '2024-02-13', 'Charlie Brown'),
            (1014, 4, 104, 1, 89.99, 89.99, '2024-02-14', 'Bob Smith'),
            (1015, 5, 105, 5, 19.99, 99.95, '2024-02-15', 'Alice Johnson')
        ]
        
        cursor.executemany(
            "INSERT INTO sales VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
            sales_data
        )
        
        # Create ORDERS table (summary view)
        print(" Creating ORDERS table...")
        cursor.execute("""
            CREATE OR REPLACE TABLE orders AS
            SELECT 
                s.sale_id as order_id,
                s.customer_id,
                c.customer_name,
                c.email,
                c.city,
                s.product_id,
                p.product_name,
                p.category,
                s.quantity,
                s.unit_price,
                s.total_amount,
                s.sale_date as order_date,
                s.salesperson
            FROM sales s
            JOIN customers c ON s.customer_id = c.customer_id
            JOIN products p ON s.product_id = p.product_id
        """)
        
        # Commit the changes
        connection.commit()
        
        print("\n Sample data created successfully!")
        
        # Show table counts
        cursor.execute("SELECT COUNT(*) FROM customers")
        customer_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM products")
        product_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM sales")
        sales_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM orders")
        orders_count = cursor.fetchone()[0]
        
        print(f" Data Summary:")
        print(f"   - Customers: {customer_count}")
        print(f"   - Products: {product_count}")
        print(f"   - Sales: {sales_count}")
        print(f"   - Orders: {orders_count}")
        
        # Show available tables
        cursor.execute("SHOW TABLES")
        tables = cursor.fetchall()
        print(f"\n Available Tables:")
        for table in tables:
            print(f"   - {table[1]}")
        
        cursor.close()
        connection.close()
        
        print("\n Sample data setup complete! You can now test the agent with real data.")
        
    except Exception as e:
        print(f"Error creating sample data: {e}")

if __name__ == "__main__":
    create_sample_data()
