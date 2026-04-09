from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "docs" / "assets" / "screenshots"
OUT_DIR.mkdir(parents=True, exist_ok=True)

WIDTH = 1600
HEIGHT = 1000
BG = "#f5efe5"
INK = "#0f172a"
TEAL = "#0f766e"
COPPER = "#d97706"
CARD = "#fffdf8"
MUTED = "#586174"
LINE = "#d7d2c8"
SOFT = "#eef7f4"


def load_font(size: int, bold: bool = False):
    candidates = [
        "C:/Windows/Fonts/msyhbd.ttc" if bold else "C:/Windows/Fonts/msyh.ttc",
        "C:/Windows/Fonts/simhei.ttf" if bold else "C:/Windows/Fonts/simsun.ttc",
    ]
    for candidate in candidates:
        path = Path(candidate)
        if path.exists():
            return ImageFont.truetype(str(path), size=size)
    return ImageFont.load_default()


TITLE = load_font(46, bold=True)
H2 = load_font(34, bold=True)
H3 = load_font(26, bold=True)
BODY = load_font(20)
SMALL = load_font(18)


def rounded(draw, box, radius=28, fill=CARD, outline=LINE, width=2):
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


def text(draw, xy, content, font, fill=INK):
    draw.text(xy, content, font=font, fill=fill)


def line_height(font, extra=0):
    return font.size + extra


def wrap_text(draw, content, font, max_width):
    if not content:
        return [""]

    if " " not in content:
        lines = []
        current = ""
        for char in content:
            test = current + char
            if current and draw.textlength(test, font=font) > max_width:
                lines.append(current)
                current = char
            else:
                current = test
        if current:
            lines.append(current)
        return lines

    words = content.split(" ")
    lines = []
    current = ""
    for word in words:
        test = word if not current else f"{current} {word}"
        if current and draw.textlength(test, font=font) > max_width:
            lines.append(current)
            current = word
        else:
            current = test
    if current:
        lines.append(current)
    return lines


def draw_lines(draw, xy, lines, font=BODY, fill=INK, spacing=10):
    x, y = xy
    for line in lines:
        draw.text((x, y), line, font=font, fill=fill)
        y += line_height(font, spacing)
    return y


def draw_wrapped_text(draw, xy, content, font, max_width, fill=INK, spacing=10):
    return draw_lines(draw, xy, wrap_text(draw, content, font, max_width), font, fill, spacing)


def draw_bullets(draw, xy, items, font=BODY, fill=INK, bullet_fill=INK, max_width=700, spacing=12):
    x, y = xy
    for item in items:
        bullet_y = y + 7
        draw.ellipse((x, bullet_y, x + 6, bullet_y + 6), fill=bullet_fill)
        wrapped = wrap_text(draw, item, font, max_width)
        y = draw_lines(draw, (x + 18, y), wrapped, font, fill, 6)
        y += spacing
    return y


def pill(draw, xy, label, fill="#eef3f7", ink=INK):
    x, y = xy
    w = int(draw.textlength(label, font=SMALL)) + 34
    rounded(draw, (x, y, x + w, y + 38), radius=18, fill=fill, outline=fill, width=1)
    text(draw, (x + 17, y + 8), label, SMALL, ink)
    return x + w + 14


def make_canvas():
    image = Image.new("RGB", (WIDTH, HEIGHT), BG)
    draw = ImageDraw.Draw(image)
    draw.ellipse((-120, -80, 360, 320), fill="#f0d9b6")
    draw.ellipse((1180, -100, 1680, 300), fill="#d9ece6")
    draw.rectangle((0, 800, WIDTH, HEIGHT), fill="#efe7da")
    return image, draw


def save(image: Image.Image, name: str):
    path = OUT_DIR / name
    image.save(path)
    return path


