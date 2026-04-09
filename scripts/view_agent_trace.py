import argparse
import json
from pathlib import Path

from session_store import normalize_session_id, trace_jsonl_file, trace_md_file


def load_latest_payload(path: Path):
    if not path.exists():
        return None

    latest_line = ""
    with path.open("r", encoding="utf-8") as file:
        for line in file:
            if line.strip():
                latest_line = line.strip()

    if not latest_line:
        return None
    return json.loads(latest_line)


def format_timeline(payload) -> str:
    steps = payload.get("trace_steps", [])
    lines = [
        "# 内部协作时间线",
        "",
        f"- session_id: {payload.get('session_id', '')}",
        f"- timestamp: {payload.get('timestamp', '')}",
        "- 说明：这里展示的是最近一次 workflow 的审计摘要，不是源码执行日志。",
        "",
    ]
    if not steps:
        lines.append("- 当前 trace 里还没有结构化 timeline。")
        return "\n".join(lines)

    for item in steps:
        lines.append(f"{item.get('step', '?')}. {item.get('actor', '未知角色')}：{item.get('summary', '')}")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="View saved multi-agent trace files")
    parser.add_argument("--session-id", default="wechat_main", help="Session id to inspect")
    parser.add_argument("--mode", choices=["md", "jsonl", "timeline"], default="md", help="Which trace file to print")
    args = parser.parse_args()

    session_id = normalize_session_id(args.session_id)
    path: Path = trace_md_file(session_id) if args.mode == "md" else trace_jsonl_file(session_id)

    if not path.exists():
        print(f"未找到 trace 文件：{path}")
        return

    if args.mode == "timeline":
        payload = load_latest_payload(path)
        if payload is None:
            print(f"trace 文件为空：{path}")
            return
        print(format_timeline(payload))
        return

    with path.open("r", encoding="utf-8") as file:
        print(file.read())


if __name__ == "__main__":
    main()
