from typing import List
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import re

from app.schemas.data_ingestion import Post
from app.schemas.analysis_result import (
    NEREntity,
    SentimentResult,
    PostAnalysis,
    AnalysisStats,
    AnalysisResponse,
    GraphResponse,
)
from app.services.graph_service import graph_service

# Sentiment analyzer
_vader = SentimentIntensityAnalyzer()

# Try spaCy for NER, else fallback to regex-based extraction
_spacy_nlp = None
try:
    import spacy  # type: ignore
    try:
        _spacy_nlp = spacy.load("en_core_web_sm")
    except Exception:
        _spacy_nlp = None
except Exception:
    _spacy_nlp = None

EMAIL_RE = re.compile(r"[\w\.-]+@[\w\.-]+", re.IGNORECASE)
PHONE_RE = re.compile(r"\+?\d[\d\-\s]{7,}\d")
URL_RE = re.compile(r"https?://\S+")


def _sentiment(text: str) -> SentimentResult:
    scores = _vader.polarity_scores(text)
    comp = scores["compound"]
    if comp >= 0.05:
        label = "positive"
    elif comp <= -0.05:
        label = "negative"
    else:
        label = "neutral"
    return SentimentResult(label=label, score=comp)


def _ner(text: str) -> List[NEREntity]:
    entities: List[NEREntity] = []
    if _spacy_nlp:
        doc = _spacy_nlp(text)
        for ent in doc.ents:
            entities.append(NEREntity(text=ent.text, label=ent.label_))
        return entities

    # Fallback: simple pattern-based entities
    for m in EMAIL_RE.findall(text):
        entities.append(NEREntity(text=m, label="EMAIL"))
    for m in PHONE_RE.findall(text):
        entities.append(NEREntity(text=m, label="PHONE"))
    for m in URL_RE.findall(text):
        entities.append(NEREntity(text=m, label="URL"))
    # Naive PERSON: consecutive capitalized words (very rough)
    for m in re.findall(r"(?:[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)", text):
        entities.append(NEREntity(text=m, label="PERSON"))
    return entities


def analyze_posts(posts: List[Post]) -> AnalysisResponse:
    items: List[PostAnalysis] = []
    pos = neu = neg = 0
    for p in posts:
        s = _sentiment(p.text)
        if s.label == "positive":
            pos += 1
        elif s.label == "negative":
            neg += 1
        else:
            neu += 1
        ents = _ner(p.text)
        items.append(
            PostAnalysis(
                post_id=p.id,
                platform=p.platform,
                author=p.author,
                sentiment=s,
                entities=ents,
                text=p.text,
            )
        )
    stats = AnalysisStats(total_posts=len(
        posts), positive=pos, neutral=neu, negative=neg)
    return AnalysisResponse(items=items, stats=stats)


def build_knowledge_graph(analysis: AnalysisResponse, clear_existing: bool = True) -> None:
    """
    Build knowledge graph from analysis response using Neo4j.
    
    Args:
        analysis: The analysis response containing posts and entities
        clear_existing: Whether to clear existing graph data first
    """
    graph_service.build_knowledge_graph(analysis, clear_existing=clear_existing)


def get_graph_response() -> GraphResponse:
    """
    Retrieve the entire graph from Neo4j.
    
    Returns:
        GraphResponse containing all nodes and edges
    """
    return graph_service.get_graph_response()
