import argparse
import os
from typing import Dict, List
from pathlib import Path

from agent_schema import StudentProfile
from data_scout import DataScoutAgent
from expert_supplement import pick_expert_cards, render_expert_cards
from rule_referee import RuleCheckResult, run_rule_referee
from strategy_agent import StrategyResult, is_science_major, prefers_science, run_strategy


def get_data_path() -> str:
    repo_data = Path(__file__).resolve().parents[1] / "data" / "gd_2024_rankings.json"
    candidate_paths = [
        str(repo_data),
        "/app/agent_project/data/gd_2024_rankings.json",
        "e:/Ke_Study/AI_Gaokao_BP_Expert/data/gd_2024_rankings.json",
    ]
    for path in candidate_paths:
        if os.path.exists(path):
            return path
    raise FileNotFoundError("未找到 gd_2024_rankings.json 数据文件。")


def format_option(option: Dict, label: str) -> str:
    return (
        f"- {label}：{option['college']}｜{option['major']}｜参考位次 {option['min_rank']}｜"
        f"就业档位 {option['employment_tier']}｜选科要求 {option['subject_req']}"
    )


def build_profile(
    rank: int,
    group: str,
    family: str,
    prefs: str,
    raw_text: str = "",
    mobility_preference: str = "",
    subject_combo: str = "",
) -> StudentProfile:
    derived_mobility = mobility_preference
    if not derived_mobility:
        if any(keyword in (prefs or "") for keyword in ["不可接受出省", "不接受出省", "不可出省", "不能出省", "不可以出省", "只接受省内", "只留广东", "只能在广东", "只能留广东", "留广东", "省内"]):
            derived_mobility = "prefer_in_province"
        elif "出省" in (prefs or ""):
            derived_mobility = "accept_outside"
    return StudentProfile(
        province="广东",
        rank=rank,
        group=group,
        family=family,
        prefs=prefs,
        mobility_preference=derived_mobility,
        subject_combo=subject_combo or ("物理" if group == "phys" else "历史" if group == "hist" else ""),
        raw_text=raw_text,
    )


def format_candidate_preview(bucket_name: str, options: List[Dict], preview_size: int = 2) -> List[str]:
    label_map = {
        "Chong (Aggressive)": "冲",
        "Wen (Stable)": "稳",
        "Bao (Guaranteed)": "保",
    }
    if not options:
        return [f"- {label_map.get(bucket_name, bucket_name)}层：当前没有命中候选。"]
    lines = [f"- {label_map.get(bucket_name, bucket_name)}层候选数：{len(options)}"]
    for option in options[:preview_size]:
        lines.append(format_option(option, label_map.get(bucket_name, bucket_name)))
    return lines


def format_strategy_section(strategy_result: StrategyResult) -> List[str]:
    lines = [
        "## 策略 Agent 输出",
    ]
    for note in strategy_result.strategic_notes:
        lines.append(f"- {note}")

    lines.extend([
        "",
        "### Ban 清单",
    ])
    if strategy_result.ban_list:
        for item in strategy_result.ban_list:
            option = item["option"]
            lines.append(f"- 谨慎：{option['college']}｜{option['major']}｜原因：{item['reason']}")
    else:
        lines.append("- 当前样本里没有明显高风险专业命中，但仍要警惕调剂和城市机会不足。")

    lines.extend([
        "",
        "### 初版冲稳保推荐",
    ])
    for bucket_name, picks in strategy_result.picks.items():
        bucket_label = {"Chong (Aggressive)": "冲", "Wen (Stable)": "稳", "Bao (Guaranteed)": "保"}.get(bucket_name, bucket_name)
        if not picks:
            lines.append(f"- {bucket_label}层：暂无推荐。")
            continue
        lines.append(f"- {bucket_label}层：")
        for option in picks:
            lines.append(format_option(option, bucket_label))
    return lines


def format_rule_section(rule_result: RuleCheckResult) -> List[str]:
    status_label = {
        "passed": "通过",
        "warning": "通过但有提醒",
        "corrected": "已自动纠偏",
        "passed_with_warnings": "通过且伴随提醒",
    }.get(rule_result.status, rule_result.status)

    lines = [
        "## 规则校验 Agent 输出",
        f"- 校验状态：{status_label}",
    ]
    if rule_result.errors:
        lines.append("- 拦截记录：")
        for item in rule_result.errors:
            lines.append(f"  {item}")
    if rule_result.replacements:
        lines.append("- 自动补位：")
        for item in rule_result.replacements:
            lines.append(f"  {item}")
    if rule_result.warnings:
        lines.append("- 风险提醒：")
        for item in rule_result.warnings:
            lines.append(f"  {item}")
    if rule_result.risk_alerts:
        lines.append("- 二次提示：")
        for item in rule_result.risk_alerts:
            lines.append(f"  {item}")
    return lines


