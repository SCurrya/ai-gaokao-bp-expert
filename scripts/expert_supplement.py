import json
import os
from typing import Dict, List
from pathlib import Path

from agent_schema import StudentProfile


def get_expert_card_path() -> str:
    repo_data = Path(__file__).resolve().parents[1] / "data" / "expert_supplement_cards.json"
    candidate_paths = [
        str(repo_data),
        "/app/agent_project/data/expert_supplement_cards.json",
        "e:/Ke_Study/AI_Gaokao_BP_Expert/data/expert_supplement_cards.json",
    ]
    for path in candidate_paths:
        if os.path.exists(path):
            return path
    raise FileNotFoundError("未找到 expert_supplement_cards.json。")


def load_cards() -> List[Dict]:
    with open(get_expert_card_path(), "r", encoding="utf-8") as file:
        return json.load(file).get("cards", [])


def prefers_science(profile: StudentProfile) -> bool:
    prefs = profile.prefs or ""
    return any(keyword in prefs for keyword in ["理学", "数学", "物理", "化学", "生物"])


def normalize_subject_combo(profile: StudentProfile) -> str:
    return profile.subject_combo or ("物理" if profile.group == "phys" else "历史" if profile.group == "hist" else "")


def card_matches_profile(card: Dict, profile: StudentProfile) -> bool:
    rank = profile.rank or 0
    if rank and not (card.get("rank_min", 0) <= rank <= card.get("rank_max", 10**9)):
        return False

    card_scope = card.get("region_scope", "any")
    if card_scope == "outside" and profile.mobility_preference == "prefer_in_province":
        return False

    required_combos = card.get("subject_combo_required", [])
    if required_combos and normalize_subject_combo(profile) not in required_combos:
        return False
    return True


def score_card(card: Dict, profile: StudentProfile, user_text: str) -> int:
    score = int(card.get("priority", 0))
    text = (user_text or "") + " " + (profile.prefs or "")
    for tag in card.get("fit_tags", []):
        if tag in text:
            score += 3
    if prefers_science(profile) and any(tag in ["理学", "数学", "物理", "化学"] for tag in card.get("fit_tags", [])):
        score += 5
    if card.get("college", "") in text or card.get("major", "") in text:
        score += 8
    if profile.mobility_preference == "prefer_in_province" and card.get("region_scope") == "in_province":
        score += 2
    if profile.mobility_preference == "accept_outside" and card.get("region_scope") == "outside":
        score += 2
    return score


def pick_expert_cards(profile: StudentProfile, user_text: str = "", limit: int = 4) -> List[Dict]:
    matched_cards = [card for card in load_cards() if card_matches_profile(card, profile)]
    ranked = sorted(matched_cards, key=lambda card: score_card(card, profile, user_text), reverse=True)
    return ranked[:limit]


def render_expert_cards(profile: StudentProfile, user_text: str = "", limit: int = 4) -> str:
    cards = pick_expert_cards(profile, user_text=user_text, limit=limit)
    lines = [
        "## 人工专家补充判断卡片",
        "- 说明：以下内容不来自广东自动样本库，而是人工整理的专家知识卡，只做补充判断，不直接参与自动冲稳保排序。",
    ]
    if not cards:
        lines.append("- 当前没有命中的补充卡片。")
        return "\n".join(lines)

    for index, card in enumerate(cards, start=1):
        lines.extend([
            f"- 卡片 {index}：{card['college']}｜{card['major']}",
            f"  适用条件：位次约 {card['rank_min']} - {card['rank_max']}，选科 {', '.join(card.get('subject_combo_required', ['不限']))}，范围 {card.get('region_scope', 'any')}",
            f"  为什么适合：{card['why_fit']}",
            f"  为什么不进自动结果：{card['why_not_auto']}",
        ])
    return "\n".join(lines)
