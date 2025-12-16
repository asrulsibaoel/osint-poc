import streamlit as st
import requests
import pandas as pd
import matplotlib.pyplot as plt
import networkx as nx
import os
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# Page configuration
st.set_page_config(
    page_title="OSINT Sentiment Analyzer",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .sentiment-positive { color: #28a745; font-weight: bold; }
    .sentiment-negative { color: #dc3545; font-weight: bold; }
    .sentiment-neutral { color: #6c757d; font-weight: bold; }
    .metric-card {
        background-color: #f8f9fa;
        border-radius: 10px;
        padding: 20px;
        text-align: center;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 24px;
    }
</style>
""", unsafe_allow_html=True)

# Get API base URL from environment or use default
DEFAULT_API_BASE = os.getenv("API_BASE_URL", "http://localhost:8080")

# Sidebar configuration
st.sidebar.title("⚙️ Configuration")
API_BASE = st.sidebar.text_input("API Base URL", DEFAULT_API_BASE)

# Check API health
try:
    health_resp = requests.get(f"{API_BASE}/health", timeout=5)
    if health_resp.ok:
        st.sidebar.success("✅ API Connected")
    else:
        st.sidebar.error("❌ API Error")
except:
    st.sidebar.error("❌ API Unreachable")

st.sidebar.markdown("---")
st.sidebar.markdown("### 📊 Analysis Options")
show_entities = st.sidebar.checkbox("Show Named Entities", value=True)
show_raw_scores = st.sidebar.checkbox("Show Raw Sentiment Scores", value=True)

# Main title
st.title("🔍 OSINT Sentiment Analyzer")
st.markdown("Analyze social media posts for sentiment and extract knowledge graphs")

# Create tabs for different functionalities
tab1, tab2, tab3, tab4 = st.tabs(["📝 Text Analysis", "🐦 Twitter Fetch", "📊 Visualizations", "🕸️ Knowledge Graph"])

# Store analysis results in session state
if 'analysis_data' not in st.session_state:
    st.session_state.analysis_data = None
if 'analysis_history' not in st.session_state:
    st.session_state.analysis_history = []

# ==================== TAB 1: TEXT ANALYSIS ====================
with tab1:
    st.header("📝 Analyze Text Posts")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        text_list = st.text_area(
            "Enter posts (one per line)",
            placeholder="Enter your posts here...\nEach line will be analyzed separately.",
            height=200,
            help="Enter multiple posts, each on a new line"
        )
        
        # Additional options
        with st.expander("📋 Post Metadata (Optional)"):
            default_platform = st.selectbox("Platform", ["twitter", "linkedin", "facebook", "instagram", "custom"])
            default_author = st.text_input("Author", "anonymous")
    
    with col2:
        st.markdown("### 💡 Sample Posts")
        if st.button("Load Positive Samples"):
            text_list = "Great product launch! The team did an amazing job.\nI love this new feature, it's incredibly useful!\nFantastic customer service, highly recommend!"
            st.rerun()
        if st.button("Load Negative Samples"):
            text_list = "Terrible experience, very disappointed.\nThe service was awful, I want a refund.\nWorst product I've ever used, total waste of money."
            st.rerun()
        if st.button("Load Mixed Samples"):
            text_list = "Amazing product launch in Jakarta! Congrats!\nThe service is okay, nothing special.\nVery disappointed with the delivery time."
            st.rerun()
    
    if st.button("🔍 Analyze Posts", type="primary", use_container_width=True):
        if text_list.strip():
            posts = []
            for i, t in enumerate([x.strip() for x in text_list.split("\n") if x.strip()]):
                posts.append({
                    "id": f"p{i+1}_{datetime.now().strftime('%H%M%S')}",
                    "platform": default_platform,
                    "author": default_author,
                    "text": t
                })
            
            with st.spinner("Analyzing posts..."):
                try:
                    resp = requests.post(f"{API_BASE}/api/v1/analyze",
                                       json={"posts": posts}, timeout=30)
                    if resp.ok:
                        data = resp.json()
                        st.session_state.analysis_data = data
                        st.session_state.analysis_history.append({
                            "timestamp": datetime.now().isoformat(),
                            "data": data
                        })
                        st.success(f"✅ Analyzed {len(data['items'])} posts!")
                    else:
                        st.error(f"API error: {resp.status_code} - {resp.text}")
                except Exception as e:
                    st.error(f"Request failed: {e}")
        else:
            st.warning("Please enter some text to analyze")
    
    # Display results if available
    if st.session_state.analysis_data:
        data = st.session_state.analysis_data
        
        st.markdown("---")
        st.subheader("📊 Analysis Results")
        
        # Stats cards
        stats = data.get("stats", {})
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Posts", stats.get("total_posts", 0))
        with col2:
            st.metric("😊 Positive", stats.get("positive", 0), 
                     delta_color="normal")
        with col3:
            st.metric("😐 Neutral", stats.get("neutral", 0))
        with col4:
            st.metric("😞 Negative", stats.get("negative", 0),
                     delta_color="inverse")
        
        # Detailed results
        st.markdown("### 📋 Detailed Results")
        
        for item in data["items"]:
            sentiment = item["sentiment"]["label"]
            score = item["sentiment"]["score"]
            
            # Color coding based on sentiment
            if sentiment == "positive":
                emoji = "😊"
                color = "green"
            elif sentiment == "negative":
                emoji = "😞"
                color = "red"
            else:
                emoji = "😐"
                color = "gray"
            
            with st.container():
                st.markdown(f"""
                <div style="padding: 10px; border-left: 4px solid {color}; background-color: #f8f9fa; margin: 10px 0; border-radius: 5px;">
                    <p style="margin: 0;"><strong>{emoji} {sentiment.upper()}</strong> (Score: {score:.3f})</p>
                    <p style="margin: 5px 0; color: #333;">{item['text']}</p>
                    <small style="color: #666;">Platform: {item['platform']} | Author: {item['author']}</small>
                </div>
                """, unsafe_allow_html=True)
                
                if show_entities and item.get("entities"):
                    entities_str = ", ".join([f"**{e['text']}** ({e['label']})" for e in item["entities"]])
                    st.markdown(f"🏷️ Entities: {entities_str}")

# ==================== TAB 2: TWITTER FETCH ====================
with tab2:
    st.header("🐦 Fetch Twitter Data")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        twitter_username = st.text_input("Twitter Username", placeholder="elonmusk", help="Enter username without @")
        tweet_limit = st.slider("Number of tweets to fetch", 5, 100, 10)
    
    with col2:
        st.markdown("### ℹ️ Notes")
        st.info("""
        - Twitter API has rate limits
        - Free tier: ~15 requests/15 min
        - Ensure valid bearer token in .env
        """)
    
    if st.button("🐦 Fetch & Analyze Tweets", type="primary"):
        if twitter_username:
            with st.spinner(f"Fetching tweets from @{twitter_username}..."):
                try:
                    # First, we need to fetch tweets via our backend
                    # For now, we'll create an endpoint or use direct fetch
                    fetch_resp = requests.post(
                        f"{API_BASE}/api/v1/twitter/fetch",
                        json={"username": twitter_username, "limit": tweet_limit},
                        timeout=60
                    )
                    
                    if fetch_resp.ok:
                        data = fetch_resp.json()
                        st.session_state.analysis_data = data
                        st.success(f"✅ Fetched and analyzed {len(data.get('items', []))} tweets!")
                    else:
                        try:
                            error_data = fetch_resp.json()
                            error_detail = error_data.get('detail', fetch_resp.text)
                        except:
                            error_detail = fetch_resp.text
                        
                        if "rate limit" in error_detail.lower():
                            st.warning(f"⚠️ Twitter API rate limited. Please wait a few minutes and try again.")
                        else:
                            st.error(f"Error ({fetch_resp.status_code}): {error_detail}")
                except requests.exceptions.ConnectionError:
                    st.error("Cannot connect to API. Is the server running?")
                except Exception as e:
                    st.error(f"Error: {e}")
        else:
            st.warning("Please enter a Twitter username")

# ==================== TAB 3: VISUALIZATIONS ====================
with tab3:
    st.header("📊 Sentiment Visualizations")
    
    if st.session_state.analysis_data:
        data = st.session_state.analysis_data
        items = data.get("items", [])
        stats = data.get("stats", {})
        
        if items:
            # Create DataFrame for visualizations
            df = pd.DataFrame([{
                "post_id": it["post_id"],
                "platform": it["platform"],
                "author": it["author"],
                "sentiment": it["sentiment"]["label"],
                "score": it["sentiment"]["score"],
                "text": it["text"][:50] + "..." if len(it["text"]) > 50 else it["text"]
            } for it in items])
            
            col1, col2 = st.columns(2)
            
            with col1:
                # Pie chart for sentiment distribution
                st.subheader("🥧 Sentiment Distribution")
                
                sentiment_counts = df["sentiment"].value_counts()
                colors = {"positive": "#28a745", "neutral": "#6c757d", "negative": "#dc3545"}
                
                fig_pie = px.pie(
                    values=sentiment_counts.values,
                    names=sentiment_counts.index,
                    color=sentiment_counts.index,
                    color_discrete_map=colors,
                    hole=0.4
                )
                fig_pie.update_layout(
                    showlegend=True,
                    legend=dict(orientation="h", yanchor="bottom", y=-0.2)
                )
                st.plotly_chart(fig_pie, use_container_width=True)
            
            with col2:
                # Bar chart for sentiment scores
                st.subheader("📊 Sentiment Scores")
                
                fig_bar = px.bar(
                    df,
                    x="post_id",
                    y="score",
                    color="sentiment",
                    color_discrete_map=colors,
                    labels={"score": "Sentiment Score", "post_id": "Post ID"}
                )
                fig_bar.add_hline(y=0, line_dash="dash", line_color="gray")
                fig_bar.update_layout(showlegend=True)
                st.plotly_chart(fig_bar, use_container_width=True)
            
            # Sentiment score distribution
            st.subheader("📈 Score Distribution")
            
            fig_hist = px.histogram(
                df,
                x="score",
                nbins=20,
                color="sentiment",
                color_discrete_map=colors,
                labels={"score": "Sentiment Score", "count": "Count"}
            )
            fig_hist.update_layout(bargap=0.1)
            st.plotly_chart(fig_hist, use_container_width=True)
            
            # Sentiment gauge
            st.subheader("🎯 Overall Sentiment Gauge")
            
            avg_score = df["score"].mean()
            
            fig_gauge = go.Figure(go.Indicator(
                mode="gauge+number+delta",
                value=avg_score,
                domain={'x': [0, 1], 'y': [0, 1]},
                title={'text': "Average Sentiment Score"},
                delta={'reference': 0},
                gauge={
                    'axis': {'range': [-1, 1]},
                    'bar': {'color': "darkblue"},
                    'steps': [
                        {'range': [-1, -0.05], 'color': '#dc3545'},
                        {'range': [-0.05, 0.05], 'color': '#6c757d'},
                        {'range': [0.05, 1], 'color': '#28a745'}
                    ],
                    'threshold': {
                        'line': {'color': "black", 'width': 4},
                        'thickness': 0.75,
                        'value': avg_score
                    }
                }
            ))
            fig_gauge.update_layout(height=300)
            st.plotly_chart(fig_gauge, use_container_width=True)
            
            # Entity analysis if available
            all_entities = []
            for item in items:
                for ent in item.get("entities", []):
                    all_entities.append(ent)
            
            if all_entities:
                st.subheader("🏷️ Named Entities")
                
                ent_df = pd.DataFrame(all_entities)
                ent_counts = ent_df.groupby(["label", "text"]).size().reset_index(name="count")
                
                fig_ent = px.treemap(
                    ent_counts,
                    path=["label", "text"],
                    values="count",
                    color="label"
                )
                st.plotly_chart(fig_ent, use_container_width=True)
            
            # Data table
            st.subheader("📋 Data Table")
            st.dataframe(df, use_container_width=True)
            
            # Export options
            st.download_button(
                label="📥 Download CSV",
                data=df.to_csv(index=False),
                file_name=f"sentiment_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )
    else:
        st.info("👆 Analyze some posts first to see visualizations")
        
        # Show sample visualization
        st.markdown("### 📊 Sample Visualization Preview")
        sample_data = {
            "sentiment": ["positive", "negative", "neutral", "positive", "negative"],
            "score": [0.8, -0.6, 0.1, 0.5, -0.3]
        }
        sample_df = pd.DataFrame(sample_data)
        
        fig = px.pie(
            sample_df,
            names="sentiment",
            color="sentiment",
            color_discrete_map={"positive": "#28a745", "neutral": "#6c757d", "negative": "#dc3545"},
            title="Sample Sentiment Distribution"
        )
        st.plotly_chart(fig, use_container_width=True)

# ==================== TAB 4: KNOWLEDGE GRAPH ====================
with tab4:
    st.header("🕸️ Knowledge Graph")
    
    col1, col2 = st.columns([3, 1])
    
    with col2:
        st.markdown("### 🎨 Graph Options")
        node_size = st.slider("Node Size", 100, 500, 300)
        show_labels = st.checkbox("Show Labels", value=True)
        layout_type = st.selectbox("Layout", ["spring", "circular", "kamada_kawai"])
    
    with col1:
        if st.button("🔄 Load Knowledge Graph", type="primary"):
            with st.spinner("Loading graph from Neo4j..."):
                try:
                    gresp = requests.get(f"{API_BASE}/api/v1/graph", timeout=30)
                    if gresp.ok:
                        graph_data = gresp.json()
                        nodes = graph_data.get("nodes", [])
                        edges = graph_data.get("edges", [])
                        
                        if nodes:
                            G = nx.DiGraph()
                            
                            # Color mapping for node types
                            type_colors = {
                                "user": "#3498db",
                                "post": "#2ecc71",
                                "platform": "#9b59b6",
                                "entity": "#e74c3c"
                            }
                            
                            # Add nodes with attributes
                            for n in nodes:
                                G.add_node(
                                    n["id"],
                                    label=n["label"][:20] + "..." if len(n["label"]) > 20 else n["label"],
                                    type=n["type"],
                                    color=type_colors.get(n["type"], "#95a5a6")
                                )
                            
                            # Add edges
                            for e in edges:
                                G.add_edge(e["source"], e["target"], label=e["label"])
                            
                            # Create layout
                            if layout_type == "spring":
                                pos = nx.spring_layout(G, seed=42, k=2)
                            elif layout_type == "circular":
                                pos = nx.circular_layout(G)
                            else:
                                pos = nx.kamada_kawai_layout(G)
                            
                            # Create figure
                            fig, ax = plt.subplots(figsize=(14, 10))
                            
                            # Get colors for nodes
                            node_colors = [G.nodes[n].get("color", "#95a5a6") for n in G.nodes]
                            
                            # Draw the graph
                            nx.draw_networkx_nodes(G, pos, node_color=node_colors, 
                                                 node_size=node_size, alpha=0.9, ax=ax)
                            nx.draw_networkx_edges(G, pos, edge_color="#bdc3c7", 
                                                 arrows=True, arrowsize=15, 
                                                 connectionstyle="arc3,rad=0.1", ax=ax)
                            
                            if show_labels:
                                labels = {n: G.nodes[n].get("label", n) for n in G.nodes}
                                nx.draw_networkx_labels(G, pos, labels=labels, 
                                                       font_size=8, ax=ax)
                            
                            # Add legend
                            legend_elements = [plt.Line2D([0], [0], marker='o', color='w', 
                                             markerfacecolor=color, markersize=10, label=type_name)
                                             for type_name, color in type_colors.items()]
                            ax.legend(handles=legend_elements, loc='upper left')
                            
                            ax.set_title(f"Knowledge Graph ({len(nodes)} nodes, {len(edges)} edges)")
                            ax.axis('off')
                            
                            st.pyplot(fig)
                            
                            # Graph statistics
                            st.markdown("### 📊 Graph Statistics")
                            stat_col1, stat_col2, stat_col3 = st.columns(3)
                            with stat_col1:
                                st.metric("Nodes", len(nodes))
                            with stat_col2:
                                st.metric("Edges", len(edges))
                            with stat_col3:
                                # Count by type
                                type_counts = {}
                                for n in nodes:
                                    t = n["type"]
                                    type_counts[t] = type_counts.get(t, 0) + 1
                                st.metric("Node Types", len(type_counts))
                            
                            # Show node type breakdown
                            st.markdown("### 📋 Node Types")
                            type_df = pd.DataFrame([
                                {"Type": k, "Count": v, "Color": type_colors.get(k, "#95a5a6")}
                                for k, v in type_counts.items()
                            ])
                            st.dataframe(type_df, use_container_width=True)
                        else:
                            st.warning("Graph is empty. Analyze some posts first!")
                    else:
                        st.error(f"API error: {gresp.status_code}")
                except Exception as e:
                    st.error(f"Error loading graph: {e}")

# Footer
st.markdown("---")
st.markdown(
    """
    <div style="text-align: center; color: #666;">
        <p>OSINT Sentiment Analyzer | Built with FastAPI, Neo4j, and Streamlit</p>
    </div>
    """,
    unsafe_allow_html=True
)
