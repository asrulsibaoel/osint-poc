from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from app.schemas.analysis_result import AnalysisResponse
from app.services.data_fetcher import TwitterFetcher
from app.services.nlp_service import analyze_posts, build_knowledge_graph

router = APIRouter(tags=["twitter"])


class TwitterFetchRequest(BaseModel):
    username: str
    limit: int = 10


class TwitterProfileResponse(BaseModel):
    user_id: str
    username: Optional[str]
    name: Optional[str]
    location: Optional[str]


@router.post("/twitter/fetch", response_model=AnalysisResponse)
def fetch_and_analyze_twitter(request: TwitterFetchRequest) -> AnalysisResponse:
    """
    Fetch tweets from a Twitter user and analyze them.
    """
    fetcher = TwitterFetcher()
    
    # Fetch posts
    posts = fetcher.fetch_posts(request.username, limit=request.limit)
    
    if not posts:
        raise HTTPException(
            status_code=404,
            detail=f"Could not fetch tweets for @{request.username}. Check if the username is correct or if you're rate limited."
        )
    
    # Analyze the posts
    result = analyze_posts(posts)
    
    # Build knowledge graph
    build_knowledge_graph(result, clear_existing=False)
    
    return result


@router.get("/twitter/profile/{username}", response_model=TwitterProfileResponse)
def get_twitter_profile(username: str) -> TwitterProfileResponse:
    """
    Get Twitter user profile information.
    """
    fetcher = TwitterFetcher()
    profile = fetcher.fetch_user_profile(username)
    
    if not profile:
        raise HTTPException(
            status_code=404,
            detail=f"Could not fetch profile for @{username}"
        )
    
    return TwitterProfileResponse(
        user_id=profile.user_id,
        username=profile.username,
        name=profile.name,
        location=profile.location
    )
