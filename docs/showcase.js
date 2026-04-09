const SAMPLE_TEXT = "我是广东物理化学，排位5000，普通工薪家庭，偏理学，不想土木，不可接受出省";

const state = { dataset: null, expertCards: null };

const provinceCandidates = [
  "北京", "天津", "上海", "重庆", "河北", "山西", "辽宁", "吉林", "黑龙江",
  "江苏", "浙江", "安徽", "福建", "江西", "山东", "河南", "湖北", "湖南",
  "广东", "海南", "四川", "贵州", "云南", "陕西", "甘肃", "青海", "台湾",
  "内蒙古", "广西", "西藏", "宁夏", "新疆", "香港", "澳门",
];

const familyLabels = [
  ["普通工薪家庭", ["普通工薪", "工薪家庭", "普通家庭", "家里一般", "家庭一般", "条件一般"]],
  ["看重稳定", ["看重稳定", "想稳定", "求稳定", "考公", "考编", "体制内", "体制"]],
];

const mobilityPatterns = [
  ["prefer_in_province", ["不可接受出省", "不接受出省", "不可出省", "不能出省", "不可以出省", "只接受省内", "只留广东", "只能在广东", "只能留广东"]],
  ["accept_outside", ["接受出省", "可接受出省", "能出省", "可以出省", "外省也行", "不介意出省", "接受外省"]],
  ["prefer_in_province", ["留广东", "想留广东", "不想出省", "想留省内", "省内优先", "广东优先"]],
];

const preferencePatterns = [
  /(想留[^，。；,;!\n]+)/g,
  /(想去[^，。；,;!\n]+)/g,
  /(想学[^，。；,;!\n]+)/g,
  /(偏(?:向)?[^，。；,;!\n]+)/g,
  /(喜欢[^，。；,;!\n]+)/g,
  /(希望[^，。；,;!\n]+)/g,
  /(不想[^，。；,;!\n]+)/g,
  /(不考虑[^，。；,;!\n]+)/g,
  /(接受[^，。；,;!\n]+)/g,
  /(能接受[^，。；,;!\n]+)/g,
  /(只考虑[^，。；,;!\n]+)/g,
];

const riskKeywords = ["心理学", "海洋科学", "土木工程", "建筑学", "市场营销"];
const safeMajors = ["计算机", "软件", "电气", "自动化", "电子", "口腔", "临床", "师范", "人工智能", "网络空间安全", "集成电路"];
const scienceMajors = ["数学", "物理", "化学", "生物", "统计", "天文", "地理科学", "基础医学"];
const scienceAdjacentMajors = ["应用物理", "信息与计算科学", "材料", "集成电路", "电子信息"];
const employmentScores = { "S+": 9, "S": 8, "A": 6, "B+": 5, "B": 3, "C": 1, "D": 0 };
const collegePlatformScores = {
  "985/C9-ish": 5,
  "985": 4,
  "Double First Class": 3,
  "211": 3,
  "Top Provincial": 2,
  "Strong Tech Provincial": 2,
  "High Growth Provincial": 1,
  "Provincial Key": 1,
};

function $(id) {
  return document.getElementById(id);
}

function normalizeText(text) {
  return (text || "").replace(/\s+/g, " ").trim();
}

function parseRankValue(raw, useWan) {
  const clean = String(raw).replace(/,/g, "").trim();
  if (!clean) return null;
  const value = Number(clean);
  if (Number.isNaN(value)) return null;
  return useWan ? Math.round(value * 10000) : Math.round(value);
}

function extractRank(text) {
  const patterns = [
    [/(?:排位|位次|排名|省排|省位次)[^\d]{0,6}(\d+(?:\.\d+)?)\s*万/i, true],
    [/(?:排位|位次|排名|省排|省位次)[^\d]{0,6}(\d[\d,]*)/i, false],
    [/(\d+(?:\.\d+)?)\s*万\s*(?:名|位|排)/i, true],
    [/(\d[\d,]*)\s*(?:名|位|排)/i, false],
  ];
  for (const [pattern, useWan] of patterns) {
    const match = text.match(pattern);
    if (match) return parseRankValue(match[1], useWan);
  }
  return null;
}

function extractGroup(text) {
  const lower = text.toLowerCase();
  const histKeywords = ["历史", "政史地", "史政", "历政", "文科", "history", "hist"];
  const physKeywords = ["物理", "物化生", "物化", "物生", "理科", "physics", "phys"];
  if (histKeywords.some((keyword) => lower.includes(keyword.toLowerCase()))) return "hist";
  if (physKeywords.some((keyword) => lower.includes(keyword.toLowerCase()))) return "phys";
  return null;
}

function extractProvince(text) {
  for (const province of provinceCandidates) {
    if (text.includes(province)) return province;
  }
  return "广东";
}

