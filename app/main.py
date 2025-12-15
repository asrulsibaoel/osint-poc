from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.api.v1.endpoints.sentiment import router as sentiment_router
from app.api.v1.endpoints.graph import router as graph_router

app = FastAPI(title=settings.app_name)

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
