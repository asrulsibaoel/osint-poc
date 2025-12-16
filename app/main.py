from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.api.v1.endpoints.sentiment import router as sentiment_router
from app.api.v1.endpoints.graph import router as graph_router
from app.services.graph_service import graph_service


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for startup and shutdown events."""
    # Startup
    try:
        if graph_service.verify_connectivity():
            graph_service.init_constraints()
            print("✅ Neo4j connection established and constraints initialized")
        else:
            print("⚠️ Neo4j connection failed - graph features will not work")
    except Exception as e:
        print(f"⚠️ Neo4j initialization error: {e}")
    
    yield
    
    # Shutdown
    graph_service.close()
    print("✅ Neo4j connection closed")


app = FastAPI(title=settings.app_name, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(sentiment_router, prefix="/api/v1")
app.include_router(graph_router, prefix="/api/v1")


@app.get("/health")
def health():
    return {"status": "ok"}
