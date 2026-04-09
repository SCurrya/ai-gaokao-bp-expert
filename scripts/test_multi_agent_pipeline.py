from pathlib import Path

from intake_manager import format_intake_response, run_intake
from gaokao_workflow import run_workflow
from run_bp_report import build_report
from agent_boardroom import build_boardroom_transcript
from session_store import reset_session_state
from showcase_roles import build_showcase
from session_store import trace_md_file
from strategy_agent import run_strategy, score_option
from wechat_agent_router import route_message
from agent_schema import StudentProfile


def test_incomplete_intake():
    session_id = "test_incomplete_intake"
    reset_session_state(session_id)
    result = run_intake("帮我报志愿，我想学计算机", session_id=session_id)
    assert result.status == "needs_more_info"
    text = format_intake_response(result)
    assert "排位" in text
    assert "科类" in text


def test_full_report():
    report = build_report(
        rank=42000,
        group="phys",
        family="普通工薪家庭，看重稳定",
        prefs="想留广东，偏计算机，不想土木",
    )
    assert "客户经理 Agent 输出" in report
    assert "数据侦察 Agent 输出" in report
    assert "策略 Agent 输出" in report
    assert "规则校验 Agent 输出" in report
    assert "土木工程" not in report.split("## 最终冲稳保方案", 1)[-1]


def test_showcase_layer():
    showcase = build_showcase("我是广东物理类，排位42000，普通工薪家庭，想留广东，偏计算机，不想土木")
    assert "产品经理视角" in showcase
    assert "程序员视角" in showcase
    assert "测试视角" in showcase


def test_boardroom_layer():
    transcript = build_boardroom_transcript("我是广东物理类，排位42000，普通工薪家庭，想留广东，偏计算机，不想土木")
    assert "老板驾驶舱" in transcript
    assert "客户经理 Agent" in transcript
    assert "数据侦察 Agent" in transcript
    assert "策略 Agent" in transcript
    assert "规则校验 Agent" in transcript


def test_session_memory_and_trace():
    session_id = "test_memory_trace"
    reset_session_state(session_id)

    first = run_intake("我是广东物理类", session_id=session_id)
    assert first.status == "needs_more_info"

    second = run_intake("排位42000，普通工薪家庭，想留广东，偏计算机，不想土木", session_id=session_id)
    assert second.status == "ready"
    assert second.profile.group == "phys"
    assert second.profile.rank == 42000
    assert second.profile.mobility_preference == "prefer_in_province"

    payload = run_workflow("我想再确认一下这版方案", session_id=session_id)
    assert payload["status"] in ["needs_more_info", "ready"]
    assert payload["trace_steps"]

    trace_path = Path(trace_md_file(session_id))
    assert trace_path.exists()
    content = trace_path.read_text(encoding="utf-8")
    assert "老板驾驶舱" in content
    assert "客户经理 Agent" in content
    assert "Agent 时间线" in content
    assert "审计摘要" in content


def test_profile_override_and_subject_guard():
    session_id = "test_profile_override"
    reset_session_state(session_id)

    first = run_intake("我是广东物理类，排位1000，普通工薪家庭，想留广东，偏计算机，不想土木", session_id=session_id)
    assert first.status == "ready"
    assert first.profile.mobility_preference == "prefer_in_province"

    second = run_intake("可接受出省，不抗拒体制内，工科都能接受", session_id=session_id)
    assert second.status == "ready"
    assert second.profile.mobility_preference == "accept_outside"
    assert "想留广东" not in second.profile.prefs

    report = run_workflow("我想看这版自动方案", session_id=session_id)["report"]
    assert "人工专家补充判断" in report
    assert "呼吸临床医学" not in report.split("## 最终冲稳保方案", 1)[-1]


