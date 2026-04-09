import argparse
import json
import re
from dataclasses import asdict
from typing import List, Optional

from agent_schema import IntakeResult, StudentProfile
from session_store import (
    build_profile_from_dict,
    load_session_state,
    merge_profiles,
    reset_session_state,
    save_session_state,
)


SUPPORTED_PROVINCE = "广东"
PROVINCE_CANDIDATES = [
    "北京", "天津", "上海", "重庆", "河北", "山西", "辽宁", "吉林", "黑龙江",
    "江苏", "浙江", "安徽", "福建", "江西", "山东", "河南", "湖北", "湖南",
    "广东", "海南", "四川", "贵州", "云南", "陕西", "甘肃", "青海", "台湾",
    "内蒙古", "广西", "西藏", "宁夏", "新疆", "香港", "澳门",
]

FAMILY_LABELS = [
    ("普通工薪家庭", ["普通工薪", "工薪家庭", "普通家庭", "家里一般", "家庭一般", "条件一般"]),
    ("看重稳定", ["看重稳定", "想稳定", "求稳定", "考公", "考编", "体制内", "体制"]),
]

MOBILITY_PATTERNS = [
    ("prefer_in_province", ["不可接受出省", "不接受出省", "不可出省", "不能出省", "不可以出省", "只接受省内", "只留广东", "只能在广东", "只能留广东"]),
    ("accept_outside", ["接受出省", "可接受出省", "能出省", "可以出省", "外省也行", "不介意出省", "接受外省"]),
    ("prefer_in_province", ["留广东", "想留广东", "不想出省", "想留省内", "省内优先", "广东优先"]),
]

PREFERENCE_PATTERNS = [
    r"(想留[^，。；,;!\n]+)",
    r"(想去[^，。；,;!\n]+)",
    r"(想学[^，。；,;!\n]+)",
    r"(偏(?:向)?[^，。；,;!\n]+)",
    r"(喜欢[^，。；,;!\n]+)",
    r"(希望[^，。；,;!\n]+)",
    r"(不想[^，。；,;!\n]+)",
    r"(不考虑[^，。；,;!\n]+)",
    r"(接受[^，。；,;!\n]+)",
    r"(能接受[^，。；,;!\n]+)",
    r"(只考虑[^，。；,;!\n]+)",
]


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def parse_rank_value(raw_value: str, use_wan: bool) -> Optional[int]:
    value = raw_value.replace(",", "").strip()
    if not value:
        return None
    if use_wan:
        return int(float(value) * 10000)
    return int(float(value))


def extract_rank(text: str) -> Optional[int]:
    patterns = [
        (r"(?:排位|位次|排名|省排|省位次)[^\d]{0,6}(\d+(?:\.\d+)?)\s*万", True),
        (r"(?:排位|位次|排名|省排|省位次)[^\d]{0,6}(\d[\d,]*)", False),
        (r"(\d+(?:\.\d+)?)\s*万\s*(?:名|位|排)", True),
        (r"(\d[\d,]*)\s*(?:名|位|排)", False),
    ]
    for pattern, use_wan in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return parse_rank_value(match.group(1), use_wan)
    return None


def extract_group(text: str) -> Optional[str]:
    phys_keywords = ["物理", "物化生", "物化", "物生", "理科", "physics", "phys"]
    hist_keywords = ["历史", "政史地", "史政", "历政", "文科", "history", "hist"]

    if any(keyword.lower() in text.lower() for keyword in hist_keywords):
        return "hist"
    if any(keyword.lower() in text.lower() for keyword in phys_keywords):
        return "phys"
    return None


def extract_province(text: str) -> str:
    for province in PROVINCE_CANDIDATES:
        if province in text:
            return province
    return SUPPORTED_PROVINCE


def extract_family(text: str) -> str:
    labels = []
    for label, keywords in FAMILY_LABELS:
        if any(keyword in text for keyword in keywords):
            labels.append(label)

    seen = set()
    unique_labels = []
    for label in labels:
        if label not in seen:
            seen.add(label)
            unique_labels.append(label)
    return "，".join(unique_labels)


