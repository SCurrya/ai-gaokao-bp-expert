from typing import Dict, List

from agent_schema import StrategyResult, StudentProfile


RISK_KEYWORDS = ["心理学", "海洋科学", "土木工程", "建筑学", "市场营销"]
SAFE_MAJORS = ["计算机", "软件", "电气", "自动化", "电子", "口腔", "临床", "师范", "人工智能", "网安"]
SCIENCE_MAJORS = ["数学", "物理", "化学", "生物", "统计", "天文", "地理科学", "基础医学"]
SCIENCE_ADJACENT_MAJORS = ["应用物理", "信息与计算科学", "材料", "集成电路", "电子信息"]
EMPLOYMENT_SCORES = {
    "S+": 9,
    "S": 8,
    "A": 6,
    "B+": 5,
    "B": 3,
    "C": 1,
    "D": 0,
}
COLLEGE_PLATFORM_SCORES = {
    "985/C9-ish": 5,
    "985": 4,
    "Double First Class": 3,
    "211": 3,
    "Top Provincial": 2,
    "Strong Tech Provincial": 2,
    "High Growth Provincial": 1,
    "Provincial Key": 1,
}


def is_risky(option: Dict) -> bool:
    major = option["major"]
    if option.get("employment_tier") in ["C", "D"]:
        return True
    return any(keyword in major for keyword in RISK_KEYWORDS)


def summarize_family_advice(family: str) -> List[str]:
    family = family or "普通家庭"
    advice = []
    if any(keyword in family for keyword in ["普通", "工薪", "一般"]):
        advice.append("家庭资源偏普通时，要优先看就业确定性、城市资源和考公兼容性，不要为听起来高级但兑现率低的方向买单。")
        advice.append("专业优先级建议高于学校光环，尤其要避免培养周期长、投入高但回报不稳定的专业。")
    if any(keyword in family for keyword in ["体制", "考公", "考编", "稳定"]):
        advice.append("如果家庭更看重稳定，优先考虑电气、自动化、医学、师范、计算机等更容易兼顾就业和考编的路径。")
    if not advice:
        advice.append("家庭条件和职业预期会直接影响志愿选择，建议把就业稳定性和地理位置一起纳入判断。")
    return advice


def employment_score(tier: str) -> int:
    return EMPLOYMENT_SCORES.get(tier, 2)


def is_science_major(major: str) -> bool:
    return any(keyword in major for keyword in SCIENCE_MAJORS)


def is_science_adjacent_major(major: str) -> bool:
    return any(keyword in major for keyword in SCIENCE_ADJACENT_MAJORS)


def prefers_science(profile: StudentProfile) -> bool:
    prefs = profile.prefs or ""
    return any(keyword in prefs for keyword in ["理学", "数学", "物理", "化学", "生物"])


def college_platform_score(option: Dict) -> int:
    tier = option.get("tier", "")
    return COLLEGE_PLATFORM_SCORES.get(tier, 0)


def score_option(option: Dict, profile: StudentProfile) -> int:
    score = employment_score(option["employment_tier"])
    major = option["major"]
    prefs = profile.prefs or ""
    family = profile.family or ""
    science_preference = prefers_science(profile)

    if any(keyword in major for keyword in SAFE_MAJORS):
        score += 4

    score += college_platform_score(option)

    if science_preference:
        if is_science_major(major):
            score += 6
            if college_platform_score(option) >= 3:
                score += 3
        elif is_science_adjacent_major(major):
            score += 2
        else:
            score -= 1

    if "计算机" in prefs or "软件" in prefs or "人工智能" in prefs or "编程" in prefs:
        if any(keyword in major for keyword in ["计算机", "软件", "人工智能", "网络空间安全", "集成电路"]):
            score += 4
    if "电气" in prefs or "电子" in prefs:
        if "电气" in major or "电子" in major:
            score += 3
    if "医学" in prefs or "临床" in prefs or "口腔" in prefs:
        if any(keyword in major for keyword in ["临床", "口腔", "医学"]):
            score += 4
    if "师范" in prefs and "师范" in major:
        score += 4

    if profile.mobility_preference == "prefer_in_province" or any(keyword in prefs for keyword in ["广东", "广州", "深圳"]):
        if "广州" in option["college"] or "深圳" in option["college"]:
            score += 2

    if any(keyword in family for keyword in ["稳定", "考公", "考编", "体制"]):
        if any(keyword in major for keyword in ["电气", "自动化", "师范", "医学", "计算机", "法学"]):
            score += 2

    return score


