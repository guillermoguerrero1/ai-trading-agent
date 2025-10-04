#!/usr/bin/env python3
"""
JWT Token Creation Utility for AI Trading Agent

This script creates JWT tokens for authentication with the AI Trading Agent API.
"""

import jwt
import argparse
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.models.base import Settings

def create_jwt_token(
    username: str,
    user_id: str = None,
    roles: list = None,
    secret: str = None,
    algorithm: str = "HS256",
    audience: str = "ai-trading-agent",
    issuer: str = "ai-trading-agent",
    expires_minutes: int = 30
) -> str:
    """
    Create a JWT token for authentication.
    
    Args:
        username: Username for the token
        user_id: User ID (defaults to username)
        roles: List of user roles (defaults to ["trader"])
        secret: JWT secret (defaults to settings.JWT_SECRET)
        algorithm: JWT algorithm (defaults to HS256)
        audience: Token audience (defaults to ai-trading-agent)
        issuer: Token issuer (defaults to ai-trading-agent)
        expires_minutes: Token expiration in minutes (defaults to 30)
        
    Returns:
        JWT token string
    """
    if user_id is None:
        user_id = username
    
    if roles is None:
        roles = ["trader"]
    
    if secret is None:
        settings = Settings()
        secret = settings.JWT_SECRET
    
    # Create token payload
    now = datetime.utcnow()
    payload = {
        "sub": user_id,  # Subject (user ID)
        "username": username,
        "roles": roles,
        "iat": now,  # Issued at
        "exp": now + timedelta(minutes=expires_minutes),  # Expiration
        "nbf": now,  # Not before
        "aud": audience,  # Audience
        "iss": issuer,  # Issuer
    }
    
    # Create token
    token = jwt.encode(payload, secret, algorithm=algorithm)
    
    return token

def main():
    """Main function for command-line usage."""
    parser = argparse.ArgumentParser(description="Create JWT token for AI Trading Agent")
    parser.add_argument("username", help="Username for the token")
    parser.add_argument("--user-id", help="User ID (defaults to username)")
    parser.add_argument("--roles", nargs="+", default=["trader"], help="User roles (default: trader)")
    parser.add_argument("--secret", help="JWT secret (defaults to settings)")
    parser.add_argument("--expires", type=int, default=30, help="Expiration in minutes (default: 30)")
    parser.add_argument("--algorithm", default="HS256", help="JWT algorithm (default: HS256)")
    parser.add_argument("--audience", default="ai-trading-agent", help="Token audience")
    parser.add_argument("--issuer", default="ai-trading-agent", help="Token issuer")
    parser.add_argument("--output", help="Output file (default: stdout)")
    
    args = parser.parse_args()
    
    try:
        # Create token
        token = create_jwt_token(
            username=args.username,
            user_id=args.user_id,
            roles=args.roles,
            secret=args.secret,
            algorithm=args.algorithm,
            audience=args.audience,
            issuer=args.issuer,
            expires_minutes=args.expires
        )
        
        # Output token
        if args.output:
            with open(args.output, "w") as f:
                f.write(token)
            print(f"Token written to {args.output}")
        else:
            print(token)
            
    except Exception as e:
        print(f"Error creating token: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
