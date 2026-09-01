import os
import uvicorn
from src.bridges.webmcp_bridge import app

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8001))
    # Local Interface Hardening: bind to 127.0.0.1 locally, 0.0.0.0 in Cloud Run
    host = "0.0.0.0" if os.getenv("K_SERVICE") else "127.0.0.1"
    print(f"[Shure Bridge] Starting server on {host}:{port}")
    uvicorn.run(app, host=host, port=port)