function extractFamily(text) {
  const result = [];
  familyLabels.forEach(([label, keywords]) => {
    if (keywords.some((keyword) => text.includes(keyword))) result.push(label);
  });
  return [...new Set(result)].join("，");
}

function extractMobilityPreference(text) {
  for (const [label, keywords] of mobilityPatterns) {
    if (keywords.some((keyword) => text.includes(keyword))) return label;
  }
  return "";
}

function mobilityLabel(value) {
  return {
    accept_outside: "接受出省",
    prefer_in_province: "省内优先",
  }[value] || "未明确";
}

function extractSubjectCombo(text) {
  if (["物化生", "物理化学生物", "物理+化学+生物"].some((keyword) => text.includes(keyword))) return "物理+化学+生物";
  if (["物化", "物理化学", "物理+化学"].some((keyword) => text.includes(keyword))) return "物理+化学";
  if (["物生", "物理生物", "物理+生物"].some((keyword) => text.includes(keyword))) return "物理+生物";
  if (["史政地", "历史政治地理", "历史+政治+地理"].some((keyword) => text.includes(keyword))) return "历史+政治+地理";
  if (["历史", "政史地", "史政", "历政", "文科", "history", "hist"].some((keyword) => text.toLowerCase().includes(keyword.toLowerCase()))) return "历史";
  if (["物理", "物化生", "物化", "物生", "理科", "physics", "phys"].some((keyword) => text.toLowerCase().includes(keyword.toLowerCase()))) return "物理";
  return "";
}

function isMobilityPhrase(text) {
  const compact = text.replace(/\s+/g, "");
  return ["留广东", "省内", "出省", "外省", "广东优先"].some((keyword) => compact.includes(keyword));
}

function extractPrefs(text) {
  const hits = [];
  preferencePatterns.forEach((pattern) => {
    const matches = text.match(pattern) || [];
    matches.forEach((item) => {
      const cleaned = item.trim().replace(/^[ ：:;；，。,.!?！？]+|[ ：:;；，。,.!?！？]+$/g, "");
      if (cleaned && !isMobilityPhrase(cleaned) && !hits.includes(cleaned)) hits.push(cleaned);
    });
  });
  if (!hits.length) {
    ["计算机", "软件", "电气", "电子", "自动化", "医学", "口腔", "师范", "法学", "金融", "理学", "数学", "物理", "化学"].forEach((keyword) => {
      if (text.includes(keyword) && !hits.length) hits.push(`偏${keyword}`);
    });
  }
  return hits.join("；");
}

function buildProfile(rawText) {
  const text = normalizeText(rawText);
  const province = extractProvince(text);
  return {
    province,
    rank: extractRank(text),
    group: extractGroup(text),
    family: extractFamily(text),
    prefs: extractPrefs(text),
    mobilityPreference: extractMobilityPreference(text),
    subjectCombo: extractSubjectCombo(text) || (extractGroup(text) === "phys" ? "物理" : extractGroup(text) === "hist" ? "历史" : ""),
    unsupportedProvince: province !== "广东" ? province : "",
    rawText: text,
  };
}

function missingFields(profile) {
  const fields = [];
  if (profile.rank === null) fields.push("排位");
  if (!profile.group) fields.push("科类");
  if (!profile.family) fields.push("家庭情况");
  if (!profile.prefs) fields.push("偏好");
  return fields;
}

function groupLabel(group) {
  if (group === "phys") return "物理类";
  if (group === "hist") return "历史类";
  return "未识别";
}

function buildRankWindows(rank) {
  if (rank <= 2000) {
    return {
      chongMin: rank,
      chongMax: rank + 8000,
      wenMin: rank + 8000,
      wenMax: rank + 25000,
      baoMin: rank + 25000,
    };
  }
  return {
    chongMin: Math.max(1, rank - 5000),
    chongMax: rank,
    wenMin: rank,
    wenMax: rank + 15000,
    baoMin: rank + 15000,
  };
}

function scoutOptions(dataset, rank, group) {
  const results = {
    "Chong (Aggressive)": [],
    "Wen (Stable)": [],
    "Bao (Guaranteed)": [],
  };
  const rankKey = `min_rank_${group}`;
  const windows = buildRankWindows(rank);
  dataset.colleges.forEach((college) => {
    college.majors.forEach((major) => {
      const minRank = major[rankKey];
      if (minRank === null || minRank === undefined) return;
      const entry = {
        college: college.name,
        major: major.name,
        tier: college.tier,
        min_rank: minRank,
        subject_req: major.subject_req,
        employment_tier: major.employment_tier || "B",
      };
      if (minRank >= windows.chongMin && minRank < windows.chongMax) results["Chong (Aggressive)"].push(entry);
      else if (minRank >= windows.wenMin && minRank <= windows.wenMax) results["Wen (Stable)"].push(entry);
      else if (minRank > windows.baoMin) results["Bao (Guaranteed)"].push(entry);
    });
  });
  return results;
}

