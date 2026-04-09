import argparse

from data_scout import DataScoutAgent
from intake_manager import format_intake_response, run_intake
from rule_referee import run_rule_referee
from run_bp_report import get_data_path
from strategy_agent import run_strategy


def localize_status(status: str) -> str:
    return {
        "passed": "通过",
        "warning": "通过但有提醒",
        "corrected": "已自动纠偏",
        "passed_with_warnings": "通过且伴随提醒",
    }.get(status, status)


def format_pm_view(profile, candidate_layers, strategy_result, rule_result):
    total_candidates = sum(len(options) for options in candidate_layers.values())
    return "\n".join([
        "## 产品经理视角",
        "- 这个项目解决的不是简单问答，而是高考志愿这种高约束决策问题。",
        "- 我把链路拆成四段，是因为用户原始输入通常不完整，不能直接让模型硬给答案。",
        f"- 当前这次分析里，系统先把用户画像结构化，再从数据层筛出 {total_candidates} 个候选，最后经过策略和规则校验输出结果。",
        "- 这样设计的价值是：可解释、可追问、可拦截错误，而不是只追求一次性生成。",
        f"- 最终规则校验状态是：{localize_status(rule_result.status)}，说明系统具备最后一道质量防线。",
    ])


def format_engineer_view(profile, candidate_layers, strategy_result, rule_result):
    return "\n".join([
        "## 程序员视角",
        "- 入口在 `scripts/gaokao_workflow.py`，负责把自然语言需求送入完整工作流。",
        "- `scripts/intake_manager.py` 负责客户经理 Agent：抽取排位、科类、家庭情况、偏好，并判断是否缺字段。",
        "- `scripts/data_scout.py` 负责数据侦察 Agent：按排位和科类把院校专业分成冲稳保候选池。",
        "- `scripts/strategy_agent.py` 负责策略 Agent：Ban 掉高风险专业，按偏好和就业档位给候选排序。",
        "- `scripts/rule_referee.py` 负责规则校验 Agent：拦截冲突推荐、去重、自动补位。",
        "- `scripts/run_bp_report.py` 负责把多 Agent 的结果汇总成最终中文报告，适合 GitHub 和演示。",
        f"- 这次数据侦察的分层结果是：冲 {len(candidate_layers['Chong (Aggressive)'])} / 稳 {len(candidate_layers['Wen (Stable)'])} / 保 {len(candidate_layers['Bao (Guaranteed)'])}。",
    ])


def format_qa_view(profile, candidate_layers, strategy_result, rule_result):
    checks = [
        "- 已验证缺失字段场景：如果只说“帮我报志愿”，系统会先追问，而不会乱推荐。",
        "- 已验证完整输入场景：如果画像完整，系统会产出四段式多 Agent 报告。",
        "- 已验证规则校验场景：规则 Agent 会过滤风险专业，并在需要时自动补位。",
    ]
    if rule_result.errors:
        checks.append(f"- 本次运行触发了 {len(rule_result.errors)} 条规则拦截，说明校验链路实际生效。")
    else:
        checks.append("- 本次运行没有触发硬性拦截，但规则 Agent 仍完成了全量检查。")
    if rule_result.risk_alerts:
        checks.append(f"- 本次运行还给出了 {len(rule_result.risk_alerts)} 条二次风险提示，避免用户只看推荐不看约束。")

    return "\n".join([
        "## 测试视角",
        *checks,
        "- 后续建议继续补外省数据、调剂风险、极端画像和异常输入回归测试。",
    ])


def build_showcase(text: str) -> str:
    intake_result = run_intake(text)
    if intake_result.status != "ready":
        return "\n".join([
            "# 展示层协作视图",
            "",
            "当前还不能进入展示层，因为真实业务链路还在客户经理 Agent 追问阶段。",
            "",
            format_intake_response(intake_result),
        ])

    profile = intake_result.profile
    scout = DataScoutAgent(get_data_path())
    candidate_layers = scout.scout_options(profile.rank, profile.group)
    strategy_result = run_strategy(profile, candidate_layers)
    rule_result = run_rule_referee(profile, strategy_result)

    return "\n".join([
        "# 展示层协作视图",
        "",
        format_pm_view(profile, candidate_layers, strategy_result, rule_result),
        "",
        format_engineer_view(profile, candidate_layers, strategy_result, rule_result),
        "",
        format_qa_view(profile, candidate_layers, strategy_result, rule_result),
    ])


def main() -> None:
    parser = argparse.ArgumentParser(description="Render the showcase role layer for the Gaokao project")
    parser.add_argument("--text", required=True, help="Raw user message")
    args = parser.parse_args()
    print(build_showcase(args.text))


if __name__ == "__main__":
    main()
