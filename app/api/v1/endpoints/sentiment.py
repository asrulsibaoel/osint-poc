from fastapi import APIRouter
from app.schemas.data_ingestion import AnalyzeRequest
from app.schemas.analysis_result import AnalysisResponse
from app.services.nlp_service import analyze_posts, build_knowledge_graph

router = APIRouter(tags=["analysis"])


@router.post("/analyze", response_model=AnalysisResponse)
def analyze(request: AnalyzeRequest) -> AnalysisResponse:
    result = analyze_posts(request.posts)
    # Build/update the knowledge graph from latest analysis
    build_knowledge_graph(result)
    return result