function isRisky(option) {
  return ["C", "D"].includes(option.employment_tier) || riskKeywords.some((keyword) => option.major.includes(keyword));
}

function employmentScore(tier) {
  return employmentScores[tier] || 2;
}

function prefersScience(profile) {
  return ["理学", "数学", "物理", "化学", "生物"].some((keyword) => (profile.prefs || "").includes(keyword));
}

function isScienceMajor(major) {
  return scienceMajors.some((keyword) => major.includes(keyword));
}

function isScienceAdjacentMajor(major) {
  return scienceAdjacentMajors.some((keyword) => major.includes(keyword));
}

function collegePlatformScore(option) {
  return collegePlatformScores[option.tier] || 0;
}

function scoreOption(option, profile) {
  let score = employmentScore(option.employment_tier);
  const major = option.major;
  if (safeMajors.some((keyword) => major.includes(keyword))) score += 4;
  score += collegePlatformScore(option);

  if (prefersScience(profile)) {
    if (isScienceMajor(major)) {
      score += 6;
      if (collegePlatformScore(option) >= 3) score += 3;
    } else if (isScienceAdjacentMajor(major)) {
      score += 2;
    } else {
      score -= 1;
    }
  }

  if (["计算机", "软件", "人工智能", "编程"].some((keyword) => profile.prefs.includes(keyword)) &&
      ["计算机", "软件", "人工智能", "网络空间安全", "集成电路"].some((keyword) => major.includes(keyword))) {
    score += 4;
  }
  if (["电气", "电子"].some((keyword) => profile.prefs.includes(keyword)) &&
      ["电气", "电子"].some((keyword) => major.includes(keyword))) {
    score += 3;
  }
  if (["医学", "临床", "口腔"].some((keyword) => profile.prefs.includes(keyword)) &&
      ["医学", "临床", "口腔"].some((keyword) => major.includes(keyword))) {
    score += 4;
  }
  if ((profile.mobilityPreference === "prefer_in_province" || ["广东", "广州", "深圳"].some((keyword) => profile.prefs.includes(keyword))) &&
      (option.college.includes("广州") || option.college.includes("深圳"))) {
    score += 2;
  }
  if (["稳定", "考公", "考编", "体制"].some((keyword) => profile.family.includes(keyword)) &&
      ["电气", "自动化", "师范", "医学", "计算机", "法学"].some((keyword) => major.includes(keyword))) {
    score += 2;
  }
  return score;
}

function buildBanReason(option) {
  if (["C", "D"].includes(option.employment_tier)) return `就业档位 ${option.employment_tier}，风险较高。`;
  if (option.major.includes("土木工程")) return "土木方向周期承压，普通家庭要谨慎。";
  if (option.major.includes("建筑学")) return "建筑方向培养长、投入高，当前回报不稳定。";
  if (option.major.includes("心理学")) return "心理学对学历和深造要求高，就业兑现慢。";
  if (option.major.includes("海洋科学")) return "岗位面偏窄，就业弹性不足。";
  return "命中高风险关键词，建议谨慎。";
}

function strategicNotes(profile) {
  const notes = [
    "这不是简单查学校，而是一次 Ban/Pick 博弈：先排雷，再做冲稳保梯度配置。",
    "优先级顺序建议是：专业兑现率 > 城市机会 > 学校名气。",
  ];
  if (["普通", "工薪", "一般"].some((keyword) => profile.family.includes(keyword))) {
    notes.push("对普通家庭来说，志愿更要看兑现率，而不是只看学校招牌。");
  }
  if (["计算机", "软件", "人工智能", "电子", "电气"].some((keyword) => profile.prefs.includes(keyword))) {
    notes.push("你的偏好和粤港澳大湾区的技术岗位趋势是同向的，可以适当向工科和技术方向集中。");
  }
  if (prefersScience(profile)) {
    notes.push("你明确偏理学时，系统会提高纯理学专业和高平台院校的权重，不会简单拿四非应用工科压过 985/211 理学。");
  }
  if (profile.rank !== null && profile.rank <= 2000) {
    notes.push("你属于顶尖位次，静态展示页也同步启用了顶尖位次分层，避免出现空冲层。");
  }
  if (profile.mobilityPreference === "accept_outside") {
    notes.push("你已明确接受出省，但外省院校不会混入本轮自动结果；会单独进入人工专家补充判断卡片。");
  }
  return notes;
}