def extract_mobility_preference(text: str) -> str:
    negative_keywords = ["不可接受出省", "不接受出省", "不可出省", "不能出省", "不可以出省", "只接受省内", "只留广东", "只能在广东", "只能留广东"]
    positive_keywords = ["接受出省", "可接受出省", "能出省", "可以出省", "外省也行", "不介意出省", "接受外省"]
    province_keywords = ["留广东", "想留广东", "不想出省", "想留省内", "省内优先", "广东优先"]

    if any(keyword in text for keyword in negative_keywords):
        return "prefer_in_province"
    if any(keyword in text for keyword in positive_keywords):
        return "accept_outside"
    if any(keyword in text for keyword in province_keywords):
        return "prefer_in_province"
    return ""


def mobility_label(value: str) -> str:
    return {
        "accept_outside": "接受出省",
        "prefer_in_province": "省内优先",
    }.get(value, "未识别")


def is_mobility_phrase(text: str) -> bool:
    normalized = text.replace(" ", "")
    keywords = ["留广东", "省内", "出省", "外省", "广东优先"]
    return any(keyword in normalized for keyword in keywords)


def extract_subject_combo(text: str) -> str:
    if any(keyword in text for keyword in ["物化生", "物理化学生物", "物理+化学+生物"]):
        return "物理+化学+生物"
    if any(keyword in text for keyword in ["物化", "物理化学", "物理+化学"]):
        return "物理+化学"
    if any(keyword in text for keyword in ["物生", "物理生物", "物理+生物"]):
        return "物理+生物"
    if any(keyword in text for keyword in ["史政地", "历史政治地理", "历史+政治+地理"]):
        return "历史+政治+地理"
    if any(keyword in text for keyword in ["历史", "政史地", "史政", "历政", "文科", "history", "hist"]):
        return "历史"
    if any(keyword in text for keyword in ["物理", "物化生", "物化", "物生", "理科", "physics", "phys"]):
        return "物理"
    return ""


def extract_preferences(text: str) -> str:
    matches = []
    for pattern in PREFERENCE_PATTERNS:
        for raw_match in re.findall(pattern, text, flags=re.IGNORECASE):
            cleaned = raw_match.strip(" ：:;；，。,.!?！？")
            if cleaned and not is_mobility_phrase(cleaned) and cleaned not in matches:
                matches.append(cleaned)

    major_keywords = ["计算机", "软件", "电气", "电子", "自动化", "口腔", "临床", "师范", "法学", "金融"]
    if not matches:
        for keyword in major_keywords:
            if keyword in text:
                matches.append(f"偏{keyword}")
                break
    return "；".join(matches)


def build_student_profile(raw_text: str) -> StudentProfile:
    text = normalize_text(raw_text)
    province = extract_province(text)
    unsupported_province = ""
    if province != SUPPORTED_PROVINCE:
        unsupported_province = province

    return StudentProfile(
        province=province,
        rank=extract_rank(text),
        group=extract_group(text),
        family=extract_family(text),
        prefs=extract_preferences(text),
        mobility_preference=extract_mobility_preference(text),
        subject_combo=extract_subject_combo(text),
        unsupported_province=unsupported_province,
        raw_text=text,
    )


def get_missing_fields(profile: StudentProfile) -> List[str]:
    missing_fields = []
    if profile.rank is None:
        missing_fields.append("rank")
    if profile.group is None:
        missing_fields.append("group")
    if not profile.family:
        missing_fields.append("family")
    if not profile.prefs:
        missing_fields.append("prefs")
    return missing_fields


def get_follow_up_questions(missing_fields: List[str]) -> List[str]:
    question_map = {
        "rank": "你的广东省排位是多少？请直接告诉我具体位次，比如 42000。",
        "group": "你是物理类还是历史类？",
        "family": "你的家庭情况更偏哪种：普通工薪、看重稳定，还是有别的约束？",
        "prefs": "你偏哪些专业？明确不想学什么？如果愿意，也可以顺手补一句你更偏省内还是接受出省。",
    }
    return [question_map[field_name] for field_name in missing_fields]


def format_profile_summary(profile: StudentProfile) -> List[str]:
    group_label = "物理类" if profile.group == "phys" else "历史类" if profile.group == "hist" else "未识别"
    return [
        f"- 省份：{profile.province}",
        f"- 排位：{profile.rank if profile.rank is not None else '未识别'}",
        f"- 科类：{group_label}",
        f"- 流动偏好：{mobility_label(profile.mobility_preference)}",
        f"- 选科组合：{profile.subject_combo or '仅识别到科类，未识别到更细选科组合'}",
        f"- 家庭情况：{profile.family or '未识别'}",
        f"- 偏好：{profile.prefs or '未识别'}",
    ]


