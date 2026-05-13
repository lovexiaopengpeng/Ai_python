import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'rag_demo'))

from user_auth_service import app

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)