function summarizeFamilyAdvice(profile) {
  const family = profile.family || "普通家庭";
  const advice = [];
  if (["普通", "工薪", "一般"].some((keyword) => family.includes(keyword))) {
    advice.push("家庭资源偏普通时，要优先看就业确定性、城市资源和考公兼容性。");
    advice.push("专业优先级建议高于学校光环，避免投入高、回报慢的方向。");
  }
  if (["体制", "考公", "考编", "稳定"].some((keyword) => family.includes(keyword))) {
    advice.push("如果家庭更看重稳定，优先考虑电气、自动化、医学、师范、计算机等路径。");
  }
  if (!advice.length) advice.push("家庭条件和职业预期会直接影响志愿选择，建议把就业稳定性和地理位置一起纳入判断。");
  return advice;
}

function runStrategy(profile, candidateLayers) {
  const rankedLayers = {};
  const picks = {};
  Object.keys(candidateLayers).forEach((bucketName) => {
    rankedLayers[bucketName] = candidateLayers[bucketName]
      .filter((item) => !isRisky(item))
      .sort((a, b) => {
        const scoreDiff = scoreOption(b, profile) - scoreOption(a, profile);
        if (scoreDiff !== 0) return scoreDiff;
        const tierDiff = employmentScore(b.employment_tier) - employmentScore(a.employment_tier);
        if (tierDiff !== 0) return tierDiff;
        return a.min_rank - b.min_rank;
      });
    picks[bucketName] = rankedLayers[bucketName].slice(0, 3);
  });

  const banList = [];
  Object.entries(candidateLayers).forEach(([bucketName, bucket]) => {
    bucket.forEach((option) => {
      if (isRisky(option)) banList.push({ bucket: bucketName, option, reason: buildBanReason(option) });
    });
  });

  const notes = strategicNotes(profile);
  const scienceCandidates = Object.values(candidateLayers).flat().filter((item) => isScienceMajor(item.major));
  if (prefersScience(profile) && !scienceCandidates.length) {
    notes.push("当前广东本地样本库里纯理学专业覆盖不足，所以自动结果只能先给出理工相邻方向；这不代表 985 理学天然不如四非应用工科。");
  }

  return {
    rankedLayers,
    picks,
    banList: banList.slice(0, 6),
    strategicNotes: notes,
    familyAdvice: summarizeFamilyAdvice(profile),
  };
}

function extractAvoidTerms(prefs) {
  const terms = [];
  const matches = prefs.match(/(?:不想学|不想|不考虑|不要|排斥)([^；，。,!?\s]+)/g) || [];
  matches.forEach((item) => {
    const cleaned = item.replace(/^(?:不想学|不想|不考虑|不要|排斥)/, "").replace(/^学/, "").trim();
    cleaned.split(/[、/和与]/).forEach((part) => {
      const text = part.trim();
      if (text && !terms.includes(text)) terms.push(text);
    });
  });
  return terms;
}

function getSelectedSubjects(profile) {
  if (profile.subjectCombo === "物理+化学+生物") return new Set(["物理", "化学", "生物"]);
  if (profile.subjectCombo === "物理+化学") return new Set(["物理", "化学"]);
  if (profile.subjectCombo === "物理+生物") return new Set(["物理", "生物"]);
  if (profile.subjectCombo === "历史+政治+地理") return new Set(["历史", "政治", "地理"]);
  if (profile.subjectCombo === "历史") return new Set(["历史"]);
  if (profile.group === "phys") return new Set(["物理"]);
  if (profile.group === "hist") return new Set(["历史"]);
  return new Set();
}

function subjectRequirementCheck(profile, subjectReq) {
  if (!subjectReq || subjectReq === "不限") return { passed: true, reason: "" };
  const selectedSubjects = getSelectedSubjects(profile);
  const requiredSubjects = new Set(subjectReq.split("+").map((item) => item.trim()).filter(Boolean));

  if (profile.group === "hist") {
    if (["物理", "化学", "生物"].some((subject) => requiredSubjects.has(subject))) {
      return { passed: false, reason: `当前识别为历史类，不满足 ${subjectReq}` };
    }
    return { passed: true, reason: "" };
  }

  if (profile.group === "phys" && !requiredSubjects.has("物理")) {
    return { passed: false, reason: `当前识别为物理类，但要求为 ${subjectReq}` };
  }

  const matched = [...requiredSubjects].every((subject) => selectedSubjects.has(subject));
  if (matched) return { passed: true, reason: "" };
  if (profile.group === "phys" && selectedSubjects.size === 1 && selectedSubjects.has("物理") && requiredSubjects.size > 1) {
    return { passed: false, reason: `未提供更细选科组合，暂时无法确认是否满足 ${subjectReq}` };
  }
  return { passed: false, reason: `选科组合 ${profile.subjectCombo || "未识别"} 不满足 ${subjectReq}` };
}

