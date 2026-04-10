"""
dashboard/pages/network_graph.py — Account coordination network visualization.
"""
from __future__ import annotations

from datetime import datetime, timedelta

import numpy as np
import plotly.graph_objects as go
import requests
import streamlit as st


def render(api_base: str, token: str) -> None:
    st.title("🕸️ Account Network Graph")
    st.caption("Temporal coincidence coordination network — visualize connected accounts")

    headers = {"Authorization": f"Bearer {token}"}

    col_inp1, col_inp2, col_inp3 = st.columns(3)
    with col_inp1:
        account_id = st.text_input("Account ID", placeholder="e.g. a1b2c3d4e5f6g7h8")
    with col_inp2:
        scrip = st.text_input("Scrip (optional)", placeholder="e.g. RELIANCE")
    with col_inp3:
        days_back = st.slider("Days back", 1, 90, 30)

    if not account_id:
        st.info("Enter an Account ID to visualize its coordination network.")
        _demo_network()
        return

    to_date = datetime.utcnow()
    from_date = to_date - timedelta(days=days_back)

    if st.button("🔍 Fetch Network", type="primary"):
        with st.spinner("Building coordination graph..."):
            params: dict = {
                "from_date": from_date.isoformat(),
                "to_date": to_date.isoformat(),
            }
            if scrip:
                params["scrip"] = scrip

            network_data: dict = {}
            try:
                resp = requests.get(
                    f"{api_base}/accounts/{account_id}/network",
                    headers=headers,
                    params=params,
                    timeout=15,
                )
                if resp.ok:
                    network_data = resp.json()
                else:
                    st.error(f"API error: {resp.status_code}")
                    network_data = _demo_network_data(account_id)
            except Exception as exc:
                st.warning(f"API unavailable: {exc}. Showing demo network.")
                network_data = _demo_network_data(account_id)

            nodes = network_data.get("nodes", [])
            edges = network_data.get("edges", [])

            if not nodes:
                st.warning("No network data found for this account/period.")
                return

            st.metric("Connected Accounts", len(nodes))
            st.metric("Coordination Edges", len(edges))
            st.markdown("---")

            # Build plotly graph
            node_ids = [n["id"] for n in nodes]
            node_idx = {nid: i for i, nid in enumerate(node_ids)}

            # Layout using spring/circular
            import networkx as nx
            G = nx.Graph()
            G.add_nodes_from(node_ids)
            for e in edges:
                G.add_edge(e["source"], e["target"], weight=e.get("weight", 1.0))

            try:
                pos = nx.spring_layout(G, seed=42, k=2.0)
            except Exception:
                pos = {nid: (np.random.random(), np.random.random()) for nid in node_ids}

            # Edge traces
            edge_x, edge_y = [], []
            for e in edges:
                src, tgt = e["source"], e["target"]
                if src in pos and tgt in pos:
                    x0, y0 = pos[src]
                    x1, y1 = pos[tgt]
                    edge_x.extend([x0, x1, None])
                    edge_y.extend([y0, y1, None])

            edge_trace = go.Scatter(
                x=edge_x, y=edge_y,
                mode="lines",
                line=dict(width=1.5, color="#C8A951"),
                hoverinfo="none",
                name="Coordination",
            )

            # Node traces
            node_x = [pos[n["id"]][0] for n in nodes if n["id"] in pos]
            node_y = [pos[n["id"]][1] for n in nodes if n["id"] in pos]
            node_colors = []
            for n in nodes:
                if n.get("is_target"):
                    node_colors.append("#FF5252")
                elif G.degree(n["id"]) >= 3:
                    node_colors.append("#FF9800")
                else:
                    node_colors.append("#1A7FBF")

            node_text = [
                f"ID: {n['id']}<br>Connections: {G.degree(n['id'])}"
                for n in nodes
                if n["id"] in pos
            ]

            node_trace = go.Scatter(
                x=node_x, y=node_y,
                mode="markers+text",
                hoverinfo="text",
                text=[n["id"][:6] for n in nodes if n["id"] in pos],
                hovertext=node_text,
                textposition="top center",
                marker=dict(
                    size=[max(10, G.degree(n["id"]) * 4) for n in nodes if n["id"] in pos],
                    color=node_colors,
                    line=dict(width=2, color="white"),
                ),
                name="Accounts",
            )

            fig = go.Figure(
                data=[edge_trace, node_trace],
                layout=go.Layout(
                    title=f"Coordination Network for {account_id[:8]}... ({len(nodes)} accounts)",
                    showlegend=True,
                    hovermode="closest",
                    xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                    yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                    plot_bgcolor="#0d1b2a",
                    paper_bgcolor="#0d1b2a",
                    font_color="white",
                    height=600,
                    legend=dict(bgcolor="#1a2b5f"),
                ),
            )
            st.plotly_chart(fig, use_container_width=True)
            st.caption("🔴 Red = target account | 🟠 Orange = highly connected | 🔵 Blue = peripheral")

            # Node details
            if nodes:
                st.markdown("### Node Details")
                node_df_data = [
                    {
                        "Account ID": n["id"],
                        "Connections": G.degree(n["id"]),
                        "Is Target": "✅" if n.get("is_target") else "",
                    }
                    for n in nodes
                ]
                import pandas as pd
                st.dataframe(pd.DataFrame(node_df_data), use_container_width=True, hide_index=True)


def _demo_network_data(account_id: str) -> dict:
    accounts = [account_id] + [f"acc_{i:03d}" for i in range(12)]
    nodes = [{"id": a, "is_target": a == account_id} for a in accounts]
    edges = [
        {"source": account_id, "target": f"acc_{i:03d}", "weight": round(0.3 + i * 0.05, 2)}
        for i in range(5)
    ] + [
        {"source": f"acc_{i:03d}", "target": f"acc_{i+1:03d}", "weight": 0.4}
        for i in range(4)
    ]
    return {"account_id": account_id, "nodes": nodes, "edges": edges}


def _demo_network() -> None:
    """Show a sample coordination network for illustration."""
    import networkx as nx
    G = nx.karate_club_graph()
    pos = nx.spring_layout(G, seed=7)

    edge_x, edge_y = [], []
    for u, v in G.edges():
        x0, y0 = pos[u]
        x1, y1 = pos[v]
        edge_x.extend([x0, x1, None])
        edge_y.extend([y0, y1, None])

    fig = go.Figure(
        data=[
            go.Scatter(x=edge_x, y=edge_y, mode="lines",
                       line=dict(color="#C8A951", width=1), hoverinfo="none"),
            go.Scatter(
                x=[pos[n][0] for n in G.nodes()],
                y=[pos[n][1] for n in G.nodes()],
                mode="markers",
                marker=dict(size=12, color="#1A7FBF", line=dict(width=2, color="white")),
                hoverinfo="none",
            ),
        ],
        layout=go.Layout(
            title="Sample Coordination Network (Illustrative)",
            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            plot_bgcolor="#0d1b2a",
            paper_bgcolor="#0d1b2a",
            font_color="white",
            height=500,
        ),
    )
    st.plotly_chart(fig, use_container_width=True)
