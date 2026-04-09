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
BLUE = "#e9f0fb"
BLUE_LINE = "#c8d5ee"
SAND = "#fbf6ee"
SHADOW = "#e7e1d6"


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


def metric_block(draw, box, eyebrow, title, lines, fill="#fffaf2", outline=LINE):
    x1, y1, x2, y2 = box
    rounded(draw, box, radius=24, fill=fill, outline=outline)
    text(draw, (x1 + 30, y1 + 28), eyebrow, SMALL, TEAL)
    text(draw, (x1 + 30, y1 + 68), title, H3, INK)
    draw_bullets(draw, (x1 + 30, y1 + 122), lines, BODY, MUTED, MUTED, x2 - x1 - 70, 12)


def number_badge(draw, xy, label, fill="#fff1d8", ink=COPPER):
    x, y = xy
    rounded(draw, (x, y, x + 46, y + 46), radius=23, fill=fill, outline=fill, width=1)
    text(draw, (x + 15, y + 8), label, H3, ink)


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
    rounded(draw, (60, 60, 1030, 940), fill="#fffaf2")
    rounded(draw, (1060, 60, 1540, 300), fill=SOFT, outline="#cfe3db")
    rounded(draw, (1060, 330, 1540, 600), fill=SAND, outline="#ead7b8")
    rounded(draw, (1060, 630, 1540, 940), fill=BLUE, outline=BLUE_LINE)

    text(draw, (110, 110), "AI Gaokao BP Expert", SMALL, TEAL)
    title_lines = [
        "把高考志愿分析做成",
        "可审计、可复盘、可展示的",
        "Multi-Agent 决策系统",
    ]
    y = draw_lines(draw, (110, 170), title_lines, TITLE, INK, 14)
    y += 20
    y = draw_wrapped_text(draw, (110, y), "真实业务链路由客户经理、数据侦察、策略与规则校验四类 Agent 组成。", BODY, 830, MUTED, 10)
    y += 4
    y = draw_wrapped_text(draw, (110, y), "自动结果严格限定在广东本地样本库内，库外知识独立进入专家补充卡片。", BODY, 830, MUTED, 10)
    y += 4
    y = draw_wrapped_text(draw, (110, y), "每轮分析都会落盘为审计摘要和老板驾驶舱，避免黑盒式输出。", BODY, 830, MUTED, 10)

    x = 110
    x = pill(draw, (x, 505), "Automatic Result", "#fff1d8", COPPER)
    x = pill(draw, (x, 505), "Expert Supplement", "#e5f5f0", TEAL)
    pill(draw, (x, 505), "Audit Trace", "#edf1f7", INK)

    metric_block(
        draw,
        (110, 585, 980, 885),
        "Design Principles",
        "核心设计原则",
        [
            "业务拆分优先于单次问答，关键步骤必须可单独审计。",
            "自动结果与专家补充分层展示，系统边界保持清晰。",
            "保留会话记忆、规则校验和回归测试，确保输出可落地。",
        ],
        fill="#f7fbfa",
        outline="#cfe3db",
    )

    metric_block(
        draw,
        (1060, 60, 1540, 300),
        "Delivery",
        "交付结果",
        ["冲稳保自动方案", "专家补充判断卡片", "老板驾驶舱与审计摘要"],
        fill=SOFT,
        outline="#cfe3db",
    )
    metric_block(
        draw,
        (1060, 330, 1540, 600),
        "Capabilities",
        "核心能力",
        ["Multi-Agent Workflow", "Rule Validation", "Audit Trace", "Structured Memory"],
        fill=SAND,
        outline="#ead7b8",
    )
    rounded(draw, (1060, 630, 1540, 940), radius=24, fill=BLUE, outline=BLUE_LINE)
    text(draw, (1095, 670), "一句话定位", SMALL, TEAL)
    draw_wrapped_text(
        draw,
        (1095, 725),
        "把复杂、高约束的志愿决策问题，组织成边界清楚、可解释、可复盘的产品化工作流。",
        BODY,
        390,
        INK,
        12,
    )
    return save(image, "01-overview-hero.png")


