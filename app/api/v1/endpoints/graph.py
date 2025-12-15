from fastapi import APIRouter
from app.schemas.analysis_result import GraphResponse
from app.services.nlp_service import get_graph_response

router = APIRouter(tags=["graph"])


@router.get("/graph", response_model=GraphResponse)
def get_graph() -> GraphResponse:
    return get_graph_response()