function validateOption(profile, option, avoidTerms) {
  const reasons = [];
  const subjectCheck = subjectRequirementCheck(profile, option.subject_req);
  if (!subjectCheck.passed) reasons.push(subjectCheck.reason || "选科要求不匹配");
  if (isRisky(option)) reasons.push("命中高风险专业或低就业档位");
  if (avoidTerms.some((term) => option.major.includes(term))) reasons.push("与用户明确排斥项冲突");
  return reasons;
}

function optionKey(option) {
  return `${option.college}__${option.major}`;
}

function runRuleReferee(profile, strategyResult) {
  const avoidTerms = extractAvoidTerms(profile.prefs || "");
  const approvedPicks = {};
  const warnings = [];
  const errors = [];
  const replacements = [];
  const used = new Set();

  Object.keys(strategyResult.picks).forEach((bucketName) => {
    approvedPicks[bucketName] = [];
    strategyResult.picks[bucketName].forEach((option) => {
      const key = optionKey(option);
      if (used.has(key)) return;
      const reasons = validateOption(profile, option, avoidTerms);
      if (reasons.length) {
        errors.push(`${bucketName} 拦截：${option.college}｜${option.major}｜${reasons.join("；")}`);
        return;
      }
      used.add(key);
      approvedPicks[bucketName].push(option);
    });

    if (approvedPicks[bucketName].length < 3) {
      strategyResult.rankedLayers[bucketName].forEach((option) => {
        if (approvedPicks[bucketName].length >= 3) return;
        const key = optionKey(option);
        if (used.has(key)) return;
        const reasons = validateOption(profile, option, avoidTerms);
        if (reasons.length) return;
        used.add(key);
        approvedPicks[bucketName].push(option);
        replacements.push(`${bucketName} 补位：${option.college}｜${option.major}`);
      });
    }

    if (!approvedPicks[bucketName].length) warnings.push(`${bucketName} 当前没有通过规则校验的推荐。`);
  });

  const riskAlerts = [];
  const totalApproved = Object.values(approvedPicks).reduce((sum, items) => sum + items.length, 0);
  if (!totalApproved) {
    riskAlerts.push("当前没有通过校验的推荐结果，说明输入约束太强或数据集暂时不够，需要人工复核。");
  }
  if (profile.mobilityPreference === "prefer_in_province") {
    riskAlerts.push("你更偏省内，后续如果要进一步提分层次，可能需要权衡是否开放部分外省机会。");
  }
  if (profile.mobilityPreference === "accept_outside") {
    riskAlerts.push("你已接受出省，但当前自动候选仍限于广东样本库；如果要纳入外省高校，需要单独启用人工专家补充判断。");
  }
  const selectedSubjects = getSelectedSubjects(profile);
  if (profile.group === "phys" && selectedSubjects.size === 1 && selectedSubjects.has("物理")) {
    riskAlerts.push("你目前只提供了物理类，没有补充物化/物生/物化生；凡是需要化学或生物的专业，系统都会先从自动推荐里剔除。");
  }

  let status = "passed";
  if (errors.length && warnings.length) status = "passed_with_warnings";
  else if (errors.length) status = "corrected";
  else if (warnings.length) status = "warning";

  return { status, approvedPicks, warnings, errors, replacements, riskAlerts };
}

function statusLabel(status) {
  return {
    passed: "通过",
    warning: "通过但有提醒",
    corrected: "已自动纠偏",
    passed_with_warnings: "通过且伴随提醒",
  }[status] || status;
}

function formatOptionLine(label, option) {
  return `${label}：${option.college}｜${option.major}｜参考位次 ${option.min_rank}｜就业档位 ${option.employment_tier}｜选科要求 ${option.subject_req}`;
}

function normalizeCardSubjectCombo(profile) {
  return profile.subjectCombo || (profile.group === "phys" ? "物理" : profile.group === "hist" ? "历史" : "");
}

function cardMatchesProfile(card, profile) {
  const rank = profile.rank || 0;
  if (rank && !(card.rank_min <= rank && rank <= card.rank_max)) return false;
  if (card.region_scope === "outside" && profile.mobilityPreference === "prefer_in_province") return false;
  if (card.subject_combo_required && card.subject_combo_required.length) {
    if (!card.subject_combo_required.includes(normalizeCardSubjectCombo(profile))) return false;
  }
  return true;
}

