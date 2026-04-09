import argparse

from data_scout import DataScoutAgent
from expert_supplement import pick_expert_cards
from intake_manager import format_intake_response, run_intake
from rule_referee import run_rule_referee
from run_bp_report import get_data_path
from strategy_agent import run_strategy


def localize_rule_status(status: str) -> str:
    return {
        "passed": "通过",
        "warning": "通过但有提醒",
        "corrected": "已自动纠偏",
        "passed_with_warnings": "通过且伴随提醒",
    }.get(status, status)


def build_boardroom_transcript(user_text: str, session_id: str = "wechat_main", intake_result=None) -> str:
    if intake_result is None:
        intake_result = run_intake(user_text, session_id=session_id)
    if intake_result.status != "ready":
        return "\n".join([
            "# 老板驾驶舱",
            "",
            "老板：先别给我方案，先确认这个用户画像是不是完整。",
            "客户经理 Agent：收到，我先做 intake。",
            "",
            format_intake_response(intake_result),
            "",
            "老板结论：信息还不够，先补排位、科类、家庭情况和偏好，再继续开会。",
        ])

    profile = intake_result.profile
    scout = DataScoutAgent(get_data_path())
    candidate_layers = scout.scout_options(profile.rank, profile.group)
    strategy_result = run_strategy(profile, candidate_layers)
    rule_result = run_rule_referee(profile, strategy_result)
    expert_cards = pick_expert_cards(profile, user_text=profile.raw_text)

    approved_total = sum(len(items) for items in rule_result.approved_picks.values())
    ban_total = len(strategy_result.ban_list)

    lines = [
        "# 老板驾驶舱",
        "",
        "老板：今天这位考生的案子，按公司流程做一次内部会审。",
        "",
        "客户经理 Agent：",
        f"- 用户画像已经结构化完成，省份 {profile.province}，排位 {profile.rank}，科类 {'物理类' if profile.group == 'phys' else '历史类'}。",
        f"- 流动偏好：{'接受出省' if profile.mobility_preference == 'accept_outside' else '省内优先' if profile.mobility_preference == 'prefer_in_province' else '未明确'}。",
        f"- 选科组合：{profile.subject_combo or '仅识别到科类，未识别到更细选科组合'}。",
        f"- 家庭情况：{profile.family or '未提供'}。",
        f"- 偏好约束：{profile.prefs or '未提供'}。",
        "",
        "数据侦察 Agent：",
        f"- 已从广东本地样本库筛出候选池，冲 {len(candidate_layers['Chong (Aggressive)'])} 个，稳 {len(candidate_layers['Wen (Stable)'])} 个，保 {len(candidate_layers['Bao (Guaranteed)'])} 个。",
        "- 候选池已交给策略 Agent 进入 Ban/Pick 决策。",
        "",
        "策略 Agent：",
        f"- 本轮共 Ban 掉 {ban_total} 个高风险方向，主要集中在低就业档位或典型风险专业。",
        "- 已按就业兑现率、用户偏好和城市机会完成冲稳保排序。",
    ]

    for item in strategy_result.strategic_notes:
        lines.append(f"- {item}")

    lines.extend([
        "",
        "规则校验 Agent：",
        f"- 本轮校验状态：{localize_rule_status(rule_result.status)}。",
        f"- 最终通过校验的推荐共 {approved_total} 个。",
    ])
    if rule_result.errors:
        lines.append(f"- 拦截了 {len(rule_result.errors)} 条冲突推荐。")
    if rule_result.replacements:
        lines.append(f"- 自动补位 {len(rule_result.replacements)} 次，确保结果不断层。")
    if rule_result.risk_alerts:
        lines.append(f"- 额外追加 {len(rule_result.risk_alerts)} 条老板级风险提醒。")
    if expert_cards:
        lines.extend([
            "",
            "人工专家补充判断模块：",
            f"- 本轮额外命中 {len(expert_cards)} 张知识卡，这些卡片不会混入自动冲稳保排序。",
            "- 适合用来补齐库外专业、外省院校或样本覆盖不足的判断。",
        ])

    lines.extend([
        "",
        "老板：",
        "- 对外同步时，必须标明本轮结果来自广东本地样本库，不得伪装成全国实时录取库。",
        "- 内部 trace 继续保留为审计摘要，不要写成源码级执行日志。",
        "",
        "## 老板批示",
        "- 对外给用户：输出正式冲稳保方案和风险提示。",
        "- 对内给团队：继续补充用户是否接受调剂、是否能提供更细选科组合。",
        "- 对项目展示：内部沟通只展示真实可审计内容，不添加伪工具调用。",
    ])
    if profile.mobility_preference == "accept_outside":
        lines.insert(-3, "- 用户已明确接受出省，但省外院校判断必须单独标为人工专家补充，不与本轮自动候选混写。")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Render an internal boardroom transcript for the Gaokao agent team")
    parser.add_argument("--text", required=True, help="Raw user request")
    parser.add_argument("--session-id", default="wechat_main", help="Session id for multi-turn memory")
    args = parser.parse_args()
    print(build_boardroom_transcript(args.text, session_id=args.session_id))


if __name__ == "__main__":
    main()
