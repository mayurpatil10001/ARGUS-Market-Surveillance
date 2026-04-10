"""
dashboard/components/graph_viz.py — Network graph visualization component.
"""
from __future__ import annotations

import numpy as np
import plotly.graph_objects as go
import streamlit as st

try:
    import networkx as nx
    NX_AVAILABLE = True
except ImportError:
    NX_AVAILABLE = False


def render_network_graph(
    nodes: list[dict],
    edges: list[dict],
    highlight_node: str = "",
    title: str = "Coordination Network",
    height: int = 500,
) -> None:
    """
    Renders a Plotly network graph from nodes/edges dicts.
    nodes: [{"id": str, "is_target": bool, ...}]
    edges: [{"source": str, "target": str, "weight": float}]
    """
    if not nodes:
        st.info("No network data to display.")
        return

    if not NX_AVAILABLE:
        st.warning("networkx not available for layout.")
        return

    G = nx.Graph()
    node_ids = [n["id"] for n in nodes]
    G.add_nodes_from(node_ids)
    for e in edges:
        G.add_edge(e["source"], e["target"], weight=e.get("weight", 1.0))

    try:
        pos = nx.spring_layout(G, seed=42, k=1.5)
    except Exception:
        pos = {n: (np.random.random(), np.random.random()) for n in node_ids}

    # Edges
    ex, ey = [], []
    for e in edges:
        s, t = e["source"], e["target"]
        if s in pos and t in pos:
            x0, y0 = pos[s]
            x1, y1 = pos[t]
            ex.extend([x0, x1, None])
            ey.extend([y0, y1, None])

    edge_trace = go.Scatter(
        x=ex, y=ey,
        mode="lines",
        line=dict(width=1.5, color="#C8A951"),
        hoverinfo="none",
    )

    # Nodes
    nx_arr = [pos[n["id"]][0] for n in nodes if n["id"] in pos]
    ny_arr = [pos[n["id"]][1] for n in nodes if n["id"] in pos]
    colors = [
        "#FF5252" if n["id"] == highlight_node or n.get("is_target")
        else "#FF9800" if G.degree(n["id"]) >= 3
        else "#1A7FBF"
        for n in nodes if n["id"] in pos
    ]
    sizes = [max(10, G.degree(n["id"]) * 5) for n in nodes if n["id"] in pos]

    node_trace = go.Scatter(
        x=nx_arr, y=ny_arr,
        mode="markers",
        hoverinfo="text",
        hovertext=[f"{n['id']}<br>Degree: {G.degree(n['id'])}" for n in nodes if n["id"] in pos],
        marker=dict(size=sizes, color=colors, line=dict(width=2, color="white")),
    )

    fig = go.Figure(
        data=[edge_trace, node_trace],
        layout=go.Layout(
            title=title,
            showlegend=False,
            hovermode="closest",
            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            plot_bgcolor="#0d1b2a",
            paper_bgcolor="#0d1b2a",
            font_color="white",
            height=height,
        ),
    )
    st.plotly_chart(fig, use_container_width=True)
