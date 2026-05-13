import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'rag_demo'))

import uvicorn

if __name__ == "__main__":
    from user_auth_service import app
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)