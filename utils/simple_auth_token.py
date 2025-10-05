#!/usr/bin/env python3
"""
Generate a simple JWT token for testing
"""
import jwt
import time
from datetime import datetime, timedelta, UTC
import os
from dotenv import load_dotenv

def generate_test_token():
    """Generate a test JWT token"""
    load_dotenv()
    
    # Get secret key from environment or use default
    secret_key = os.getenv('SECRET_KEY', 'default-secret-key-for-testing')
    algorithm = os.getenv('AUTH_ALGORITHM', 'HS256')
    
    # Create payload
    payload = {
        "sub": "test-user",
        "username": "testuser",
        "email": "test@example.com",
        "role": "admin",
        "exp": datetime.now(UTC) + timedelta(minutes=30),  # Token expires in 30 minutes
        "iat": datetime.now(UTC)
    }
    
    # Generate token
    token = jwt.encode(payload, secret_key, algorithm=algorithm)
    
    print("Authentication Token Generated")
    print("=" * 40)
    print(f"Token: {token}")
    print("\n Usage:")
    print("Add this header to your API requests:")
    print("-" * 40)
    print(f'Authorization: Bearer {token}')
    print("\n Test with curl:")
    print("-" * 40)
    print(f'curl -H "Authorization: Bearer {token}" \\')
    print('     -H "Content-Type: application/json" \\')
    print('     -X POST "http://localhost:8000/query" \\')
    print('     -d \'{"query": "Hello", "conversation_id": "test-123"}\'')
    print("-" * 40)
    print("\n Token expires in 30 minutes")
    
    return token

if __name__ == "__main__":
    generate_test_token()

