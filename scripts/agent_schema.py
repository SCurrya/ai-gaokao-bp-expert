from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class StudentProfile:
    province: str = "广东"
    rank: Optional[int] = None
    group: Optional[str] = None
    family: str = ""
    prefs: str = ""
    mobility_preference: str = ""
    subject_combo: str = ""
    unsupported_province: str = ""
    raw_text: str = ""


@dataclass
class IntakeResult:
    status: str
    profile: StudentProfile
    missing_fields: List[str] = field(default_factory=list)
    follow_up_questions: List[str] = field(default_factory=list)
    report: str = ""


@dataclass
class StrategyResult:
    profile: StudentProfile
    candidate_layers: Dict[str, List[Dict]]
    ranked_layers: Dict[str, List[Dict]]
    picks: Dict[str, List[Dict]]
    ban_list: List[Dict] = field(default_factory=list)
    family_advice: List[str] = field(default_factory=list)
    strategic_notes: List[str] = field(default_factory=list)


@dataclass
class RuleCheckResult:
    status: str
    approved_picks: Dict[str, List[Dict]]
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    replacements: List[str] = field(default_factory=list)
    risk_alerts: List[str] = field(default_factory=list)
