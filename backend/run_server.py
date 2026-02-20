"""
Run the FastAPI app from the backend directory so all routes (including /agents) load.
Usage: from backend folder run:  python run_server.py
"""
import sys
from pathlib import Path

# Ensure backend directory is the current working directory and on path
BACKEND_DIR = Path(__file__).resolve().parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))
import os
os.chdir(BACKEND_DIR)

if __name__ == "__main__":
    import uvicorn
    import os
    port = int(os.environ.get("PORT", "8000"))
    is_production = os.getenv("NODE_ENV") == "production" or os.getenv("ENV") == "production"
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=not is_production,
    )
