"""
Authentication and security module for securing access to the workflow/API
Implements JWT tokens, rate limiting, and CORS for ingress security
"""
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from fastapi import HTTPException, status, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext
import time
from collections import defaultdict
import structlog

from app.config.settings import config

logger = structlog.get_logger()

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT token security
security = HTTPBearer()


class AuthManager:
    """Handles authentication and authorization for the API"""
    
    def __init__(self):
        self.secret_key = config.auth.secret_key
        self.algorithm = config.auth.algorithm
        self.access_token_expire_minutes = config.auth.access_token_expire_minutes
        
        # Rate limiting storage (in production, use Redis)
        self.rate_limits: Dict[str, list] = defaultdict(list)
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash"""
        return pwd_context.verify(plain_password, hashed_password)
    
    def get_password_hash(self, password: str) -> str:
        """Hash a password"""
        return pwd_context.hash(password)
    
    def create_access_token(self, data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
        """Create JWT access token"""
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=self.access_token_expire_minutes)
        
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt
    
    def verify_token(self, token: str) -> Dict[str, Any]:
        """Verify and decode JWT token"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
        except JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
    
    def check_rate_limit(self, client_ip: str) -> bool:
        """Check if client has exceeded rate limits"""
        current_time = time.time()
        window_start = current_time - config.auth.rate_limit_window
        
        # Clean old entries
        self.rate_limits[client_ip] = [
            timestamp for timestamp in self.rate_limits[client_ip]
            if timestamp > window_start
        ]
        
        # Check if limit exceeded
        if len(self.rate_limits[client_ip]) >= config.auth.rate_limit_requests:
            logger.warning("Rate limit exceeded", client_ip=client_ip)
            return False
        
        # Add current request
        self.rate_limits[client_ip].append(current_time)
        return True


# Global auth manager instance
auth_manager = AuthManager()


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict[str, Any]:
    """Dependency to get current authenticated user"""
    token = credentials.credentials
    payload = auth_manager.verify_token(token)
    
    username: str = payload.get("sub")
    if username is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return {"username": username, "payload": payload}


def check_rate_limit(request: Request) -> bool:
    """Dependency to check rate limits"""
    client_ip = request.client.host
    
    if not auth_manager.check_rate_limit(client_ip):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Please try again later.",
        )
    
    return True


# CORS configuration for ingress security
def get_cors_config() -> Dict[str, Any]:
    """Get CORS configuration for ingress security"""
    return {
        "allow_origins": config.auth.get_allowed_origins_list(),
        "allow_credentials": True,
        "allow_methods": config.auth.get_allowed_methods_list(),
        "allow_headers": ["*"],
        "expose_headers": ["X-Total-Count", "X-Query-Time"],
    }
