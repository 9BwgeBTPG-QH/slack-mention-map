"""Dot-connect 分析パイプライン (Slack 向け適応版).

オリジナル: ref/Dot-connect/app/core.py
変更点:
  - parse_address_field: Slack user ID ("Name <USER_ID>") 形式に対応
  - build_graph: domain → workspace, is_internal デフォルト True
  - load_csv / load_config: 削除 (呼び出し側で DataFrame / config を直接渡す)
"""

import logging
import re
from collections import defaultdict

import networkx as nx
import pandas as pd

log = logging.getLogger(__name__)

# コミュニティカラーパレット (Dot-connect 準拠)
COMMUNITY_COLORS = [
    "#6366f1",  # indigo
    "#f59e0b",  # amber
    "#10b981",  # emerald
    "#ef4444",  # red
    "#8b5cf6",  # violet
    "#06b6d4",  # cyan
    "#f97316",  # orange
    "#ec4899",  # pink
    "#14b8a6",  # teal
    "#a855f7",  # purple
    "#84cc16",  # lime
    "#e11d48",  # rose
]

# デフォルト設定
DEFAULT_CONFIG = {
    "company_domains": [],
    "thresholds": {
        "cc_key_person_threshold": 0.30,
        "min_edge_weight": 1,
        "hub_degree_weight": 0.5,
        "hub_betweenness_weight": 0.5,
    },
}


def load_config_from_env() -> dict:
    """環境変数から設定を上書きする。

    対応する環境変数:
        MENTION_MAP_CC_THRESHOLD    (float) CC キーマン検出閾値
        MENTION_MAP_MIN_EDGE_WEIGHT (int)   エッジ表示の最小重み
        MENTION_MAP_HUB_DEGREE_W    (float) ハブスコアの degree 重み
        MENTION_MAP_HUB_BETWEEN_W   (float) ハブスコアの betweenness 重み
        MENTION_MAP_COMPANY_DOMAINS (str)   カンマ区切りのドメインリスト
    """
    import os
    config = {
        "company_domains": DEFAULT_CONFIG["company_domains"][:],
        "thresholds": DEFAULT_CONFIG["thresholds"].copy(),
    }

    domains = os.environ.get("MENTION_MAP_COMPANY_DOMAINS")
    if domains:
        config["company_domains"] = [d.strip() for d in domains.split(",") if d.strip()]

    env_map = {
        "MENTION_MAP_CC_THRESHOLD": ("cc_key_person_threshold", float),
        "MENTION_MAP_MIN_EDGE_WEIGHT": ("min_edge_weight", int),
        "MENTION_MAP_HUB_DEGREE_W": ("hub_degree_weight", float),
        "MENTION_MAP_HUB_BETWEEN_W": ("hub_betweenness_weight", float),
    }
    for env_key, (config_key, cast) in env_map.items():
        val = os.environ.get(env_key)
        if val is not None:
            try:
                config["thresholds"][config_key] = cast(val)
            except ValueError:
                log.warning("Invalid value for %s: %s", env_key, val)

    return config


# ---------------------------------------------------------------------------
# Address parsing (Slack 適応版)
# ---------------------------------------------------------------------------

def parse_address_field(field: str) -> list[tuple[str, str]]:
    """'Name <id>; Name2 <id2>' 形式のフィールドをパース.

    Slack 版: ID に @ が含まれなくても受け付ける。

    Returns:
        list of (id, name)
    """
    if not field or (isinstance(field, float) and pd.isna(field)):
        return []
    field = str(field)
    results = []
    for entry in field.split(";"):
        entry = entry.strip()
        if not entry:
            continue
        match = re.match(r"^(.*?)\s*<(.+?)>$", entry)
        if match:
            name = match.group(1).strip()
            identifier = match.group(2).strip()
            results.append((identifier, name))
        elif entry:
            # フォールバック: <> なしの場合はそのまま ID として扱う
            results.append((entry, ""))
    return results


# ---------------------------------------------------------------------------
# Graph construction
# ---------------------------------------------------------------------------