def build_ban_reason(option: Dict) -> str:
    if option.get("employment_tier") in ["C", "D"]:
        return f"就业档位 {option['employment_tier']}，风险较高。"
    if "土木工程" in option["major"]:
        return "土木方向周期承压，普通家庭要谨慎。"
    if "建筑学" in option["major"]:
        return "建筑方向培养长、投入高，当前回报不稳定。"
    if "心理学" in option["major"]:
        return "心理学对学历和后续深造要求高，就业兑现慢。"
    if "海洋科学" in option["major"]:
        return "专业听起来高级，但岗位面偏窄，就业弹性不足。"
    return "命中高风险关键词，建议谨慎。"


def rank_bucket_options(options: List[Dict], profile: StudentProfile) -> List[Dict]:
    valid_options = [item for item in options if not is_risky(item)]
    return sorted(
        valid_options,
        key=lambda item: (score_option(item, profile), employment_score(item["employment_tier"]), -item["min_rank"]),
        reverse=True,
    )


def build_strategic_notes(profile: StudentProfile) -> List[str]:
    notes = [
        "这不是简单查学校，而是一次 Ban/Pick 博弈：先排雷，再做冲稳保梯度配置。",
        "优先级顺序建议是：专业兑现率 > 城市机会 > 学校名气。",
    ]
    if any(keyword in profile.family for keyword in ["普通", "工薪", "一般"]):
        notes.append("对普通家庭来说，志愿更要看兑现率，而不是只看学校招牌。")
    if any(keyword in profile.prefs for keyword in ["计算机", "软件", "人工智能", "电子", "电气"]):
        notes.append("你的偏好和粤港澳大湾区的技术岗位趋势是同向的，可以适当向工科和技术方向集中。")
    if prefers_science(profile):
        notes.append("你明确偏理学时，系统会提高纯理学专业和高平台院校的权重，不会简单拿四非应用工科压过 985/211 理学。")
    if profile.rank is not None and profile.rank <= 2000:
        notes.append("你属于顶尖位次，系统已启用顶尖位次分层：样本库里最靠前的广东候选会优先进入冲刺池，避免出现空冲层。")
    if profile.mobility_preference == "accept_outside":
        notes.append("你已明确接受出省，但当前自动候选仍只基于广东样本库；省外院校需要作为下一轮人工专家补充判断，不能与本轮自动结果混写。")
    return notes


def run_strategy(profile: StudentProfile, candidate_layers: Dict[str, List[Dict]]) -> StrategyResult:
    strategic_notes = build_strategic_notes(profile)
    science_candidates = [
        option
        for bucket_options in candidate_layers.values()
        for option in bucket_options
        if is_science_major(option["major"])
    ]
    if prefers_science(profile) and not science_candidates:
        strategic_notes.append("当前广东本地样本库里纯理学专业覆盖不足，所以自动结果只能先给出理工相邻方向；这不代表 985 理学天然不如四非应用工科。")

    ranked_layers = {
        bucket_name: rank_bucket_options(bucket_options, profile)
        for bucket_name, bucket_options in candidate_layers.items()
    }
    picks = {
        bucket_name: ranked_layers[bucket_name][:3]
        for bucket_name in candidate_layers
    }

    ban_list = []
    for bucket_name, bucket_options in candidate_layers.items():
        for option in bucket_options:
            if is_risky(option):
                ban_list.append({
                    "bucket": bucket_name,
                    "option": option,
                    "reason": build_ban_reason(option),
                })

    return StrategyResult(
        profile=profile,
        candidate_layers=candidate_layers,
        ranked_layers=ranked_layers,
        picks=picks,
        ban_list=ban_list[:6],
        family_advice=summarize_family_advice(profile.family),
        strategic_notes=strategic_notes,
    )
