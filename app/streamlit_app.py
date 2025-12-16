import streamlit as st
import requests
import pandas as pd
import matplotlib.pyplot as plt
import networkx as nx
import os

# Get API base URL from environment or use default
DEFAULT_API_BASE = os.getenv("API_BASE_URL", "http://localhost:8080")
API_BASE = st.sidebar.text_input("API base URL", DEFAULT_API_BASE)

st.title("Sentiment Analyzer UI")

st.header("Analyze Text Posts")
text_list = st.text_area("Enter one post per line",
                         "Great product launch in Jakarta! Congrats to the team.")
if st.button("Analyze"):
    posts = []
    for i, t in enumerate([x.strip() for x in text_list.split("\n") if x.strip()]):
        posts.append({
            "id": f"p{i+1}",
            "platform": "custom",
            "author": "anonymous",
            "text": t
        })
    try:
        resp = requests.post(f"{API_BASE}/api/v1/analyze",
                             json={"posts": posts}, timeout=30)
        if resp.ok:
            data = resp.json()
            items_df = pd.DataFrame([{
                "post_id": it["post_id"],
                "platform": it["platform"],
                "author": it["author"],
                "sentiment": it["sentiment"]["label"],
                "score": it["sentiment"]["score"],
                "text": it["text"]
            } for it in data["items"]])
            st.subheader("Post Analyses")
            st.dataframe(items_df)
            st.subheader("Stats")
            st.json(data.get("stats", {}))
        else:
            st.error(f"API error: {resp.status_code} - {resp.text}")
    except Exception as e:
        st.error(f"Request failed: {e}")

st.header("Knowledge Graph")
if st.button("Load Graph"):
    try:
        gresp = requests.get(f"{API_BASE}/api/v1/graph", timeout=30)
        if gresp.ok:
            graph = gresp.json()
            G = nx.Graph()
            for n in graph.get("nodes", []):
                G.add_node(n["id"], label=n["label"], type=n["type"])
            for e in graph.get("edges", []):
                G.add_edge(e["source"], e["target"], label=e["label"])
            pos = nx.spring_layout(G, seed=42)
            plt.figure(figsize=(10, 6))
            node_labels = {n: G.nodes[n].get("label", n) for n in G.nodes}
            nx.draw(G, pos, with_labels=False,
                    node_color="#6baed6", edge_color="#9ecae1")
            nx.draw_networkx_labels(G, pos, labels=node_labels, font_size=8)
            st.pyplot(plt)
        else:
            st.error(f"API error: {gresp.status_code} - {gresp.text}")
    except Exception as e:
        st.error(f"Request failed: {e}")