def build_graph(df: pd.DataFrame, config: dict | None = None, domain_map: dict | None = None) -> nx.DiGraph:
    """メッセージ DataFrame から有向グラフを構築.

    Args:
      domain_map: user_id → email domain のマッピング (省略時は from_domain カラムから取得)
    """
    if config is None:
        config = load_config_from_env()
    if domain_map is None:
        domain_map = {}

    G = nx.DiGraph()
    company_domains = [d.lower() for d in config.get("company_domains", [])]

    node_stats = defaultdict(lambda: {
        "name": "", "email": "", "domain": "",
        "sent": 0, "received": 0, "cc_count": 0,
    })

    for _, row in df.iterrows():
        from_id = str(row.get("from_email", "")).strip()
        from_name = str(row.get("from_name", "")).strip() if pd.notna(row.get("from_name")) else ""

        if not from_id:
            continue

        from_domain = str(row.get("from_domain", "")).strip() if pd.notna(row.get("from_domain")) else ""

        # 送信者ノード
        node_stats[from_id]["name"] = from_name or node_stats[from_id]["name"]
        node_stats[from_id]["email"] = from_id
        if from_domain:
            node_stats[from_id]["domain"] = from_domain
        node_stats[from_id]["sent"] += 1

        # To 受信者
        to_addrs = parse_address_field(row.get("to", ""))
        for to_id, to_name in to_addrs:
            node_stats[to_id]["name"] = to_name or node_stats[to_id]["name"]
            node_stats[to_id]["email"] = to_id
            if to_id in domain_map and not node_stats[to_id]["domain"]:
                node_stats[to_id]["domain"] = domain_map[to_id]
            node_stats[to_id]["received"] += 1

            if G.has_edge(from_id, to_id):
                G[from_id][to_id]["to_weight"] += 1
            else:
                G.add_edge(from_id, to_id, to_weight=1, cc_weight=0)

        # CC 受信者
        cc_addrs = parse_address_field(row.get("cc", ""))
        for cc_id, cc_name in cc_addrs:
            node_stats[cc_id]["name"] = cc_name or node_stats[cc_id]["name"]
            node_stats[cc_id]["email"] = cc_id
            if cc_id in domain_map and not node_stats[cc_id]["domain"]:
                node_stats[cc_id]["domain"] = domain_map[cc_id]
            node_stats[cc_id]["cc_count"] += 1

            if G.has_edge(from_id, cc_id):
                G[from_id][cc_id]["cc_weight"] += 1
            else:
                G.add_edge(from_id, cc_id, to_weight=0, cc_weight=1)

    # ノード属性を設定
    for node_id, stats in node_stats.items():
        if node_id in G.nodes:
            domain = stats.get("domain", "")
            if company_domains:
                is_internal = any(domain.endswith(d) for d in company_domains)
            else:
                # Slack 単一ワークスペース: 全員社内扱い
                is_internal = True

            G.nodes[node_id].update({
                "name": stats["name"] or node_id,
                "email": node_id,
                "domain": domain,
                "is_internal": is_internal,
                "sent": stats["sent"],
                "received": stats["received"],
                "cc_count": stats["cc_count"],
            })

    log.info("グラフ構築: %d ノード, %d エッジ", G.number_of_nodes(), G.number_of_edges())
    return G


# ---------------------------------------------------------------------------
# Analysis
# ---------------------------------------------------------------------------

def analyze_graph(G: nx.DiGraph, total_mails: int, config: dict | None = None) -> dict:
    """ネットワーク分析を実行.

    Returns:
        dict with keys: total_mails, cc_key_persons, hubs, communities, community_map
    """
    if config is None:
        config = load_config_from_env()

    if G.number_of_nodes() == 0:
        return {
            "total_mails": 0,
            "communities": [],
            "community_map": {},
            "cc_key_persons": [],
            "hubs": [],
        }

    thresholds = config.get("thresholds", {})

    # --- CC キーマン ---
    cc_threshold = thresholds.get("cc_key_person_threshold", 0.30)
    cc_key_persons = []
    for node, data in G.nodes(data=True):
        cc_count = data.get("cc_count", 0)
        if cc_count / total_mails >= cc_threshold:
            cc_key_persons.append({
                "email": node,
                "name": data.get("name", node),
                "cc_count": cc_count,
                "ratio": round(cc_count / total_mails, 3),
            })
    cc_key_persons.sort(key=lambda x: x["cc_count"], reverse=True)

    # --- ハブ (centrality) ---
    hub_dw = thresholds.get("hub_degree_weight", 0.5)
    hub_bw = thresholds.get("hub_betweenness_weight", 0.5)

    undirected = G.to_undirected()
    degree_c = nx.degree_centrality(undirected)
    # 大規模グラフでは近似計算 (k サンプリング) で高速化
    n_nodes = len(undirected)
    if n_nodes > 200:
        k = min(100, n_nodes)
        betweenness_c = nx.betweenness_centrality(undirected, k=k)
        log.info("Betweenness centrality: 近似計算 (k=%d/%d)", k, n_nodes)
    else:
        betweenness_c = nx.betweenness_centrality(undirected)

    hub_scores = {}
    for node in G.nodes:
        hub_scores[node] = (
            hub_dw * degree_c.get(node, 0)
            + hub_bw * betweenness_c.get(node, 0)
        )

    top_hubs = sorted(hub_scores.items(), key=lambda x: x[1], reverse=True)[:20]
    hubs = []
    for node_id, score in top_hubs:
        data = G.nodes[node_id]
        hubs.append({
            "email": node_id,
            "name": data.get("name", node_id),
            "score": round(score, 4),
            "degree_centrality": round(degree_c.get(node_id, 0), 4),
            "betweenness_centrality": round(betweenness_c.get(node_id, 0), 4),
        })

    # --- Louvain コミュニティ ---
    communities = list(nx.community.louvain_communities(undirected, seed=42))
    community_map = {}
    for idx, comm in enumerate(communities):
        for node in comm:
            community_map[node] = idx

    for node in G.nodes:
        G.nodes[node]["community"] = community_map.get(node, 0)

    community_info = []
    for idx, comm in enumerate(communities):
        members = [
            {"email": n, "name": G.nodes[n].get("name", n)}
            for n in comm if n in G.nodes
        ]
        community_info.append({
            "id": idx,
            "color": COMMUNITY_COLORS[idx % len(COMMUNITY_COLORS)],
            "size": len(comm),
            "members": members,
        })

    log.info(
        "分析完了: CCキーマン %d人, コミュニティ %d個",
        len(cc_key_persons), len(communities),
    )

    return {
        "total_mails": total_mails,
        "cc_key_persons": cc_key_persons,
        "hubs": hubs,
        "communities": community_info,
        "community_map": community_map,
    }