def should_reset_session(user_text: str) -> bool:
    keywords = ["重置会话", "清空画像", "重新开始", "reset session", "reset"]
    normalized = normalize_text(user_text).lower()
    return any(keyword in normalized for keyword in keywords)


def run_intake(user_text: str, session_id: str = "wechat_main") -> IntakeResult:
    if should_reset_session(user_text):
        reset_session_state(session_id)
        cleared_profile = StudentProfile(raw_text=normalize_text(user_text))
        save_session_state(session_id, cleared_profile, user_text, "reset", [])
        return IntakeResult(
            status="session_reset",
            profile=cleared_profile,
        )

    extracted_profile = build_student_profile(user_text)
    previous_state = load_session_state(session_id)
    previous_profile = build_profile_from_dict(previous_state.get("profile", {}))
    profile = merge_profiles(previous_profile, extracted_profile)

    if profile.unsupported_province:
        result = IntakeResult(
            status="unsupported_province",
            profile=profile,
        )
        save_session_state(session_id, profile, user_text, result.status, [])
        return result

    missing_fields = get_missing_fields(profile)
    if missing_fields:
        result = IntakeResult(
            status="needs_more_info",
            profile=profile,
            missing_fields=missing_fields,
            follow_up_questions=get_follow_up_questions(missing_fields),
        )
        save_session_state(session_id, profile, user_text, result.status, missing_fields)
        return result

    result = IntakeResult(
        status="ready",
        profile=profile,
    )
    save_session_state(session_id, profile, user_text, result.status, [])
    return result


def format_intake_response(result: IntakeResult) -> str:
    profile_lines = format_profile_summary(result.profile)

    if result.status == "session_reset":
        lines = [
            "# 客户经理 Agent 结果",
            "",
            "- 已为你清空当前会话画像。",
            "- 你可以重新告诉我：排位、科类、家庭情况和偏好，我会按新的案子重新建档。",
        ]
        return "\n".join(lines)

    if result.status == "unsupported_province":
        lines = [
            "# 客户经理 Agent 结果",
            "",
            f"- 当前你提到的省份是：{result.profile.unsupported_province}",
            f"- 这个版本目前只接入了 {SUPPORTED_PROVINCE} 数据集，暂时不能直接给其他省份出正式 BP 方案。",
            "- 如果你就是广东考生，请直接补一句“我是广东考生”。",
            "- 如果你确实是外省考生，我可以先继续帮你梳理画像和志愿策略框架。",
        ]
        return "\n".join(lines)

    if result.status == "needs_more_info":
        lines = [
            "# 客户经理 Agent 结果",
            "",
            "## 当前已识别画像",
            *profile_lines,
            "",
            "## 还缺哪些关键信息",
        ]
        missing_label_map = {
            "rank": "排位",
            "group": "科类",
            "family": "家庭情况",
            "prefs": "偏好与明确排斥项",
        }
        for field_name in result.missing_fields:
            lines.append(f"- {missing_label_map[field_name]}")

        lines.extend([
            "",
            "## 我下一步会追问你这些",
        ])
        for question in result.follow_up_questions:
            lines.append(f"- {question}")

        lines.extend([
            "",
            "## 你可以直接按这个格式回复我",
            "- 排位：",
            "- 科类（物理/历史）：",
            "- 家庭情况：",
            "- 偏好/不想学的方向：",
        ])
        return "\n".join(lines)

    lines = [
        "# 客户经理 Agent 结果",
        "",
        "## 标准化用户画像",
        *profile_lines,
        "",
        "## 状态",
        "- 信息已完整，可以继续交给数据侦察 Agent、策略 Agent 和规则校验 Agent。",
    ]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Gaokao intake manager for structured profile collection")
    parser.add_argument("--text", required=True, help="Raw user text for intake")
    parser.add_argument("--session-id", default="wechat_main", help="Session id for multi-turn memory")
    parser.add_argument("--json", action="store_true", help="Return structured JSON instead of markdown text")
    args = parser.parse_args()

    result = run_intake(args.text, session_id=args.session_id)
    if args.json:
        print(json.dumps(asdict(result), ensure_ascii=False, indent=2))
        return
    print(format_intake_response(result))


if __name__ == "__main__":
    main()