def test_science_preference_respects_platform():
    profile = StudentProfile(
        province="广东",
        rank=3000,
        group="phys",
        family="普通工薪家庭",
        prefs="偏理学",
        mobility_preference="accept_outside",
        subject_combo="物理+化学",
    )
    scut_science = {
        "college": "华南理工大学 (SCUT)",
        "major": "应用物理学",
        "tier": "985",
        "min_rank": 12000,
        "subject_req": "物理+化学",
        "employment_tier": "B+",
    }
    dgut_ai = {
        "college": "东莞理工学院 (DGUT)",
        "major": "人工智能",
        "tier": "Applied Provincial",
        "min_rank": 65000,
        "subject_req": "物理+化学",
        "employment_tier": "A",
    }
    assert score_option(scut_science, profile) > score_option(dgut_ai, profile)


def test_science_preference_reports_dataset_gap():
    profile = StudentProfile(
        province="广东",
        rank=3000,
        group="phys",
        family="普通工薪家庭",
        prefs="偏理学；不想土木",
        mobility_preference="accept_outside",
        subject_combo="物理+化学",
    )
    candidate_layers = {
        "Chong (Aggressive)": [],
        "Wen (Stable)": [
            {
                "college": "华南理工大学 (SCUT)",
                "major": "软件工程",
                "tier": "985",
                "min_rank": 8000,
                "subject_req": "物理+化学",
                "employment_tier": "S",
            }
        ],
        "Bao (Guaranteed)": [
            {
                "college": "东莞理工学院 (DGUT)",
                "major": "人工智能",
                "tier": "Applied Provincial",
                "min_rank": 65000,
                "subject_req": "物理+化学",
                "employment_tier": "A",
            }
        ],
    }
    result = run_strategy(profile, candidate_layers)
    assert any("纯理学专业覆盖不足" in note for note in result.strategic_notes)


def test_negative_mobility_is_parsed_correctly():
    session_id = "test_negative_mobility"
    reset_session_state(session_id)
    result = run_intake("我是广东物理化学，排位5000，普通工薪家庭，偏理学，不想土木，不可接受出省", session_id=session_id)
    assert result.status == "ready"
    assert result.profile.mobility_preference == "prefer_in_province"


def test_expert_supplement_card_section():
    report = build_report(
        rank=5000,
        group="phys",
        family="普通工薪家庭",
        prefs="偏理学；不想土木",
        raw_text="我是广东物理化学，排位5000，普通工薪家庭，偏理学，不想土木，不可接受出省",
        mobility_preference="prefer_in_province",
        subject_combo="物理+化学",
    )
    assert "## 人工专家补充判断卡片" in report
    assert "华南理工大学 (SCUT)｜数学与应用数学" in report


def test_wechat_router_trace_flow():
    session_id = "test_wechat_router"
    reset_session_state(session_id)

    first_response = route_message(
        "我是广东物理类，排位42000，普通工薪家庭，想留广东，偏计算机，不想土木",
        session_id=session_id,
    )
    assert "高考志愿 Multi-Agent 决策报告" in first_response
    assert "给我看内部沟通记录" in first_response

    trace_response = route_message("给我看内部沟通记录", session_id=session_id)
    assert "内部协作时间线" in trace_response
    assert "客户经理 Agent" in trace_response

    boardroom_response = route_message("给我看老板驾驶舱", session_id=session_id)
    assert "老板驾驶舱" in boardroom_response
    assert "策略 Agent" in boardroom_response

    strategy_response = route_message("我想看 Step 4 策略 Agent 输出", session_id=session_id)
    assert "策略 Agent 的真实输出摘录" in strategy_response
    assert "审计摘要" in strategy_response

    supplement_response = route_message("给我看人工专家补充判断卡片", session_id=session_id)
    assert "人工专家补充判断卡片" in supplement_response


def main():
    test_incomplete_intake()
    test_full_report()
    test_showcase_layer()
    test_boardroom_layer()
    test_session_memory_and_trace()
    test_profile_override_and_subject_guard()
    test_science_preference_respects_platform()
    test_science_preference_reports_dataset_gap()
    test_negative_mobility_is_parsed_correctly()
    test_expert_supplement_card_section()
    test_wechat_router_trace_flow()
    print("ALL_TESTS_PASSED")


if __name__ == "__main__":
    main()
