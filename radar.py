from __future__ import annotations

import math
from typing import Any

FAMILY_CONFIGS: dict[str, dict[str, Any]] = {
    "claude":   {"base_deg": 0.0,   "color": "#f59e0b", "name": "Anthropic Claude", "short": "Anthropic"},
    "gpt":      {"base_deg": 40.0,  "color": "#10b981", "name": "OpenAI GPT",       "short": "OpenAI"},
    "gemini":   {"base_deg": 80.0,  "color": "#38bdf8", "name": "Google Gemini",    "short": "Google"},
    "deepseek": {"base_deg": 120.0, "color": "#06b6d4", "name": "DeepSeek",         "short": "DeepSeek"},
    "grok":     {"base_deg": 160.0, "color": "#c084fc", "name": "xAI Grok",         "short": "xAI"},
    "llama":    {"base_deg": 200.0, "color": "#818cf8", "name": "Meta Llama",       "short": "Meta"},
    "qwen":     {"base_deg": 240.0, "color": "#fb7185", "name": "Alibaba Qwen",     "short": "Qwen"},
    "mistral":  {"base_deg": 280.0, "color": "#facc15", "name": "Mistral AI",       "short": "Mistral"},
    "frontier": {"base_deg": 320.0, "color": "#2dd4bf", "name": "Frontier AI",      "short": "Frontier"},
}


def build_radar_constellation(bank: dict) -> list[dict[str, Any]]:
    """Generates 2D polar & cartesian constellation coordinates for all enrolled models."""
    models = bank.get("models", [])
    radar_models: list[dict[str, Any]] = []

    for fam_id, cfg in FAMILY_CONFIGS.items():
        fam_models = [m for m in models if m.get("family") == fam_id]
        count = len(fam_models)
        base_rad = math.radians(cfg["base_deg"])

        for i, m in enumerate(fam_models):
            # Angular spread across family sector (+/- 13 degrees)
            spread_deg = ((i / max(1, count - 1)) - 0.5) * 26.0 if count > 1 else 0.0
            rad = math.radians((cfg["base_deg"] + spread_deg) % 360)
            # Alternating radial shells between 0.52 and 0.90
            r = 0.52 + 0.38 * ((i % 4) / 3.0)
            x = r * math.cos(rad)
            y = r * math.sin(rad)

            radar_models.append({
                "id": m["id"],
                "display_name": m["display_name"],
                "family": fam_id,
                "family_name": cfg["name"],
                "family_short": cfg["short"],
                "x": round(x, 4),
                "y": round(y, 4),
                "r": round(r, 4),
                "angle_deg": round(math.degrees(rad) % 360, 1),
                "color": cfg["color"],
            })

    return radar_models


def project_radar_coordinate(result: dict, constellation_nodes: list[dict]) -> dict[str, Any]:
    """Projects an audit evaluation result into the 2D Latent Radar manifold."""
    node_map = {n["id"]: n for n in constellation_nodes}
    is_ood = result.get("is_ood", False)

    if is_ood:
        closest = result.get("closest_candidate", "")
        base_node = node_map.get(closest)
        if base_node:
            rad = math.radians(base_node["angle_deg"])
        else:
            rad = math.radians(90.0)

        # Place in Outer Unanchored Drift Zone (r = 1.18, outside the 1.0 perimeter)
        r = 1.18
        x = r * math.cos(rad)
        y = r * math.sin(rad)
        return {
            "x": round(x, 4),
            "y": round(y, 4),
            "r": round(r, 4),
            "angle_deg": round(math.degrees(rad) % 360, 1),
            "status": "UNANCHORED_OOD",
            "status_label": "OUT-OF-DISTRIBUTION (DRIFT)",
            "label": result.get("prediction_name", "Unanchored / OOD Void"),
            "confidence": 0.0,
            "color": "#ef4444",
            "nearest_cluster": base_node["family_name"] if base_node else "Unknown",
            "dispersion_sigma": 0.40,
        }

    # Centroid coordinate weighted by candidate model posteriors
    x_sum = 0.0
    y_sum = 0.0
    weight_sum = 0.0
    candidates = result.get("results", [])[:6]
    for c in candidates:
        m_id = c.get("model")
        prob = float(c.get("probability", 0.0))
        if m_id in node_map and prob > 0.001:
            node = node_map[m_id]
            x_sum += prob * node["x"]
            y_sum += prob * node["y"]
            weight_sum += prob

    if weight_sum > 0:
        x = x_sum / weight_sum
        y = y_sum / weight_sum
    else:
        top_m = result.get("prediction")
        node = node_map.get(top_m, constellation_nodes[0] if constellation_nodes else {"x": 0, "y": 0})
        x, y = node["x"], node["y"]

    r = math.sqrt(x * x + y * y)
    angle_rad = math.atan2(y, x)
    angle_deg = math.degrees(angle_rad) % 360

    pred_m = result.get("prediction")
    pred_node = node_map.get(pred_m)
    fam_color = pred_node["color"] if pred_node else "#10b981"
    fam_name = pred_node["family_name"] if pred_node else "Frontier"

    top_sim = float(result.get("top_similarity", 0.85))
    dispersion = max(0.04, min(0.25, (1.0 - top_sim) * 0.5))

    return {
        "x": round(x, 4),
        "y": round(y, 4),
        "r": round(r, 4),
        "angle_deg": round(angle_deg, 1),
        "status": "LOCKED",
        "status_label": "TARGET ACQUIRED (AUTHENTIC CLUSTER)",
        "label": result.get("prediction_name", "Identified Model"),
        "confidence": round(float(result.get("probability", 1.0)) * 100, 1),
        "color": fam_color,
        "nearest_cluster": fam_name,
        "dispersion_sigma": round(dispersion, 4),
    }
