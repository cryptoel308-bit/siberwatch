"""Visualisasi jaringan amplifikasi: akun-akun yang memakai hashtag/narasi
yang sama dianggap terhubung. Kluster akun yang serentak mengangkat narasi
yang sama adalah ciri khas kampanye buzzer terkoordinasi.

Urutan fallback:
1. networkx (bila terpasang) untuk layout spring.
2. Layout melingkar deterministik buatan sendiri (tanpa dependensi ekstra).
Render memakai plotly bila tersedia; selalu ada fallback berupa tabel relasi.
"""

from __future__ import annotations

import math
from collections import defaultdict

import pandas as pd


def narrative_clusters(posts: pd.DataFrame) -> dict[str, list[str]]:
    """hashtag -> daftar username unik yang memakainya."""
    clusters: dict[str, set] = defaultdict(set)
    for _, row in posts.iterrows():
        clusters[row["hashtag"]].add(row["username"])
    return {tag: sorted(users) for tag, users in clusters.items()}


def build_relations(posts: pd.DataFrame) -> list[tuple[str, str, str, int]]:
    """Pasangan akun yang terhubung karena berbagi hashtag.

    Returns list of (akun_a, akun_b, hashtag, jumlah_posting_bersama).
    """
    counts: dict[tuple[str, str, str], int] = defaultdict(int)
    for _, grp in posts.groupby("hashtag"):
        users = sorted(grp["username"].unique())
        tag = grp["hashtag"].iloc[0]
        n_posts = len(grp)
        for i in range(len(users)):
            for j in range(i + 1, len(users)):
                counts[(users[i], users[j], tag)] += n_posts
    return [(a, b, tag, n) for (a, b, tag), n in sorted(counts.items())]


def relation_table(posts: pd.DataFrame) -> pd.DataFrame:
    """Fallback non-visual: tabel relasi antarakun."""
    rels = build_relations(posts)
    return pd.DataFrame(rels, columns=["akun_a", "akun_b", "hashtag_bersama",
                                       "posting_pada_hashtag"])


def _layout(nodes: list[str], edges: list[tuple[str, str]]):
    """Posisi node: networkx spring layout bila ada, else lingkaran."""
    try:
        import networkx as nx

        g = nx.Graph()
        g.add_nodes_from(nodes)
        g.add_edges_from(edges)
        pos = nx.spring_layout(g, seed=42)
        return {n: (float(p[0]), float(p[1])) for n, p in pos.items()}, "networkx"
    except Exception:
        pos = {}
        n = max(len(nodes), 1)
        for i, node in enumerate(nodes):
            angle = 2 * math.pi * i / n
            pos[node] = (math.cos(angle), math.sin(angle))
        return pos, "lingkaran (fallback, networkx tidak terpasang)"


def make_network_figure(posts: pd.DataFrame, scores: dict[str, int] | None = None):
    """Bangun figure plotly jaringan akun. None bila plotly tidak tersedia.

    scores: dict username -> skor bot (untuk warna node; merah = risiko tinggi).
    """
    try:
        import plotly.graph_objects as go
    except Exception:
        return None

    rels = build_relations(posts)
    nodes = sorted(set(posts["username"]))
    edges = [(a, b) for a, b, _, _ in rels]
    pos, layout_name = _layout(nodes, edges)

    edge_x, edge_y = [], []
    for a, b in edges:
        x0, y0 = pos[a]
        x1, y1 = pos[b]
        edge_x += [x0, x1, None]
        edge_y += [y0, y1, None]
    edge_trace = go.Scatter(x=edge_x, y=edge_y, mode="lines",
                            line=dict(width=1, color="#999"), hoverinfo="none")

    node_x = [pos[n][0] for n in nodes]
    node_y = [pos[n][1] for n in nodes]
    if scores:
        node_color = [scores.get(n, 0) for n in nodes]
        colorbar = dict(title="Skor bot")
        colorscale = "Reds"
    else:
        degree = defaultdict(int)
        for a, b in edges:
            degree[a] += 1
            degree[b] += 1
        node_color = [degree[n] for n in nodes]
        colorbar = dict(title="Jumlah relasi")
        colorscale = "Blues"
    node_trace = go.Scatter(
        x=node_x, y=node_y, mode="markers+text", text=nodes,
        textposition="top center", hovertext=nodes, hoverinfo="text",
        marker=dict(size=14, color=node_color, colorscale=colorscale,
                    colorbar=colorbar, line=dict(width=1, color="#333")),
    )

    fig = go.Figure(data=[edge_trace, node_trace])
    fig.update_layout(
        title=f"Jaringan akun berdasarkan hashtag bersama (layout: {layout_name})",
        showlegend=False, hovermode="closest",
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        margin=dict(l=20, r=20, t=50, b=20),
    )
    return fig