def command_center():
    image, draw = make_canvas()
    rounded(draw, (55, 55, 510, 940), fill="#fffaf2")
    rounded(draw, (545, 55, 1545, 940), fill="#fffdf9")

    text(draw, (95, 105), "Command Center", H2, TEAL)
    rounded(draw, (90, 160, 475, 330), radius=22, fill="#ffffff", outline="#dad4c8")
    text(draw, (120, 195), "输入画像", SMALL, TEAL)
    draw_wrapped_text(
        draw,
        (120, 235),
        "我是广东物理化学，排位5000，普通工薪家庭，偏理学，不想土木，不可接受出省。",
        BODY,
        300,
        INK,
        12,
    )

    rounded(draw, (90, 360, 475, 580), radius=22, fill="#f6fbf9", outline="#cfe3db")
    text(draw, (120, 398), "Workflow Summary", SMALL, TEAL)
    draw_bullets(
        draw,
        (120, 438),
        [
            "自动生成冲稳保结果",
            "执行选科校验与风险拦截",
            "理学偏好与省内优先权重修正",
            "支持老板驾驶舱和内部审计摘要",
        ],
        BODY,
        INK,
        INK,
        300,
        12,
    )

    x = 95
    x = pill(draw, (x, 620), "运行业务链路", "#fff1d8", COPPER)
    x = pill(draw, (x, 620), "老板驾驶舱", "#edf1f7", INK)
    pill(draw, (95, 675), "查看审计摘要", "#e5f5f0", TEAL)

    rounded(draw, (90, 760, 475, 900), radius=22, fill=SAND, outline="#ead7b8")
    text(draw, (120, 798), "交互入口", SMALL, COPPER)
    draw_bullets(
        draw,
        (120, 838),
        ["本地脚本", "静态展示页", "自然语言入口复用同一工作流"],
        SMALL,
        MUTED,
        MUTED,
        300,
        10,
    )

    text(draw, (585, 100), "自动结果", H2, INK)
    rounded(draw, (580, 150, 1510, 430), radius=22, fill="#f7fbfa", outline="#cfe3db")
    number_badge(draw, (615, 190), "1")
    text(draw, (680, 188), "画像结构化", H3, INK)
    draw_wrapped_text(draw, (680, 226), "广东 / 物理类 / 物理+化学 / 省内优先 / 偏理学", BODY, 760, MUTED, 8)
    number_badge(draw, (615, 286), "2")
    text(draw, (680, 284), "候选池筛选", H3, INK)
    draw_wrapped_text(draw, (680, 322), "数据侦察输出：冲 5 个，稳 14 个，保 18 个。", BODY, 760, MUTED, 8)
    number_badge(draw, (1075, 190), "3")
    text(draw, (1140, 188), "策略与校验", H3, INK)
    draw_wrapped_text(draw, (1140, 226), "Ban 掉土木、建筑、心理学等高风险方向，规则校验通过。", BODY, 320, MUTED, 8)

    rounded(draw, (580, 465, 1510, 700), radius=22, fill="#fff8ee", outline="#ead7b8")
    text(draw, (615, 505), "专家补充判断卡片", H3, COPPER)
    draw_bullets(
        draw,
        (615, 555),
        [
            "华南理工大学｜数学与应用数学",
            "中山大学｜数学与应用数学",
            "暨南大学｜化学",
            "仅做补充判断，不进入自动排序结果",
        ],
        BODY,
        INK,
        INK,
        820,
        14,
    )

    rounded(draw, (580, 735, 1510, 935), radius=22, fill=BLUE, outline=BLUE_LINE)
    text(draw, (615, 775), "边界声明", H3, INK)
    draw_bullets(
        draw,
        (615, 825),
        ["自动结果来自广东样本库", "库外知识单独进入补充卡片", "内部沟通记录仅展示审计摘要"],
        BODY,
        MUTED,
        MUTED,
        820,
        12,
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
        ("6", "专家补充模块", "补充库外理学高平台专业卡片"),
        ("7", "老板驾驶舱", "批准对外输出自动结果、补充卡片与审计摘要"),
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

    rounded(draw, (940, 525, 1515, 920), radius=22, fill=SOFT, outline="#cfe3db")
    text(draw, (970, 565), "审计结论", H3, TEAL)
    draw_bullets(
        draw,
        (970, 620),
        [
            "主链路由 intake、候选筛选、Ban/Pick 与规则校验组成。",
            "自动结果与专家补充严格分层，不混写能力边界。",
            "每轮分析保留时间线和驾驶舱摘要，支持复盘与解释。",
            "系统包含记忆、路由、校验与回归测试，具备持续迭代基础。",
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
