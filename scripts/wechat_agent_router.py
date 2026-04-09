import argparse
from pathlib import Path

from gaokao_workflow import run_workflow
from session_store import normalize_session_id, trace_jsonl_file, trace_md_file
from view_agent_trace import format_timeline, load_latest_payload


TRACE_KEYWORDS = [
    "内部沟通记录", "沟通记录", "trace", "时间线", "内部流转", "协作记录", "聊天记录",
    "执行记录", "运行记录", "过程记录", "agent记录", "agent trace",
]
FULL_TRACE_KEYWORDS = ["完整", "全文", "原文", "详细", "完整记录", "全部记录", "markdown", "md", "jsonl"]
BOARDROOM_KEYWORDS = ["老板驾驶舱", "老板视角", "内部会审", "会审", "员工汇报", "内部协作", "团队汇报"]
STRATEGY_DETAIL_KEYWORDS = ["策略 agent", "策略过程", "step 4", "step4", "ban/pick", "ban掉", "冲稳保排序"]
SUPPLEMENT_KEYWORDS = ["人工专家补充判断", "补充判断卡片", "专家补充卡片", "全国院校补充卡片", "补充卡片"]
INTRO_KEYWORDS = ["你是谁", "你能做什么", "介绍一下你自己", "怎么用", "你可以做什么"]
PROFILE_HINT_KEYWORDS = [
    "排位", "位次", "省排", "物理", "历史", "普通工薪", "工薪家庭", "留广东", "出省", "不想",
    "偏", "想学", "考公", "考编", "稳定",
]


def normalize_text(text: str) -> str:
    return (text or "").strip()


def contains_any(text: str, keywords) -> bool:
    lowered = text.lower()
    return any(keyword.lower() in lowered for keyword in keywords)


def has_profile_signal(text: str) -> bool:
    return contains_any(text, PROFILE_HINT_KEYWORDS)


def build_intro() -> str:
    return (
        "我是 AI 高考志愿 BP 专家，主要帮你做广东高考志愿的冲稳保分析、专业排雷、"
        "家庭约束判断、内部协作复盘和老板驾驶舱展示。当前自动结果基于广东本地样本库。\n\n"
        "你直接发自然语言给我就行，比如：\n"
        "1. 我是广东物理类，排位42000，普通工薪家庭，想留广东，偏计算机，不想土木\n"
        "2. 给我看老板驾驶舱\n"
        "3. 给我看内部沟通记录\n"
        "4. 给我看完整内部沟通记录"
    )


def load_latest_trace_content(session_id: str, mode: str) -> str:
    payload = load_latest_payload(trace_jsonl_file(session_id))
    if payload is None:
        return (
            "当前还没有可查看的内部沟通记录。\n"
            "你先发一条高考画像或志愿需求，我跑完 workflow 之后，再给你看内部 trace。"
        )

    if mode == "timeline":
        lines = [
            format_timeline(payload),
            "",
            "如果你还想看完整原文，可以继续发：给我看完整内部沟通记录",
        ]
        return "\n".join(lines)

    if mode == "jsonl":
        path = trace_jsonl_file(session_id)
    else:
        path = trace_md_file(session_id)

    if not path.exists():
        return f"找到 trace 元数据了，但文件不存在：{path}"

    return path.read_text(encoding="utf-8")


def load_latest_boardroom(session_id: str) -> str:
    payload = load_latest_payload(trace_jsonl_file(session_id))
    if payload is None:
        return (
            "当前还没有老板驾驶舱内容。\n"
            "你先把排位、科类、家庭情况和偏好发给我，我跑完一次完整 workflow 后就能给你看。"
        )

    boardroom = payload.get("boardroom", "").strip()
    if boardroom:
        return boardroom

    return (
        "当前这次会话还没生成老板驾驶舱内容。\n"
        "你可以先发一条高考分析需求，我会先完成 workflow，再把内部会审给你看。"
    )


def extract_section(report_text: str, header: str, next_header: str) -> str:
    if not report_text:
        return ""
    start = report_text.find(header)
    if start == -1:
        return ""
    end = report_text.find(next_header, start + len(header))
    if end == -1:
        end = len(report_text)
    return report_text[start:end].strip()


