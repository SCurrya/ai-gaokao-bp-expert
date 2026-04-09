import re
from typing import Dict, List, Set, Tuple

from agent_schema import RuleCheckResult, StrategyResult, StudentProfile
from strategy_agent import is_risky, score_option


BUCKET_LABELS = {
    "Chong (Aggressive)": "冲",
    "Wen (Stable)": "稳",
    "Bao (Guaranteed)": "保",
}


def get_selected_subjects(profile: StudentProfile) -> Set[str]:
    combo = profile.subject_combo or ""
    if combo == "物理+化学+生物":
        return {"物理", "化学", "生物"}
    if combo == "物理+化学":
        return {"物理", "化学"}
    if combo == "物理+生物":
        return {"物理", "生物"}
    if combo == "历史+政治+地理":
        return {"历史", "政治", "地理"}
    if combo == "历史":
        return {"历史"}
    if profile.group == "phys":
        return {"物理"}
    if profile.group == "hist":
        return {"历史"}
    return set()


def subject_requirement_matches(profile: StudentProfile, subject_req: str) -> Tuple[bool, str]:
    subject_req = subject_req or "不限"
    if subject_req == "不限":
        return True, ""

    selected_subjects = get_selected_subjects(profile)
    required_subjects = {item.strip() for item in subject_req.split("+") if item.strip()}

    if profile.group == "hist":
        if any(subject in required_subjects for subject in ["物理", "化学", "生物"]):
            return False, f"当前识别为历史类，不满足 {subject_req}"
        return True, ""

    if profile.group == "phys" and "物理" not in required_subjects:
        return False, f"当前识别为物理类，但要求为 {subject_req}"

    if required_subjects.issubset(selected_subjects):
        return True, ""

    if profile.group == "phys" and selected_subjects == {"物理"} and len(required_subjects) > 1:
        return False, f"未提供更细选科组合，暂时无法确认是否满足 {subject_req}"

    return False, f"选科组合 {profile.subject_combo or '未识别'} 不满足 {subject_req}"


def extract_avoid_terms(prefs: str) -> List[str]:
    if not prefs:
        return []

    terms = []
    for match in re.findall(r"(?:不想学|不想|不考虑|不要|排斥)([^；，。,!?\s]+)", prefs):
        cleaned = match.strip().lstrip("学")
        if not cleaned:
            continue
        for part in re.split(r"[、/和与]", cleaned):
            part = part.strip()
            if part and part not in terms:
                terms.append(part)
    return terms


def conflicts_with_avoid_terms(option: Dict, avoid_terms: List[str]) -> bool:
    return any(term in option["major"] for term in avoid_terms)


def validate_option(profile: StudentProfile, option: Dict, avoid_terms: List[str]) -> List[str]:
    reasons = []
    subject_passed, subject_reason = subject_requirement_matches(profile, option.get("subject_req", ""))
    if not subject_passed:
        reasons.append(subject_reason or "选科要求不匹配")
    if is_risky(option):
        reasons.append("命中高风险专业或低就业档位")
    if conflicts_with_avoid_terms(option, avoid_terms):
        reasons.append("与用户明确排斥项冲突")
    return reasons


def option_key(option: Dict) -> Tuple[str, str]:
    return option["college"], option["major"]


def find_replacements(
    bucket_name: str,
    strategy_result: StrategyResult,
    profile: StudentProfile,
    avoid_terms: List[str],
    used_keys: Set[Tuple[str, str]],
    target_count: int,
) -> List[Dict]:
    replacements = []
    for option in strategy_result.ranked_layers.get(bucket_name, []):
        key = option_key(option)
        if key in used_keys:
            continue
        if validate_option(profile, option, avoid_terms):
            continue
        if profile.prefs and score_option(option, profile) < 8:
            continue
        replacements.append(option)
        used_keys.add(key)
        if len(replacements) >= target_count:
            break
    return replacements


def build_risk_alerts(profile: StudentProfile, approved_picks: Dict[str, List[Dict]]) -> List[str]:
    alerts = []
    total_options = sum(len(options) for options in approved_picks.values())
    if total_options == 0:
        alerts.append("当前没有通过校验的推荐结果，说明输入约束太强或数据集暂时不够，需要人工复核。")
        return alerts

    if any(keyword in profile.family for keyword in ["稳定", "考公", "考编", "体制"]):
        stable_pool = approved_picks.get("Wen (Stable)", []) + approved_picks.get("Bao (Guaranteed)", [])
        if not any(item["employment_tier"] in ["S+", "S", "A", "B+"] for item in stable_pool):
            alerts.append("你强调稳定，但当前稳保层的高确定性专业不够强，建议继续往电气、自动化、医学、师范方向补筛。")

    if profile.mobility_preference == "prefer_in_province":
        alerts.append("你更偏省内，后续如果要进一步提分层次，可能需要权衡是否开放部分外省机会。")
    if profile.mobility_preference == "accept_outside":
        alerts.append("你已接受出省，但当前自动候选仍限于广东样本库；如果要纳入外省高校，需要单独启用人工专家补充判断。")
    if profile.group == "phys" and get_selected_subjects(profile) == {"物理"}:
        alerts.append("你目前只提供了物理类，没有补充物化/物生/物化生；凡是需要化学或生物的专业，系统都会先从自动推荐里剔除。")

    return alerts


def run_rule_referee(profile: StudentProfile, strategy_result: StrategyResult) -> RuleCheckResult:
    avoid_terms = extract_avoid_terms(profile.prefs)
    approved_picks = {bucket_name: [] for bucket_name in strategy_result.picks}
    warnings = []
    errors = []
    replacements_log = []
    used_keys: Set[Tuple[str, str]] = set()

    for bucket_name, selected_options in strategy_result.picks.items():
        for option in selected_options:
            key = option_key(option)
            if key in used_keys:
                warnings.append(f"{BUCKET_LABELS.get(bucket_name, bucket_name)}层出现重复专业，已自动去重：{option['college']}｜{option['major']}")
                continue

            reasons = validate_option(profile, option, avoid_terms)
            if reasons:
                errors.append(f"{BUCKET_LABELS.get(bucket_name, bucket_name)}层候选被拦截：{option['college']}｜{option['major']}｜原因：{'；'.join(reasons)}")
                continue

            used_keys.add(key)
            approved_picks[bucket_name].append(option)

        missing_count = max(0, 3 - len(approved_picks[bucket_name]))
        if missing_count > 0:
            replacements = find_replacements(
                bucket_name=bucket_name,
                strategy_result=strategy_result,
                profile=profile,
                avoid_terms=avoid_terms,
                used_keys=used_keys,
                target_count=missing_count,
            )
            for option in replacements:
                approved_picks[bucket_name].append(option)
                replacements_log.append(f"{BUCKET_LABELS.get(bucket_name, bucket_name)}层补入候选：{option['college']}｜{option['major']}")

        if not approved_picks[bucket_name]:
            warnings.append(f"{BUCKET_LABELS.get(bucket_name, bucket_name)}层当前没有通过规则校验的方案，建议人工复核。")

    risk_alerts = build_risk_alerts(profile, approved_picks)
    status = "passed"
    if errors and warnings:
        status = "passed_with_warnings"
    elif errors:
        status = "corrected"
    elif warnings:
        status = "warning"

    return RuleCheckResult(
        status=status,
        approved_picks=approved_picks,
        warnings=warnings,
        errors=errors,
        replacements=replacements_log,
        risk_alerts=risk_alerts,
    )
