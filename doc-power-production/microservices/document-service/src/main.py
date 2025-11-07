import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get service name from environment variable, default to "Service"
SERVICE_NAME = os.getenv("SERVICE_NAME", "Service")

# Create FastAPI app
app = FastAPI(
    title=f"{SERVICE_NAME}",
    version="1.0.0",
    description=f"{SERVICE_NAME} API"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health():
    return {"status": "healthy", "service": SERVICE_NAME}

@app.get("/ready")
async def ready():
    return {"status": "ready", "service": SERVICE_NAME}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