def overview():
    image, draw = make_canvas()
    rounded(draw, (60, 60, 1000, 940), fill="#fffaf2")
    rounded(draw, (1030, 60, 1540, 285), fill="#f6fbf9", outline="#cfe3db")
    rounded(draw, (1030, 315, 1540, 565), fill="#fff8ee", outline="#eed9ba")
    rounded(draw, (1030, 595, 1540, 940), fill="#f7f7fb", outline="#d7dbe6")

    text(draw, (110, 115), "AI Gaokao BP Expert", SMALL, TEAL)
    title_lines = [
        "把高考志愿做成一套",
        "有组织、有流程、有风控的",
        "Agent 公司",
    ]
    y = draw_lines(draw, (110, 175), title_lines, TITLE, INK, 14)
    y += 18
    y = draw_wrapped_text(draw, (110, y), "真实业务链路：客户经理 intake、数据侦察、策略 Ban/Pick、规则校验", BODY, 820, MUTED, 10)
    y += 4
    y = draw_wrapped_text(draw, (110, y), "产品边界清晰：自动结果、人工专家补充判断、审计摘要分开展示", BODY, 820, MUTED, 10)
    y += 4
    y = draw_wrapped_text(draw, (110, y), "多入口闭环：本地脚本、GitHub Pages、OpenClaw + 微信", BODY, 820, MUTED, 10)

    x = 110
    x = pill(draw, (x, 520), "自动结果", "#fff1d8", COPPER)
    x = pill(draw, (x, 520), "专家补充", "#e5f5f0", TEAL)
    pill(draw, (x, 520), "审计摘要", "#edf1f7", INK)

    rounded(draw, (110, 600, 950, 870), radius=22, fill=SOFT, outline="#cfe3db")
    text(draw, (145, 640), "系统价值", H2, INK)
    draw_bullets(
        draw,
        (145, 705),
        [
            "不是单 Prompt，而是完整 Agent workflow",
            "有系统边界意识，避免把人工补充伪装成自动结果",
            "有 trace、memory、校验、回归测试，能支撑工程落地",
        ],
        BODY,
        INK,
        INK,
        740,
        16,
    )

    text(draw, (1070, 105), "交付结果", H3, TEAL)
    draw_bullets(draw, (1070, 155), ["冲稳保自动方案", "人工专家补充卡片", "可审计 trace"], BODY, INK, INK, 360, 10)

    text(draw, (1070, 355), "核心能力", H3, COPPER)
    draw_bullets(draw, (1070, 405), ["Multi-Agent Workflow", "Audit Trace", "Expert Supplement", "Rule Validation"], BODY, INK, INK, 360, 10)

    text(draw, (1070, 635), "一句话介绍", H3, INK)
    draw_wrapped_text(draw, (1070, 690), "把复杂业务问题做成边界清楚、可复盘、可展示的 Multi-Agent 决策系统。", BODY, 360, MUTED, 12)
    return save(image, "01-overview-hero.png")


def command_center():
    image, draw = make_canvas()
    rounded(draw, (55, 55, 530, 940), fill="#fffaf2")
    rounded(draw, (565, 55, 1545, 940), fill="#fffdf9")

    text(draw, (95, 105), "Command Center", H2, TEAL)
    y = draw_wrapped_text(draw, (95, 165), "输入画像", BODY, 360, INK, 12)
    y += 8
    for line in [
        "我是广东物理化学，排位5000，",
        "普通工薪家庭，偏理学，",
        "不想土木，不可接受出省",
    ]:
        y = draw_wrapped_text(draw, (95, y), line, BODY, 360, INK, 12)

    rounded(draw, (90, 330, 495, 520), radius=20, fill="#f6fbf9", outline="#cfe3db")
    text(draw, (120, 370), "核心能力", H3, INK)
    draw_bullets(
        draw,
        (120, 430),
        ["自动冲稳保结果", "选科校验与风险拦截", "理学偏好权重修正", "省内优先识别"],
        BODY,
        MUTED,
        MUTED,
        320,
        10,
    )
    x = 95
    x = pill(draw, (x, 580), "运行业务链路", "#fff1d8", COPPER)
    x = pill(draw, (x, 580), "老板驾驶舱", "#edf1f7", INK)
    pill(draw, (95, 635), "给我看内部沟通记录", "#e5f5f0", TEAL)

    text(draw, (605, 100), "自动结果", H2, INK)
    rounded(draw, (600, 150, 1510, 420), radius=22, fill="#f6fbf9", outline="#cfe3db")
    draw_lines(
        draw,
        (635, 190),
        [
            "客户经理：广东 / 物理类 / 物理+化学 / 省内优先 / 偏理学",
            "数据侦察：冲 5 个，稳 14 个，保 18 个",
            "策略：Ban 掉土木、建筑、心理学等高风险方向",
            "规则校验：通过校验，输出自动冲稳保结果",
        ],
        BODY,
        INK,
        18,
    )

    rounded(draw, (600, 455, 1510, 710), radius=22, fill="#fff8ee", outline="#eed9ba")
    text(draw, (635, 495), "人工专家补充判断卡片", H3, COPPER)
    draw_bullets(
        draw,
        (635, 545),
        [
            "华南理工大学｜数学与应用数学",
            "中山大学｜数学与应用数学",
            "暨南大学｜化学",
            "说明：仅做补充判断，不混入自动排序结果",
        ],
        BODY,
        INK,
        INK,
        780,
        14,
    )

    rounded(draw, (600, 730, 1510, 935), radius=22, fill="#f7f7fb", outline="#d7dbe6")
    text(draw, (635, 785), "产品边界", H3, INK)
    draw_bullets(
        draw,
        (635, 830),
        ["自动结果来自广东样本库", "库外知识单独进入补充卡片", "内部沟通记录只展示审计摘要"],
        BODY,
        MUTED,
        MUTED,
        780,
        10,
    )
    return save(image, "02-command-center.png")


