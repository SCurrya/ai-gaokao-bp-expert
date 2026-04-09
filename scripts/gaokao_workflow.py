import argparse
import json
from dataclasses import asdict

from agent_boardroom import build_boardroom_transcript
from expert_supplement import pick_expert_cards
from intake_manager import format_intake_response, run_intake
from run_bp_report import build_report
from session_store import append_trace, load_session_state, now_iso, normalize_session_id, trace_md_file, write_latest_trace_markdown


def build_trace_steps(user_text: str, intake_result, expert_card_count: int = 0) -> list:
    steps = [
        {
            "step": 1,
            "actor": "用户",
            "stage": "input",
            "summary": user_text,
        }
    ]

    if intake_result.status != "ready":
        missing_labels = {
            "rank": "排位",
            "group": "科类",
            "family": "家庭情况",
            "prefs": "偏好",
        }
        missing = [missing_labels.get(field, field) for field in intake_result.missing_fields]
        summary = "已识别部分画像，但还缺关键信息。"
        if missing:
            summary = f"已完成首轮 intake，但还缺：{'、'.join(missing)}。"
        steps.extend([
            {
                "step": 2,
                "actor": "客户经理 Agent",
                "stage": "intake",
                "summary": summary,
            },
            {
                "step": 3,
                "actor": "老板",
                "stage": "decision",
                "summary": "要求先补全画像，再进入数据侦察、策略和规则会审。",
            },
        ])
        return steps

    profile = intake_result.profile
    group_label = "物理类" if profile.group == "phys" else "历史类" if profile.group == "hist" else "未识别"
    mobility_label = {
        "accept_outside": "接受出省",
        "prefer_in_province": "省内优先",
    }.get(profile.mobility_preference, "未明确")
    steps.extend([
        {
            "step": 2,
            "actor": "客户经理 Agent",
            "stage": "intake",
            "summary": (
                f"已建档：{profile.province}，{group_label}，排位 {profile.rank}，"
                f"流动偏好 {mobility_label}，家庭情况 {profile.family or '未提供'}。"
            ),
        },
        {
            "step": 3,
            "actor": "数据侦察 Agent",
            "stage": "scouting",
            "summary": "已基于广东本地样本库按排位和科类筛出冲稳保候选池，准备进入 Ban/Pick。",
        },
        {
            "step": 4,
            "actor": "策略 Agent",
            "stage": "strategy",
            "summary": "已完成风险专业 Ban 和候选排序，形成冲稳保初版方案，并记录数据边界。",
        },
        {
            "step": 5,
            "actor": "规则校验 Agent",
            "stage": "validation",
            "summary": "已执行选科匹配、去重、纠偏和风险提醒，确认结果可交付。",
        },
    ])
    if expert_card_count > 0:
        steps.append({
            "step": 6,
            "actor": "人工专家补充判断模块",
            "stage": "supplement",
            "summary": f"已补充 {expert_card_count} 张库外知识卡，与自动结果分开展示。",
        })
        boss_step = 7
    else:
        boss_step = 6
    steps.append({
        "step": boss_step,
        "actor": "老板",
        "stage": "delivery",
        "summary": "批准对外同步方案，同时要求把 trace 保留为审计摘要，供后续复盘。",
    })
    return steps


def build_trace_markdown(session_id: str, user_text: str, intake_result, report_text: str, boardroom_text: str, trace_steps: list) -> str:
    session_state = load_session_state(session_id)
    lines = [
        "# Multi-Agent Trace",
        "",
        f"- session_id: {normalize_session_id(session_id)}",
        f"- updated_at: {now_iso()}",
        "",
        "## 用户原话",
        user_text,
        "",
        "## Trace 说明",
        "- 这里保存的是多 Agent 工作流审计摘要，不是源码执行日志，也不会伪装成逐文件工具调用记录。",
        "",
        "## Agent 时间线",
    ]
    for item in trace_steps:
        lines.append(f"- Step {item['step']} | {item['actor']} | {item['summary']}")

    lines.extend([
        "",
        "## 客户经理 Agent",
        format_intake_response(intake_result),
    ])
    if report_text:
        lines.extend([
            "",
            "## 业务链路结果",
            report_text,
        ])
    lines.extend([
        "",
        "## 老板驾驶舱",
        boardroom_text,
        "",
        "## 当前会话状态",
        json.dumps(session_state, ensure_ascii=False, indent=2),
    ])
    return "\n".join(lines)


def run_workflow(user_text: str, session_id: str = "wechat_main") -> dict:
    intake_result = run_intake(user_text, session_id=session_id)
    trace_payload = {
        "timestamp": now_iso(),
        "session_id": normalize_session_id(session_id),
        "user_text": user_text,
        "intake": asdict(intake_result),
    }

    if intake_result.status != "ready":
        trace_steps = build_trace_steps(user_text, intake_result)
        trace_payload["trace_steps"] = trace_steps
        boardroom_text = build_boardroom_transcript(user_text, session_id=session_id, intake_result=intake_result)
        trace_payload["boardroom"] = boardroom_text
        append_trace(session_id, trace_payload)
        write_latest_trace_markdown(session_id, build_trace_markdown(session_id, user_text, intake_result, "", boardroom_text, trace_steps))
        return {
            "status": intake_result.status,
            "session_id": normalize_session_id(session_id),
            "intake": asdict(intake_result),
            "boardroom": boardroom_text,
            "trace_file": str(trace_md_file(session_id)),
            "trace_steps": trace_steps,
            "rendered_response": format_intake_response(intake_result),
        }

    profile = intake_result.profile
    report = build_report(
        rank=profile.rank,
        group=profile.group,
        family=profile.family,
        prefs=profile.prefs,
        raw_text=profile.raw_text,
        mobility_preference=profile.mobility_preference,
        subject_combo=profile.subject_combo,
    )
    expert_card_count = len(pick_expert_cards(profile, user_text=profile.raw_text))
    trace_steps = build_trace_steps(user_text, intake_result, expert_card_count=expert_card_count)
    trace_payload["trace_steps"] = trace_steps
    boardroom_text = build_boardroom_transcript(user_text, session_id=session_id, intake_result=intake_result)
    trace_payload["report"] = report
    trace_payload["boardroom"] = boardroom_text
    append_trace(session_id, trace_payload)
    write_latest_trace_markdown(session_id, build_trace_markdown(session_id, user_text, intake_result, report, boardroom_text, trace_steps))
    return {
        "status": "ready",
        "session_id": normalize_session_id(session_id),
        "profile": asdict(profile),
        "report": report,
        "boardroom": boardroom_text,
        "trace_file": str(trace_md_file(session_id)),
        "trace_steps": trace_steps,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the full Gaokao multi-agent workflow")
    parser.add_argument("--text", required=True, help="Raw user message for the full workflow")
    parser.add_argument("--session-id", default="wechat_main", help="Session id for multi-turn memory")
    parser.add_argument("--json", action="store_true", help="Return workflow result as JSON")
    args = parser.parse_args()

    payload = run_workflow(args.text, session_id=args.session_id)

    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return

    if payload["status"] == "ready":
        print(payload["report"])
        return
    print(payload["rendered_response"])


if __name__ == "__main__":
    main()