# ---------------------------------------------------------------------------
# vis.js data generation
# ---------------------------------------------------------------------------

def generate_vis_data(G: nx.DiGraph, analysis: dict, config: dict | None = None) -> dict:
    """vis.js 用の JSON データを生成."""
    if config is None:
        config = load_config_from_env()
    thresholds = config.get("thresholds", {})
    min_weight = thresholds.get("min_edge_weight", 1)
    community_map = analysis["community_map"]
    communities = analysis["communities"]

    # ノードデータ
    nodes = []
    cc_key_emails = {p["email"] for p in analysis["cc_key_persons"]}
    hub_emails = {h["email"] for h in analysis["hubs"][:10]}

    for node, data in G.nodes(data=True):
        comm_id = community_map.get(node, 0)
        color = COMMUNITY_COLORS[comm_id % len(COMMUNITY_COLORS)]

        total_activity = data.get("sent", 0) + data.get("received", 0) + data.get("cc_count", 0)
        size = max(8, min(40, 8 + total_activity * 0.5))

        label = data.get("name", node)
        if len(label) > 15:
            label = label[:14] + "\u2026"

        nodes.append({
            "id": node,
            "label": label,
            "name": data.get("name", node),
            "email": node,
            "domain": data.get("domain", ""),
            "is_internal": data.get("is_internal", True),
            "sent": data.get("sent", 0),
            "received": data.get("received", 0),
            "cc_count": data.get("cc_count", 0),
            "community": comm_id,
            "color": color,
            "size": size,
            "is_cc_key": node in cc_key_emails,
            "is_hub": node in hub_emails,
        })

    # エッジデータ
    edges = []
    for u, v, data in G.edges(data=True):
        to_w = data.get("to_weight", 0)
        cc_w = data.get("cc_weight", 0)
        total = to_w + cc_w
        if total < min_weight:
            continue
        edges.append({
            "from": u,
            "to": v,
            "to_weight": to_w,
            "cc_weight": cc_w,
            "weight": total,
            "width": max(1, min(8, total * 0.3)),
        })

    # ワードクラウドデータ
    wordcloud_data = []
    for node, data in G.nodes(data=True):
        total = data.get("sent", 0) + data.get("received", 0) + data.get("cc_count", 0)
        if total > 0:
            comm_id = community_map.get(node, 0)
            wordcloud_data.append({
                "text": data.get("name", node),
                "size": total,
                "email": node,
                "color": COMMUNITY_COLORS[comm_id % len(COMMUNITY_COLORS)],
            })
    wordcloud_data.sort(key=lambda x: x["size"], reverse=True)

    return {
        "nodes": nodes,
        "edges": edges,
        "communities": communities,
        "analysis": {
            "total_mails": analysis["total_mails"],
            "total_nodes": len(nodes),
            "total_edges": len(edges),
            "cc_key_persons": analysis["cc_key_persons"],
            "hubs": analysis["hubs"],
        },
        "wordcloud_data": wordcloud_data,
    }


def run_analysis_pipeline(df: pd.DataFrame, config: dict | None = None, domain_map: dict | None = None) -> dict:
    """DataFrame → グラフ構築 → 分析 → vis.js JSON の一括実行.

    Returns:
        vis.js 用 JSON データ (nodes, edges, communities, analysis, wordcloud_data)
    """
    if config is None:
        config = load_config_from_env()

    G = build_graph(df, config, domain_map)
    total_mails = len(df)
    analysis = analyze_graph(G, total_mails, config)
    vis_data = generate_vis_data(G, analysis, config)
    return vis_data