def load_strategy_detail(session_id: str) -> str:
    payload = load_latest_payload(trace_jsonl_file(session_id))
    if payload is None:
        return (
            "当前还没有可查看的策略 Agent 输出。\n"
            "你先发一条高考画像，我跑完 workflow 之后，再给你看真实的策略摘要。"
        )

    section = extract_section(payload.get("report", ""), "## 策略 Agent 输出", "## 规则校验 Agent 输出")
    if not section:
        return (
            "最近一次 workflow 里没有独立的策略 Agent 摘要可展示。\n"
            "你可以先重新发一条画像，我再为你生成一份最新的策略结果。"
        )

    lines = [
        "下面是最近一次自动 workflow 里，策略 Agent 的真实输出摘录。",
        "说明：这是审计摘要，不是源码级执行日志，也不是临时编造的工具调用过程。",
        "",
        section,
    ]
    return "\n".join(lines)


def load_supplement_cards(session_id: str) -> str:
    payload = load_latest_payload(trace_jsonl_file(session_id))
    if payload is None:
        return (
            "当前还没有可查看的人工专家补充判断卡片。\n"
            "你先发一条高考画像，我跑完 workflow 之后，再给你看补充卡片。"
        )

    section = extract_section(payload.get("report", ""), "## 人工专家补充判断卡片", "## 最终冲稳保方案")
    if not section:
        return (
            "最近一次 workflow 里没有命中人工专家补充判断卡片。\n"
            "你可以先发更明确的偏好，比如理学方向、外省倾向或具体学校专业，我再试一次。"
        )
    return section


def choose_trace_mode(text: str) -> str:
    lowered = text.lower()
    if "jsonl" in lowered:
        return "jsonl"
    if contains_any(text, FULL_TRACE_KEYWORDS):
        return "md"
    return "timeline"


def route_message(user_text: str, session_id: str = "wechat_main") -> str:
    text = normalize_text(user_text)
    normalized_session = normalize_session_id(session_id)

    if not text:
        return build_intro()

    if contains_any(text, INTRO_KEYWORDS):
        return build_intro()

    if contains_any(text, TRACE_KEYWORDS):
        if has_profile_signal(text):
            run_workflow(text, session_id=normalized_session)
        return load_latest_trace_content(normalized_session, choose_trace_mode(text))

    if contains_any(text, STRATEGY_DETAIL_KEYWORDS):
        if has_profile_signal(text):
            run_workflow(text, session_id=normalized_session)
        return load_strategy_detail(normalized_session)

    if contains_any(text, SUPPLEMENT_KEYWORDS):
        if has_profile_signal(text):
            run_workflow(text, session_id=normalized_session)
        return load_supplement_cards(normalized_session)

    if contains_any(text, BOARDROOM_KEYWORDS):
        if has_profile_signal(text):
            payload = run_workflow(text, session_id=normalized_session)
            return payload.get("boardroom") or load_latest_boardroom(normalized_session)
        return load_latest_boardroom(normalized_session)

    payload = run_workflow(text, session_id=normalized_session)
    if payload["status"] == "ready":
        lines = [
            payload["report"],
            "",
            "这份结果是基于广东本地样本库的自动决策结果。",
            "如果你要扩展外省院校，我会把那部分单独标成“人工专家补充判断”，不会和自动结果混写。",
            "",
            "如果你想继续看内部协作，可以直接再发：",
            "- 给我看老板驾驶舱",
            "- 给我看内部沟通记录",
            "- 我想看 Step 4 策略 Agent 输出",
            "- 给我看人工专家补充判断卡片",
        ]
        return "\n".join(lines)
    return payload["rendered_response"]


def main() -> None:
    parser = argparse.ArgumentParser(description="WeChat-friendly router for the AI Gaokao BP Expert")
    parser.add_argument("--text", required=True, help="Raw user message from WeChat or other NL channels")
    parser.add_argument("--session-id", default="wechat_main", help="Session id for multi-turn memory")
    args = parser.parse_args()

    print(route_message(args.text, session_id=args.session_id))


if __name__ == "__main__":
    main()