def build_scope_notes(profile: StudentProfile) -> List[str]:
    notes = [
        "- 本轮自动推荐基于广东 2024 本地样本库生成，不代表全国实时录取数据库。",
        "- 内部沟通记录展示的是工作流审计摘要，不是源码执行日志。",
    ]
    if profile.mobility_preference == "accept_outside":
        notes.append("- 你已明确接受出省，但省外院校不会混入本轮自动结果；如需扩展外省，会单独标注为人工专家补充判断。")
    if profile.rank is not None and profile.rank <= 2000:
        notes.append("- 你属于顶尖位次，系统已启用顶尖位次分层，避免本地样本库上限导致冲层空缺。")
    return notes


def build_next_steps(profile: StudentProfile) -> List[str]:
    steps = []
    if profile.group == "phys" and profile.subject_combo in ["", "物理"]:
        steps.append("- 如果你愿意继续细化，下一条最值得补的是具体选科组合，例如物化、物生或物化生。")
    if not profile.mobility_preference:
        steps.append("- 继续补充你更偏省内还是接受出省，我可以据此调整下一轮策略。")
    if "稳定" not in profile.family and "体制" not in profile.family:
        steps.append("- 继续告诉我你更看重就业上限还是稳定性，我会调整电气、计算机、医学等方向的权重。")
    steps.append("- 如果你担心调剂风险，我下一轮可以直接给你做“可接受专业清单”和“绝不接受专业清单”。")
    steps.append("- 如果你要扩展到全国院校，我会把那部分明确标成“人工专家补充判断”，不和本轮自动结果混写。")
    steps.append("- 如果你想单独看库外知识卡，可以直接让我展示“人工专家补充判断卡片”。")
    return steps


def build_report(
    rank: int,
    group: str,
    family: str,
    prefs: str,
    raw_text: str = "",
    mobility_preference: str = "",
    subject_combo: str = "",
) -> str:
    profile = build_profile(
        rank,
        group,
        family,
        prefs,
        raw_text=raw_text,
        mobility_preference=mobility_preference,
        subject_combo=subject_combo,
    )
    scout = DataScoutAgent(get_data_path())
    results = scout.scout_options(rank, group)
    strategy_result = run_strategy(profile, results)
    rule_result = run_rule_referee(profile, strategy_result)
    expert_cards = pick_expert_cards(profile, user_text=raw_text or prefs)
    subject_label = "物理类" if group == "phys" else "历史类"
    science_approved_count = sum(
        1
        for bucket in rule_result.approved_picks.values()
        for option in bucket
        if is_science_major(option["major"])
    )

    lines = [
        "# 高考志愿 Multi-Agent 决策报告",
        "",
        "## 客户经理 Agent 输出",
        f"- 省份：广东",
        f"- 排位：{rank}",
        f"- 科类：{subject_label}",
        f"- 流动偏好：{'接受出省' if profile.mobility_preference == 'accept_outside' else '省内优先' if profile.mobility_preference == 'prefer_in_province' else '未明确'}",
        f"- 选科组合：{profile.subject_combo or '仅识别到科类，未识别到更细选科组合'}",
        f"- 家庭情况：{family or '未提供'}",
        f"- 偏好：{prefs or '未提供'}",
        "",
        "## 数据侦察 Agent 输出",
    ]

    for bucket_name, options in results.items():
        lines.extend(format_candidate_preview(bucket_name, options))

    lines.extend([""])
    lines.extend(format_strategy_section(strategy_result))
    lines.extend([""])
    lines.extend(format_rule_section(rule_result))
    lines.extend([
        "",
        "## 系统边界说明",
    ])
    lines.extend(build_scope_notes(profile))
    if expert_cards:
        lines.extend([
            "",
            render_expert_cards(profile, user_text=raw_text or prefs),
        ])

    lines.extend([
        "",
        "## 最终冲稳保方案",
    ])
    for bucket_name, picks in rule_result.approved_picks.items():
        bucket_label = {"Chong (Aggressive)": "冲", "Wen (Stable)": "稳", "Bao (Guaranteed)": "保"}.get(bucket_name, bucket_name)
        if not picks:
            lines.append(f"- {bucket_label}层：当前无通过校验的推荐。")
            continue
        for item in picks:
            lines.append(format_option(item, bucket_label))

    lines.extend([
        "",
        "## 家庭与就业建议",
    ])
    for item in strategy_result.family_advice:
        lines.append(f"- {item}")
    if prefers_science(profile) and science_approved_count == 0:
        lines.append("- 你明确偏理学，但当前自动结果里没有足够纯理学候选；这更像样本覆盖不足，不等于平台更高的理学路线不值得选。")

    lines.extend([
        "",
        "## 下一步建议",
    ])
    lines.extend(build_next_steps(profile))

    return "\n".join(lines)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate a Chinese Gaokao BP report")
    parser.add_argument("--rank", type=int, required=True, help="Student provincial rank")
    parser.add_argument("--group", type=str, choices=["phys", "hist"], required=True, help="Subject group")
    parser.add_argument("--family", type=str, default="", help="Family situation")
    parser.add_argument("--prefs", type=str, default="", help="Student preferences")
    args = parser.parse_args()

    print(build_report(args.rank, args.group, args.family, args.prefs))
