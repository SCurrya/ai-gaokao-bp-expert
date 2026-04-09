import json
import os
import re
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List

from agent_schema import StudentProfile


ROOT_DIR = Path(__file__).resolve().parent.parent
RUNTIME_DIR = Path(os.environ.get("GAOKAO_RUNTIME_DIR", str(ROOT_DIR / "runtime"))).resolve()
SESSION_DIR = RUNTIME_DIR / "session_memory"
TRACE_DIR = RUNTIME_DIR / "agent_traces"


def ensure_runtime_dirs() -> None:
    SESSION_DIR.mkdir(parents=True, exist_ok=True)
    TRACE_DIR.mkdir(parents=True, exist_ok=True)


def normalize_session_id(session_id: str) -> str:
    raw = (session_id or "wechat_main").strip().lower()
    normalized = re.sub(r"[^a-z0-9_-]+", "_", raw)
    return normalized or "wechat_main"


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def session_file(session_id: str) -> Path:
    return SESSION_DIR / f"{normalize_session_id(session_id)}.json"


def trace_jsonl_file(session_id: str) -> Path:
    return TRACE_DIR / f"{normalize_session_id(session_id)}.jsonl"


def trace_md_file(session_id: str) -> Path:
    return TRACE_DIR / f"{normalize_session_id(session_id)}_latest.md"


def load_session_state(session_id: str) -> Dict:
    ensure_runtime_dirs()
    path = session_file(session_id)
    if not path.exists():
        return {
            "session_id": normalize_session_id(session_id),
            "turn_count": 0,
            "profile": asdict(StudentProfile()),
            "history": [],
            "updated_at": "",
        }
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def build_profile_from_dict(payload: Dict) -> StudentProfile:
    return StudentProfile(
        province=payload.get("province", "广东"),
        rank=payload.get("rank"),
        group=payload.get("group"),
        family=clean_family_labels(payload.get("family", "")),
        prefs=clean_pref_chunks(payload.get("prefs", "")),
        mobility_preference=payload.get("mobility_preference", ""),
        subject_combo=payload.get("subject_combo", ""),
        unsupported_province=payload.get("unsupported_province", ""),
        raw_text=payload.get("raw_text", ""),
    )


def merge_labels(current_value: str, new_value: str, delimiter: str) -> str:
    items: List[str] = []
    for chunk in [current_value, new_value]:
        if not chunk:
            continue
        for part in chunk.split(delimiter):
            clean = part.strip()
            if clean and clean not in items:
                items.append(clean)
    return delimiter.join(items)


def clean_family_labels(value: str) -> str:
    if not value:
        return ""
    cleaned_parts: List[str] = []
    dropped_labels = {"接受出省", "倾向省内"}
    for part in value.split("，"):
        clean = part.strip()
        if not clean or clean in dropped_labels:
            continue
        if clean not in cleaned_parts:
            cleaned_parts.append(clean)
    return "，".join(cleaned_parts)


def clean_pref_chunks(value: str) -> str:
    if not value:
        return ""
    cleaned_parts: List[str] = []
    mobility_keywords = ["留广东", "省内", "出省", "外省", "广东优先"]
    for part in value.split("；"):
        clean = part.strip()
        if not clean:
            continue
        if any(keyword in clean for keyword in mobility_keywords):
            continue
        if clean not in cleaned_parts:
            cleaned_parts.append(clean)
    return "；".join(cleaned_parts)


def pick_subject_combo(previous_value: str, latest_value: str) -> str:
    specificity_order = {
        "": 0,
        "物理": 1,
        "历史": 1,
        "物理+化学": 2,
        "物理+生物": 2,
        "历史+政治+地理": 3,
        "物理+化学+生物": 3,
    }
    if specificity_order.get(latest_value, 0) >= specificity_order.get(previous_value, 0):
        return latest_value or previous_value
    return previous_value


def merge_profiles(previous: StudentProfile, latest: StudentProfile) -> StudentProfile:
    merged = StudentProfile(
        province=latest.province or previous.province,
        rank=latest.rank if latest.rank is not None else previous.rank,
        group=latest.group or previous.group,
        family=merge_labels(clean_family_labels(previous.family), clean_family_labels(latest.family), "，"),
        prefs=merge_labels(clean_pref_chunks(previous.prefs), clean_pref_chunks(latest.prefs), "；"),
        mobility_preference=latest.mobility_preference or previous.mobility_preference,
        subject_combo=pick_subject_combo(previous.subject_combo, latest.subject_combo),
        unsupported_province=latest.unsupported_province or previous.unsupported_province,
        raw_text=latest.raw_text or previous.raw_text,
    )
    if merged.province != "广东":
        merged.unsupported_province = merged.province
    return merged


def save_session_state(session_id: str, profile: StudentProfile, user_text: str, status: str, missing_fields: List[str]) -> Dict:
    ensure_runtime_dirs()
    current = load_session_state(session_id)
    current["turn_count"] = int(current.get("turn_count", 0)) + 1
    current["profile"] = asdict(profile)
    current["updated_at"] = now_iso()
    current.setdefault("history", [])
    current["history"].append({
        "turn": current["turn_count"],
        "user_text": user_text,
        "status": status,
        "missing_fields": missing_fields,
        "updated_at": current["updated_at"],
    })
    path = session_file(session_id)
    with path.open("w", encoding="utf-8") as file:
        json.dump(current, file, ensure_ascii=False, indent=2)
    return current


def reset_session_state(session_id: str) -> None:
    path = session_file(session_id)
    if path.exists():
        path.unlink()


def append_trace(session_id: str, payload: Dict) -> None:
    ensure_runtime_dirs()
    jsonl_path = trace_jsonl_file(session_id)
    with jsonl_path.open("a", encoding="utf-8") as file:
        file.write(json.dumps(payload, ensure_ascii=False) + "\n")


def write_latest_trace_markdown(session_id: str, markdown_text: str) -> None:
    ensure_runtime_dirs()
    path = trace_md_file(session_id)
    with path.open("w", encoding="utf-8") as file:
        file.write(markdown_text)
