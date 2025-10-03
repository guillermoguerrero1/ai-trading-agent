#!/usr/bin/env python3
"""Start server with extended trading hours"""

import os
import uvicorn
from app.main import app

# Set environment variable for extended trading hours
os.environ['SESSION_WINDOWS'] = '["00:00-23:59"]'

if __name__ == "__main__":
    print("Starting AI Trading Agent with 24/7 trading enabled...")
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")