def trace_boardroom():
    image, draw = make_canvas()
    rounded(draw, (55, 55, 870, 940), fill="#fffdf9")
    rounded(draw, (910, 55, 1545, 940), fill="#f7f7fb")

    text(draw, (95, 100), "内部审计摘要", H2, TEAL)
    steps = [
        ("1", "用户", "输入完整画像，触发高考 workflow"),
        ("2", "客户经理 Agent", "完成 intake，识别省内优先与物理+化学"),
        ("3", "数据侦察 Agent", "基于广东样本库筛出冲稳保候选池"),
        ("4", "策略 Agent", "完成 Ban/Pick，并写明理学偏好与数据边界"),
        ("5", "规则校验 Agent", "执行选科校验、拦截冲突并自动补位"),
        ("6", "人工专家补充判断", "补充库外理学高平台专业卡片"),
        ("7", "老板", "批准对外输出自动结果 + 补充卡片 + 审计摘要"),
    ]
    y = 165
    for idx, actor, summary in steps:
        rounded(draw, (95, y, 830, y + 92), radius=18, fill="#ffffff", outline="#d8dde7")
        rounded(draw, (115, y + 20, 160, y + 65), radius=20, fill="#fff1d8", outline="#fff1d8", width=1)
        text(draw, (130, y + 28), idx, H3, COPPER)
        text(draw, (190, y + 16), actor, H3, INK)
        draw_wrapped_text(draw, (190, y + 50), summary, SMALL, 600, MUTED, 6)
        y += 104

    text(draw, (945, 100), "老板驾驶舱", H2, INK)
    rounded(draw, (940, 155, 1515, 490), radius=22, fill="#fffaf2", outline="#e6d7bd")
    draw_lines(
        draw,
        (970, 195),
        [
            "老板：今天这位考生的案子，",
            "按公司流程做一次内部会审。",
            "",
            "客户经理：画像完整，",
            "流动偏好为省内优先。",
            "",
            "策略 Agent：自动结果只用广东样本库，",
            "库外判断单列为专家补充卡片。",
        ],
        BODY,
        INK,
        14,
    )

    rounded(draw, (940, 525, 1515, 920), radius=22, fill="#eef7f4", outline="#cfe3db")
    text(draw, (970, 565), "为什么这版更能打 JD", H3, TEAL)
    draw_bullets(
        draw,
        (970, 620),
        [
            "有 workflow，不是单 Prompt",
            "有 system boundary，不装作全国实时库",
            "有 traceability，能做复盘与解释",
            "有 memory / routing / validation / fallback 意识",
            "有 GitHub 展示页和微信入口，作品感更强",
        ],
        BODY,
        INK,
        INK,
        480,
        16,
    )
    return save(image, "03-trace-boardroom.png")


def main():
    paths = [overview(), command_center(), trace_boardroom()]
    for path in paths:
        print(path)


if __name__ == "__main__":
    main()