function scoreCard(card, profile) {
  let score = Number(card.priority || 0);
  const text = `${profile.rawText || ""} ${profile.prefs || ""}`;
  (card.fit_tags || []).forEach((tag) => {
    if (text.includes(tag)) score += 3;
  });
  if (prefersScience(profile) && (card.fit_tags || []).some((tag) => ["理学", "数学", "物理", "化学"].includes(tag))) score += 5;
  if (text.includes(card.college) || text.includes(card.major)) score += 8;
  if (profile.mobilityPreference === "prefer_in_province" && card.region_scope === "in_province") score += 2;
  if (profile.mobilityPreference === "accept_outside" && card.region_scope === "outside") score += 2;
  return score;
}

function pickExpertCards(profile) {
  const cards = (state.expertCards && state.expertCards.cards) || [];
  return cards
    .filter((card) => cardMatchesProfile(card, profile))
    .sort((a, b) => scoreCard(b, profile) - scoreCard(a, profile))
    .slice(0, 4);
}

function buildScopeNotes(profile) {
  const notes = [
    "本轮自动推荐基于广东 2024 本地样本库生成，不代表全国实时录取数据库。",
    "内部沟通记录展示的是工作流审计摘要，不是源码执行日志。",
  ];
  if (profile.mobilityPreference === "accept_outside") {
    notes.push("你已明确接受出省，但省外院校不会混入本轮自动结果；如需扩展外省，会单独标注为人工专家补充判断。");
  }
  if (profile.rank !== null && profile.rank <= 2000) {
    notes.push("你属于顶尖位次，系统已启用顶尖位次分层，避免本地样本库上限导致冲层空缺。");
  }
  return notes;
}

function buildBoardroom(profile, candidateLayers, strategyResult, ruleResult, supplementCards) {
  const approvedTotal = Object.values(ruleResult.approvedPicks).reduce((sum, items) => sum + items.length, 0);
  const lines = [
    "老板：今天这位考生的案子，按公司流程做一次内部会审。",
    `客户经理 Agent：画像已经结构化，${groupLabel(profile.group)}，排位 ${profile.rank}，流动偏好 ${mobilityLabel(profile.mobilityPreference)}。`,
    `数据侦察 Agent：广东本地样本库已筛出候选池，冲 ${candidateLayers["Chong (Aggressive)"].length} 个，稳 ${candidateLayers["Wen (Stable)"].length} 个，保 ${candidateLayers["Bao (Guaranteed)"].length} 个。`,
    "策略 Agent：已完成 Ban/Pick，并把样本边界和理学偏好说明一并写入策略输出。",
    `规则校验 Agent：本轮状态 ${statusLabel(ruleResult.status)}，最终通过 ${approvedTotal} 个推荐。`,
  ];
  if (supplementCards.length) {
    lines.push(`人工专家补充判断模块：本轮额外命中 ${supplementCards.length} 张知识卡，只做补充判断，不混入自动冲稳保排序。`);
  }
  lines.push("老板：对外同步时必须分清自动结果、专家补充和审计摘要，这样项目才像真实产品。");
  return lines;
}

function buildWorkflow(rawText) {
  const profile = buildProfile(rawText);
  if (profile.unsupportedProvince) return { type: "unsupported", profile };
  const missing = missingFields(profile);
  if (missing.length) return { type: "incomplete", profile, missing };

  const candidateLayers = scoutOptions(state.dataset, profile.rank, profile.group);
  const strategyResult = runStrategy(profile, candidateLayers);
  const ruleResult = runRuleReferee(profile, strategyResult);
  const supplementCards = pickExpertCards(profile);
  return {
    type: "complete",
    profile,
    candidateLayers,
    strategyResult,
    ruleResult,
    supplementCards,
    scopeNotes: buildScopeNotes(profile),
    boardroom: buildBoardroom(profile, candidateLayers, strategyResult, ruleResult, supplementCards),
  };
}

function renderBulletCard(title, lines) {
  return `
    <article class="bullet-card">
      <h3>${title}</h3>
      <div class="bullet-list">
        ${lines.map((line) => `<p>${line}</p>`).join("")}
      </div>
    </article>
  `;
}

function renderTranscript(title, lines) {
  return `
    <article class="transcript-card">
      <h3>${title}</h3>
      <div class="transcript-lines">
        ${lines.map((line) => `<p>${line}</p>`).join("")}
      </div>
    </article>
  `;
}

function renderTraceTimeline(title, steps) {
  return `
    <article class="trace-card">
      <div class="trace-header">
        <h3>${title}</h3>
        <span class="trace-badge">审计摘要</span>
      </div>
      <div class="trace-list">
        ${steps.map((step, index) => `
          <div class="trace-step">
            <div class="trace-step-index">${index + 1}</div>
            <div class="trace-step-body">
              <p class="trace-step-actor">${step.actor}</p>
              <p class="trace-step-summary">${step.summary}</p>
            </div>
          </div>
        `).join("")}
      </div>
    </article>
  `;
}

