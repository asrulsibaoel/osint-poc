from pydantic import BaseModel
from typing import List


class NEREntity(BaseModel):
    text: str
    label: str


class SentimentResult(BaseModel):
    label: str  # positive, neutral, negative
    score: float


class PostAnalysis(BaseModel):
    post_id: str
    platform: str
    author: str
    sentiment: SentimentResult
    entities: List[NEREntity]
    text: str


class AnalysisStats(BaseModel):
    total_posts: int
    positive: int
    neutral: int
    negative: int


class AnalysisResponse(BaseModel):
    items: List[PostAnalysis]
    stats: AnalysisStats


class GraphNode(BaseModel):
    id: str
    label: str
    type: str  # user | post | entity | platform


class GraphEdge(BaseModel):
    source: str
    target: str
    label: str


class GraphResponse(BaseModel):
    nodes: List[GraphNode]
    edges: List[GraphEdge]
