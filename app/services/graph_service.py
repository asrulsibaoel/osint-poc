"""
Neo4j Graph Service for persistent knowledge graph storage.
"""
from typing import List, Optional
from contextlib import contextmanager

from neo4j import GraphDatabase, Driver
from neo4j.exceptions import ServiceUnavailable

from app.core.config import settings
from app.schemas.analysis_result import (
    GraphResponse,
    GraphNode,
    GraphEdge,
    AnalysisResponse,
)


class Neo4jGraphService:
    """Service for managing knowledge graph in Neo4j."""
    
    _driver: Optional[Driver] = None
    
    @classmethod
    def get_driver(cls) -> Driver:
        """Get or create Neo4j driver instance."""
        if cls._driver is None:
            cls._driver = GraphDatabase.driver(
                settings.neo4j_uri,
                auth=(settings.neo4j_user, settings.neo4j_password),
            )
        return cls._driver
    
    @classmethod
    def close(cls) -> None:
        """Close the Neo4j driver connection."""
        if cls._driver is not None:
            cls._driver.close()
            cls._driver = None
    
    @classmethod
    @contextmanager
    def get_session(cls):
        """Context manager for Neo4j session."""
        driver = cls.get_driver()
        session = driver.session(database=settings.neo4j_database)
        try:
            yield session
        finally:
            session.close()
    
    @classmethod
    def verify_connectivity(cls) -> bool:
        """Verify Neo4j connection is working."""
        try:
            driver = cls.get_driver()
            driver.verify_connectivity()
            return True
        except ServiceUnavailable:
            return False
    
    @classmethod
    def init_constraints(cls) -> None:
        """Initialize Neo4j constraints and indexes for better performance."""
        constraints = [
            "CREATE CONSTRAINT post_id IF NOT EXISTS FOR (p:Post) REQUIRE p.id IS UNIQUE",
            "CREATE CONSTRAINT user_id IF NOT EXISTS FOR (u:User) REQUIRE u.id IS UNIQUE",
            "CREATE CONSTRAINT platform_id IF NOT EXISTS FOR (pl:Platform) REQUIRE pl.id IS UNIQUE",
            "CREATE CONSTRAINT entity_id IF NOT EXISTS FOR (e:Entity) REQUIRE e.id IS UNIQUE",
        ]
        with cls.get_session() as session:
            for constraint in constraints:
                try:
                    session.run(constraint)
                except Exception:
                    # Constraint might already exist
                    pass
    
    @classmethod
    def clear_graph(cls) -> None:
        """Clear all nodes and relationships from the graph."""
        with cls.get_session() as session:
            session.run("MATCH (n) DETACH DELETE n")
    
    @classmethod
    def build_knowledge_graph(cls, analysis: AnalysisResponse, clear_existing: bool = True) -> None:
        """
        Build knowledge graph from analysis response.
        
        Args:
            analysis: The analysis response containing posts and entities
            clear_existing: Whether to clear existing graph data first
        """
        if clear_existing:
            cls.clear_graph()
        
        with cls.get_session() as session:
            for item in analysis.items:
                # Create Post node
                session.run(
                    """
                    MERGE (p:Post {id: $post_id})
                    SET p.text = $text, p.sentiment = $sentiment, p.score = $score
                    """,
                    post_id=f"post:{item.post_id}",
                    text=item.text,
                    sentiment=item.sentiment.label,
                    score=item.sentiment.score,
                )
                
                # Create User node and relationship
                session.run(
                    """
                    MERGE (u:User {id: $user_id})
                    SET u.name = $name
                    WITH u
                    MATCH (p:Post {id: $post_id})
                    MERGE (u)-[:POSTED]->(p)
                    """,
                    user_id=f"user:{item.author}",
                    name=item.author,
                    post_id=f"post:{item.post_id}",
                )
                
                # Create Platform node and relationship
                session.run(
                    """
                    MERGE (pl:Platform {id: $platform_id})
                    SET pl.name = $name
                    WITH pl
                    MATCH (p:Post {id: $post_id})
                    MERGE (p)-[:ON]->(pl)
                    """,
                    platform_id=f"platform:{item.platform}",
                    name=item.platform,
                    post_id=f"post:{item.post_id}",
                )
                
                # Create Entity nodes and relationships
                for ent in item.entities:
                    session.run(
                        """
                        MERGE (e:Entity {id: $entity_id})
                        SET e.text = $text, e.label = $label
                        WITH e
                        MATCH (p:Post {id: $post_id})
                        MERGE (p)-[:MENTIONS]->(e)
                        """,
                        entity_id=f"entity:{ent.label}:{ent.text}",
                        text=ent.text,
                        label=ent.label,
                        post_id=f"post:{item.post_id}",
                    )
    
    @classmethod
    def get_graph_response(cls) -> GraphResponse:
        """
        Retrieve the entire graph and return as GraphResponse.
        
        Returns:
            GraphResponse containing all nodes and edges
        """
        nodes: List[GraphNode] = []
        edges: List[GraphEdge] = []
        
        with cls.get_session() as session:
            # Get all nodes
            result = session.run(
                """
                MATCH (n)
                RETURN n.id AS id, 
                       COALESCE(n.name, n.text, n.id) AS label,
                       labels(n)[0] AS type
                """
            )
            for record in result:
                node_type = record["type"].lower() if record["type"] else "entity"
                nodes.append(GraphNode(
                    id=record["id"],
                    label=record["label"],
                    type=node_type,
                ))
            
            # Get all relationships
            result = session.run(
                """
                MATCH (a)-[r]->(b)
                RETURN a.id AS source, b.id AS target, type(r) AS label
                """
            )
            for record in result:
                edges.append(GraphEdge(
                    source=record["source"],
                    target=record["target"],
                    label=record["label"],
                ))
        
        return GraphResponse(nodes=nodes, edges=edges)
    
    @classmethod
    def get_node_by_id(cls, node_id: str) -> Optional[GraphNode]:
        """Get a specific node by its ID."""
        with cls.get_session() as session:
            result = session.run(
                """
                MATCH (n {id: $node_id})
                RETURN n.id AS id,
                       COALESCE(n.name, n.text, n.id) AS label,
                       labels(n)[0] AS type
                """,
                node_id=node_id,
            )
            record = result.single()
            if record:
                return GraphNode(
                    id=record["id"],
                    label=record["label"],
                    type=record["type"].lower(),
                )
        return None
    
    @classmethod
    def get_neighbors(cls, node_id: str) -> GraphResponse:
        """Get all neighbors of a node (nodes connected by one edge)."""
        nodes: List[GraphNode] = []
        edges: List[GraphEdge] = []
        
        with cls.get_session() as session:
            # Get the center node
            center = cls.get_node_by_id(node_id)
            if center:
                nodes.append(center)
            
            # Get neighbors and edges
            result = session.run(
                """
                MATCH (n {id: $node_id})-[r]-(m)
                RETURN m.id AS id,
                       COALESCE(m.name, m.text, m.id) AS label,
                       labels(m)[0] AS type,
                       n.id AS source,
                       type(r) AS rel_type,
                       startNode(r).id AS rel_start
                """,
                node_id=node_id,
            )
            for record in result:
                nodes.append(GraphNode(
                    id=record["id"],
                    label=record["label"],
                    type=record["type"].lower(),
                ))
                # Determine edge direction
                if record["rel_start"] == node_id:
                    edges.append(GraphEdge(
                        source=node_id,
                        target=record["id"],
                        label=record["rel_type"],
                    ))
                else:
                    edges.append(GraphEdge(
                        source=record["id"],
                        target=node_id,
                        label=record["rel_type"],
                    ))
        
        return GraphResponse(nodes=nodes, edges=edges)


# Singleton instance for convenience
graph_service = Neo4jGraphService()