function buildTraceSteps(result) {
  if (result.type === "incomplete") {
    return [
      { actor: "用户", summary: result.profile.rawText || "用户发来第一轮需求。" },
      { actor: "客户经理 Agent", summary: `已建立初版画像，但还缺：${result.missing.join("、")}。` },
      { actor: "老板", summary: "要求先补全排位、科类、家庭情况和偏好，再开后续会。"},
    ];
  }

  if (result.type === "complete") {
    const totalApproved = Object.values(result.ruleResult.approvedPicks)
      .reduce((sum, items) => sum + items.length, 0);
    const steps = [
      { actor: "用户", summary: result.profile.rawText || "用户发来完整需求。" },
      { actor: "客户经理 Agent", summary: `已建档：${groupLabel(result.profile.group)}，排位 ${result.profile.rank}，流动偏好 ${mobilityLabel(result.profile.mobilityPreference)}。` },
      { actor: "数据侦察 Agent", summary: `已基于广东本地样本库筛出候选池：冲 ${result.candidateLayers["Chong (Aggressive)"].length} 个，稳 ${result.candidateLayers["Wen (Stable)"].length} 个，保 ${result.candidateLayers["Bao (Guaranteed)"].length} 个。` },
      { actor: "策略 Agent", summary: `已完成 Ban/Pick，Ban 掉 ${result.strategyResult.banList.length} 个高风险方向，并写明样本边界。` },
      { actor: "规则校验 Agent", summary: `已完成校验，当前通过 ${totalApproved} 个推荐，状态 ${statusLabel(result.ruleResult.status)}。` },
    ];
    if (result.supplementCards.length) {
      steps.push({ actor: "人工专家补充判断模块", summary: `已补充 ${result.supplementCards.length} 张库外知识卡，与自动结果分开展示。` });
    }
    steps.push({ actor: "老板", summary: "批准对外输出方案，并要求把内部记录保留为审计摘要。" });
    return steps;
  }

  return [
    { actor: "系统", summary: "当前输入不在广东样本范围内，暂时无法生成正式 workflow。"},
  ];
}

const renderRoot = $("render-root");
const statusStrip = $("status-strip");

function renderIncomplete(result) {
  const lines = [
    `- 省份：${result.profile.province}`,
    `- 排位：${result.profile.rank ?? "未识别"}`,
    `- 科类：${groupLabel(result.profile.group)}`,
    `- 流动偏好：${mobilityLabel(result.profile.mobilityPreference)}`,
    `- 选科组合：${result.profile.subjectCombo || "未识别"}`,
    `- 家庭情况：${result.profile.family || "未识别"}`,
    `- 偏好：${result.profile.prefs || "未识别"}`,
  ];
  const askLines = result.missing.map((item) => `- 仍缺关键字段：${item}`);
  renderRoot.innerHTML = [
    renderBulletCard("客户经理 Agent", lines),
    renderBulletCard("当前不能继续推进的原因", askLines.concat(["- 建议用户直接补：排位、科类、家庭情况、偏好。"])),
    renderTraceTimeline("内部审计摘要", buildTraceSteps(result)),
  ].join("");
}

function renderUnsupported(result) {
  renderRoot.innerHTML = renderBulletCard("当前版本限制", [
    `- 当前识别到省份：${result.profile.unsupportedProvince}`,
    "- 这个静态展示页目前只内置了广东数据样本。",
    "- 如果是广东考生，可以继续直接体验完整业务链路。",
  ]);
}

function renderComplete(result) {
  const profileLines = [
    `- 省份：${result.profile.province}`,
    `- 排位：${result.profile.rank}`,
    `- 科类：${groupLabel(result.profile.group)}`,
    `- 流动偏好：${mobilityLabel(result.profile.mobilityPreference)}`,
    `- 选科组合：${result.profile.subjectCombo || "仅识别到科类"}`,
    `- 家庭情况：${result.profile.family}`,
    `- 偏好：${result.profile.prefs}`,
  ];

  const scoutLines = Object.entries(result.candidateLayers).flatMap(([bucketName, options]) => {
    const label = bucketName.startsWith("Chong") ? "冲" : bucketName.startsWith("Wen") ? "稳" : "保";
    const preview = options.slice(0, 2).map((item) => `- ${formatOptionLine(label, item)}`);
    return [`- ${label}层候选数：${options.length}`, ...preview];
  });

  const strategyLines = [
    ...result.strategyResult.strategicNotes.map((item) => `- ${item}`),
    ...result.strategyResult.banList.map((item) => `- Ban：${item.option.college}｜${item.option.major}｜${item.reason}`),
  ];

  const ruleLines = [
    `- 校验状态：${statusLabel(result.ruleResult.status)}`,
    ...result.ruleResult.errors.map((item) => `- ${item}`),
    ...result.ruleResult.replacements.map((item) => `- ${item}`),
    ...result.ruleResult.warnings.map((item) => `- ${item}`),
    ...result.ruleResult.riskAlerts.map((item) => `- ${item}`),
  ];

  const scopeLines = result.scopeNotes.map((item) => `- ${item}`);

  const supplementLines = result.supplementCards.length
    ? [
        "- 说明：以下内容不来自广东自动样本库，而是人工整理的专家知识卡，只做补充判断，不直接参与自动冲稳保排序。",
        ...result.supplementCards.flatMap((card, index) => [
          `- 卡片 ${index + 1}：${card.college}｜${card.major}`,
          `- 适用条件：位次约 ${card.rank_min} - ${card.rank_max}，选科 ${(card.subject_combo_required || ["不限"]).join("，")}，范围 ${card.region_scope}`,
          `- 为什么适合：${card.why_fit}`,
          `- 为什么不进自动结果：${card.why_not_auto}`,
        ]),
      ]
    : ["- 当前没有命中的人工专家补充判断卡片。"];

  const finalLines = Object.entries(result.ruleResult.approvedPicks).flatMap(([bucketName, options]) => {
    const label = bucketName.startsWith("Chong") ? "冲" : bucketName.startsWith("Wen") ? "稳" : "保";
    if (!options.length) return [`- ${label}层：当前无通过校验的自动推荐。`];
    return options.map((item) => `- ${formatOptionLine(label, item)}`);
  });

  const pills = [
    `Ban ${result.strategyResult.banList.length} 个方向`,
    `自动结果 ${finalLines.length} 条`,
    result.supplementCards.length ? `补充卡片 ${result.supplementCards.length} 张` : "无补充卡片",
    "审计摘要可复盘",
  ];

  renderRoot.innerHTML = [
    renderBulletCard("客户经理 Agent", profileLines),
    renderBulletCard("数据侦察 Agent", scoutLines),
    renderBulletCard("策略 Agent", strategyLines),
    renderBulletCard("规则校验 Agent", ruleLines),
    renderBulletCard("系统边界说明", scopeLines),
    renderBulletCard("人工专家补充判断卡片", supplementLines),
    renderBulletCard("最终自动冲稳保结果", finalLines.concat(result.strategyResult.familyAdvice.map((item) => `- ${item}`))),
    `<article class="render-card"><h3>项目亮点</h3><div class="pill-row">${pills.map((item) => `<span class="pill">${item}</span>`).join("")}</div></article>`,
    renderTraceTimeline("内部审计摘要", buildTraceSteps(result)),
    renderTranscript("老板驾驶舱", result.boardroom),
  ].join("");
}

function run(mode = "workflow") {
  if (!state.dataset || !state.expertCards) {
    statusStrip.textContent = "数据资源还没载入完成，请稍等。";
    return;
  }
  const input = $("user-input").value.trim();
  const result = buildWorkflow(input);

  if (result.type === "unsupported") {
    statusStrip.textContent = "当前命中外省输入，静态页只内置广东样本。";
    renderUnsupported(result);
    return;
  }
  if (result.type === "incomplete") {
    statusStrip.textContent = "客户经理 Agent 判断信息不全，已切到追问模式。";
    renderIncomplete(result);
    return;
  }

  statusStrip.textContent = mode === "boardroom"
    ? "老板驾驶舱已生成，自动结果、补充卡片和审计摘要也已同步对齐。"
    : "多 Agent 工作流已跑通，以下是自动结果 + 人工专家补充判断 + 审计摘要。";
  renderComplete(result);
}

async function loadDataset() {
  try {
    const [datasetResponse, cardResponse] = await Promise.all([
      fetch("./gd_2024_rankings.json"),
      fetch("./expert_supplement_cards.json"),
    ]);
    state.dataset = await datasetResponse.json();
    state.expertCards = await cardResponse.json();
    statusStrip.textContent = "广东数据样本和补充知识卡都已载入，可以开始演示。";
    run("workflow");
  } catch (error) {
    statusStrip.textContent = "数据载入失败。建议通过 GitHub Pages 或本地静态服务器打开。";
    renderRoot.innerHTML = renderBulletCard("数据载入失败", [
      "- 浏览器没有成功读取 `gd_2024_rankings.json` 或 `expert_supplement_cards.json`。",
      "- 如果你是直接双击打开 HTML，建议改用 GitHub Pages 或 `python -m http.server` 预览。",
    ]);
  }
}

$("load-sample").addEventListener("click", () => {
  $("user-input").value = SAMPLE_TEXT;
  run("workflow");
});

$("run-workflow").addEventListener("click", () => run("workflow"));
$("run-boardroom").addEventListener("click", () => run("boardroom"));

loadDataset();
