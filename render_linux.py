# -*- coding: utf-8 -*-
"""欣竹文化报：A4 200dpi 两栏活版式（无栏线、段首缩进、图文留距）"""
from PIL import Image, ImageDraw, ImageFont

W, H = 2339, 3307           # A3 @200dpi
ML, MR, MT, MB = 155, 155, 128, 128
CW = W - ML - MR
GAP = 79
COLW = (CW - GAP) // 2               # 两栏
GREEN_D = (27, 94, 32)
GREEN_M = (46, 125, 50)
GREEN_L = (232, 242, 228)
GRAY = (89, 89, 89)
INK = (26, 26, 26)
RULE = (185, 211, 179)
GOLD = (198, 154, 62)

FONTS = "/root/.openclaw/workspace/xznewspaper/fonts"
# 报纸字体：正文宋体、标题华文中宋、刊名华文行楷
FONT_FILES = {
    "NotoSansSC-Regular": (f"{FONTS}/simsun.ttc", 0),
    "NotoSansSC-Bold": (f"{FONTS}/STZHONGS.TTF", 0),
    "Xingkai": (f"{FONTS}/STXINGKA.TTF", 0),
}
FS = 1.2   # 字体放大系数

def fnt(name, size):
    size = int(size * FS)
    if name in FONT_FILES:
        path, idx = FONT_FILES[name]
        return ImageFont.truetype(path, size, index=idx)
    return ImageFont.truetype(f"{FONTS}/{name}.ttf", size)

ROOT = "/root/.openclaw/workspace/xznewspaper"
ASSETS = f"{ROOT}/assets"
PHOTO1 = f"{ROOT}/微信图片_20261009214826_2_103.jpg"
PHOTO2 = f"{ROOT}/微信图片_20261009214827_3_103.jpg"
PHOTO3 = f"{ROOT}/微信图片_20261009214829_4_103.jpg"
BAN2 = f"{ASSETS}/ban2_lineup.jpg"      # 2班参赛队候场照
CAMPUS = f"{ASSETS}/wx_img0.jpg"
SINGER = f"{ASSETS}/singer_stage.jpg"   # 十佳歌手比赛现场照（刘彦君与搭档）
BADGE = f"{ASSETS}/badge_new.png"

IMG_PAD_X = 36    # 图文水平间距
IMG_PAD_Y = 17    # 图文垂直间距


def text_w(font, s):
    return font.getlength(s)


class Flow:
    """两栏文本流，支持图片占位（文字绕排，图文留距）"""

    def __init__(self, draw, image, top, bottom):
        self.d = draw
        self.img = image
        self.top = top
        self.bottom = bottom
        self.col = 0
        self.y = top
        self.max_y = top
        self.obstructions = []

    def _col_x(self, c=None):
        c = self.col if c is None else c
        return ML + c * (COLW + GAP)

    def _avail(self, y, lh, c=None):
        x0, x1 = self._col_x(c), self._col_x(c) + COLW
        for (ox0, oy0, ox1, oy1) in self.obstructions:
            if y + lh <= oy0 or y >= oy1:
                continue
            if ox1 <= x0 or ox0 >= x1:
                continue
            if ox0 <= x0 and ox1 >= x1:
                return None
            if ox0 <= x0 < ox1:
                x0 = ox1
            elif x0 < ox0 < x1:
                x1 = ox0
        return (x0, x1)

    def _head_channel(self, lh):
        """栏头/标题用：返回 (x0, 可用宽)。整栏被挡则下移；与 para 共用同一避让逻辑"""
        while True:
            avail = self._avail(self.y, lh)
            if avail is None:
                if self.col == 1:
                    cover_bottom = max(oy1 for (_, oy0, _, oy1) in self.obstructions
                                       if not (self.y + lh <= oy0 or self.y >= oy1))
                    self.y = cover_bottom + 8
                    continue
                self._next_col()
                continue
            return avail

    def _next_col(self):
        self.col += 1
        self.y = self.top
        if self.col > 1:
            raise RuntimeError("版面溢出：两栏排不下")

    def image(self, path, x0, y0, w, photo_h, cap, cap_font):
        """跨栏图片：文字绕排，四周留出间距；先按目标比例居中裁剪，绝不拉伸变形"""
        total_h = photo_h + 68
        self.obstructions.append((x0 - IMG_PAD_X, y0 - IMG_PAD_Y,
                                  x0 + w + IMG_PAD_X, y0 + total_h + IMG_PAD_Y))
        src = Image.open(path).convert("RGB")
        target_ratio = w / photo_h
        src_ratio = src.width / src.height
        if src_ratio > target_ratio:    # 太宽，裁左右
            new_w = int(src.height * target_ratio)
            left = (src.width - new_w) // 2
            src = src.crop((left, 0, left + new_w, src.height))
        else:                           # 太高，裁上下（取中上段，保住主体）
            new_h = int(src.width / target_ratio)
            top = max(0, (src.height - new_h) // 3)
            src = src.crop((0, top, src.width, top + new_h))
        photo = src.resize((w, photo_h), Image.LANCZOS)
        self.img.paste(photo, (x0, y0))
        self.d.rectangle([x0, y0, x0 + w, y0 + photo_h], outline=(205, 205, 205), width=1)
        for i, line in enumerate(self._wrap(cap, cap_font, w - 8)):
            lw = text_w(cap_font, line)
            self.d.text((x0 + (w - lw) / 2, y0 + photo_h + 10 + i * 31), line, font=cap_font, fill=GRAY)

    # 避头尾：行首不出现句读标点，行尾不出现开括号/引号
    NO_LINE_START = set("，。、；：？！…—·」』）》】％")
    NO_LINE_END = set("「『（《【“‘")

    @classmethod
    def _kinsoku(cls, chars, i, line):
        if i < len(chars) and chars[i] in cls.NO_LINE_START:
            line.append(chars[i])
            i += 1
        while len(line) > 1 and line[-1] in cls.NO_LINE_END and i < len(chars):
            i -= 1
            line.pop()
        return i

    @classmethod
    def _wrap(cls, text, font, maxw):
        chars = list(text)
        lines, i = [], 0
        while i < len(chars):
            line, used = [], 0.0
            while i < len(chars):
                ch_w = text_w(font, chars[i])
                if used + ch_w <= maxw:
                    line.append(chars[i])
                    used += ch_w
                    i += 1
                else:
                    break
            if i < len(chars):
                i = cls._kinsoku(chars, i, line)
            if not line:          # 极窄兜底，防死循环
                line.append(chars[i])
                i += 1
            lines.append("".join(line))
        return lines

    def _draw_line(self, line, font, lx, lw, y, justify, fill):
        if justify and len(line) > 1:
            extra = lw - text_w(font, line)
            if extra > 0:
                step = extra / (len(line) - 1)
                cx = lx
                for ch in line:
                    self.d.text((cx, y), ch, font=font, fill=fill)
                    cx += text_w(font, ch) + step
                return
        self.d.text((lx, y), line, font=font, fill=fill)

    def para(self, text, font, lh, indent=0, after=24, justify=True, fill=INK):
        chars = list(text)
        i, first = 0, True
        while i < len(chars):
            avail = self._avail(self.y, lh)
            if avail is None:
                cover_bottom = max(oy1 for (_, oy0, _, oy1) in self.obstructions if not (self.y + lh <= oy0 or self.y >= oy1))
                if self.col == 1:
                    self.y = cover_bottom + 8
                    continue
                self._next_col()
                continue
            ax0, ax1 = avail
            lx = ax0 + (indent if first else 0)
            lw = ax1 - lx
            if lw < 96:
                cover_bottom = max((oy1 for (ox0, oy0, ox1, oy1) in self.obstructions
                                    if not (self.y + lh <= oy0 or self.y >= oy1) and not (ox1 <= ax0 or ox0 >= ax1)), default=None)
                if cover_bottom is not None:
                    self.y = cover_bottom + 8
                    continue
                self._next_col()
                continue
            line, used = [], 0.0
            last = False
            while i < len(chars):
                ch_w = text_w(font, chars[i])
                if used + ch_w <= lw:
                    line.append(chars[i])
                    used += ch_w
                    i += 1
                else:
                    break
            if i < len(chars):
                i = self._kinsoku(chars, i, line)
            if not line:
                line.append(chars[i])
                i += 1
            if i >= len(chars):
                last = True
            self._draw_line("".join(line), font, lx, lw, self.y, justify and not last, fill)
            self.y += lh
            first = False
            if self.y + lh > self.bottom:
                self._next_col()
        self.y += after
        self.max_y = max(self.max_y, self.y)

    def para_card(self, text, font, lh, indent=0, after=10, justify=True, fill=INK,
                  band=None, bar=None, band_in=8, bar_w=6, vpad=10):
        """访谈卡片：所有行缩进 indent；整段高亮带 band 与左竖条 bar，首行上沿/末行下沿再留 vpad 内边距"""
        chars = list(text)
        i, first = 0, True
        while i < len(chars):
            avail = self._avail(self.y, lh)
            if avail is None:
                cover_bottom = max(oy1 for (_, oy0, _, oy1) in self.obstructions if not (self.y + lh <= oy0 or self.y >= oy1))
                if self.col == 1:
                    self.y = cover_bottom + 8
                    continue
                self._next_col()
                continue
            ax0, ax1 = avail
            lx = ax0 + indent
            lw = ax1 - lx
            if lw < 96:
                cover_bottom = max((oy1 for (ox0, oy0, ox1, oy1) in self.obstructions
                                    if not (self.y + lh <= oy0 or self.y >= oy1) and not (ox1 <= ax0 or ox0 >= ax1)), default=None)
                if cover_bottom is not None:
                    self.y = cover_bottom + 8
                    continue
                self._next_col()
                continue
            line, used = [], 0.0
            last = False
            while i < len(chars):
                ch_w = text_w(font, chars[i])
                if used + ch_w <= lw:
                    line.append(chars[i])
                    used += ch_w
                    i += 1
                else:
                    break
            if i < len(chars):
                i = self._kinsoku(chars, i, line)
            if not line:
                line.append(chars[i])
                i += 1
            if i >= len(chars):
                last = True
            up = vpad if first else 3
            dn = vpad if last else 3
            if band:
                self.d.rectangle([ax0 + band_in, self.y - up, ax1 - band_in, self.y + lh + dn], fill=band)
            if bar:
                self.d.rectangle([ax0 + band_in, self.y - up, ax0 + band_in + bar_w, self.y + lh + dn], fill=bar)
            self._draw_line("".join(line), font, lx, lw, self.y, justify and not last, fill)
            self.y += lh
            first = False
            if self.y + lh > self.bottom:
                self._next_col()
        self.y += after
        self.max_y = max(self.max_y, self.y)

    def box(self, title, paras, font, lh, title_font, pad=24, border=GREEN_M, bg=(244, 248, 242)):
        inner_w = COLW - 2 * pad
        t_lines = self._wrap(title, title_font, inner_w)
        p_wraps = [self._wrap(p, font, inner_w - 24) for p in paras]
        box_h = pad + len(t_lines) * (lh + 8) + 14 + sum(len(pl) * lh + 14 for pl in p_wraps) + pad
        while True:
            conflict = None
            for (ox0, oy0, ox1, oy1) in self.obstructions:
                cx0, cx1 = self._col_x(), self._col_x() + COLW
                if cx0 < ox1 and cx1 > ox0 and self.y < oy1 and self.y + box_h > oy0:
                    conflict = oy1
            if conflict is None:
                break
            if self.col < 1 and conflict > self.y + box_h * 0.4:
                self._next_col()
            else:
                self.y = conflict + 16
        if self.y + box_h > self.bottom:
            self._next_col()
        x, y0 = self._col_x(), self.y
        self.d.rectangle([x, y0, x + COLW, y0 + box_h], outline=border, width=2, fill=bg)
        ty = y0 + pad
        for line in t_lines:
            self.d.text((x + pad, ty), line, font=title_font, fill=GREEN_D)
            ty += lh + 8
        ty += 14
        for pl in p_wraps:
            for i, line in enumerate(pl):
                self._draw_line(line, font, x + pad, inner_w - 24, ty, i != len(pl) - 1, INK)
                ty += lh
            ty += 14
        self.y += box_h + 24
        self.max_y = max(self.max_y, self.y)

    def photo_inline(self, path, cap, cap_font, photo_h):
        if self.y + photo_h + 76 > self.bottom:
            self._next_col()
        x = self._col_x()
        # 先按目标宽高比居中裁剪，再缩放，避免压扁变形
        src = Image.open(path).convert("RGB")
        target_ratio = COLW / photo_h
        src_ratio = src.width / src.height
        if src_ratio > target_ratio:    # 太宽，裁左右
            new_w = int(src.height * target_ratio)
            left = (src.width - new_w) // 2
            src = src.crop((left, 0, left + new_w, src.height))
        else:                           # 太高，裁上下（取中上段，保住主体）
            new_h = int(src.width / target_ratio)
            top = max(0, (src.height - new_h) // 3)
            src = src.crop((0, top, src.width, top + new_h))
        photo = src.resize((COLW, photo_h), Image.LANCZOS)
        self.img.paste(photo, (x, self.y))
        self.d.rectangle([x, self.y, x + COLW, self.y + photo_h], outline=(205, 205, 205), width=1)
        for i, line in enumerate(self._wrap(cap, cap_font, COLW - 8)):
            lw = text_w(cap_font, line)
            self.d.text((x + (COLW - lw) / 2, self.y + photo_h + 12 + i * 31), line, font=cap_font, fill=GRAY)
        self.y += photo_h + 76
        self.max_y = max(self.max_y, self.y)


def center_text(d, y, text, font, fill, w=W):
    tw = text_w(font, text)
    d.text(((w - tw) / 2, y), text, font=font, fill=fill)


def right_text(d, y, text, font, fill, right=ML + CW):
    tw = text_w(font, text)
    d.text((right - tw, y), text, font=font, fill=fill)


def footer(d, ban):
    center_text(d, H - 64, f"欣竹文化报 · 第 {ban} 版", fnt("NotoSansSC-Regular", 22), GRAY)


def masthead(d):
    badge = Image.open(BADGE).convert("RGB").resize((236, 236), Image.LANCZOS)
    d._image.paste(badge, (ML, MT))
    center_text(d, MT + 2, "欣竹文化报", fnt("Xingkai", 112), GREEN_D)
    center_text(d, MT + 168, "XINZHU WENHUA BAO", fnt("NotoSansSC-Bold", 26), GREEN_M)
    center_text(d, MT + 221, "记录校园点滴 · 展现青春风采", fnt("NotoSansSC-Regular", 25), GRAY)
    right_text(d, MT + 10, "2026年10月11日", fnt("NotoSansSC-Regular", 24), GRAY)
    right_text(d, MT + 55, "星期日 · 晴", fnt("NotoSansSC-Regular", 24), GRAY)
    bar_y = MT + 288
    d.rectangle([ML, bar_y, ML + CW, bar_y + 70], fill=GREEN_L)
    center_text(d, bar_y + 18, "2026年10月11日 星期日",
                 fnt("NotoSansSC-Bold", 26), GREEN_D)
    d.line([ML, bar_y + 86, ML + CW, bar_y + 86], fill=GREEN_D, width=5)
    d.line([ML, bar_y + 96, ML + CW, bar_y + 96], fill=GREEN_D, width=1)
    return bar_y + 140


def page_label(d, y, text):
    right_text(d, y, text, fnt("NotoSansSC-Bold", 26), GREEN_M)
    return y + 48


def section_label(d, flow_, text, extra=22):
    """绿色栏目头（人物·访谈 等），extra 为与上文空开的距离 """
    flow_.y += extra
    hx0, hx1 = flow_._head_channel(36)
    d.text((hx0, flow_.y), text, font=fnt("NotoSansSC-Bold", 26), fill=GREEN_M)
    flow_.y += 58
    flow_.max_y = max(flow_.max_y, flow_.y)


def article_head(d, flow_, title, subtitle=None):
    """文章独立标题：左对齐主标题 + 可选绿色副题"""
    hx0, hx1 = flow_._head_channel(44)
    x = hx0
    d.text((x, flow_.y), title, font=fnt("NotoSansSC-Bold", 36), fill=INK)
    flow_.y += 66
    if subtitle:
        d.text((x, flow_.y), subtitle, font=fnt("NotoSansSC-Bold", 26), fill=GREEN_M)
        flow_.y += 58
    flow_.y += 6
    flow_.max_y = max(flow_.max_y, flow_.y)


CAP = fnt("NotoSansSC-Regular", 21)
col1_x = ML
col2_x = ML + COLW + GAP

# ================= 第 1 版 =================
img1 = Image.new("RGB", (W, H), "white")
d1 = ImageDraw.Draw(img1)

y = masthead(d1)
y = page_label(d1, y, "第 1 版 · 校园新闻")

flow = Flow(d1, img1, y, H - MB - 50)
body_font = fnt("NotoSansSC-Regular", 25)
LH = 41
IND = 68  # 段首空两格

# —— 文章一（主稿）：抢零食大赛
article_head(d1, flow, "趣味互动点燃校园活力", "——我校“乐动比赛日”之抢零食大赛欢乐开赛")
right_text(d1, flow.y, "本报讯(记者 校报记者团)", fnt("NotoSansSC-Regular", 22), GRAY)
flow.y += 48
flow.top = flow.y  # 右栏从报头下方起排，避免压到署名行

# 两张绕栏图跨两栏中缝，一上一下，中间留白隔开
_img_y0 = flow.y
flow.image(PHOTO1, col1_x + COLW - 320, _img_y0 + 150, 640, 290, "起跑冲刺，同学们蓄势待发", CAP)
flow.image(PHOTO3, col1_x + COLW - 320, _img_y0 + 600, 640, 267, "班主任老师为参赛同学递上零食", CAP)

flow.para("为进一步丰富在校师生的课余文化生活，营造轻松鲜活的校园氛围，10月8日下午，由我校体育组主办的“乐动比赛日”主题活动核心项目——“抢零食大赛”在我校操场正式拉开帷幕，240名来自四个年级的初中学生报名参赛，活动现场欢声笑语不断，成为秋日校园里一道独特的活力风景线。", body_font, LH, indent=IND)
flow.para("本次大赛跳出传统文体赛事的固有框架，以“释放压力、共享欢乐”为核心设计理念，契合“乐动比赛日”让学生走下座位、动起来玩起来的活动定位。比赛分为四轮，各个年级各比赛一轮，活动现场的参赛区域内，每轮会放置各类零食放置在操场中央，各班班主任老师与学生配合，由老师传递零食，学生们接力运送零食来争取获得更多的零食数目。最后在各年级之间决出胜负。各班获得的零食也能带回班级与同学们分享。", body_font, LH, indent=IND)
flow.para("比赛现场气氛持续升温，不同年级、不同班级的参赛选手各展所长：观赛的同学们自发在赛场边围成圆圈，为参赛选手加油呐喊，观赛老师们掏出手机记录下欢乐瞬间，现场时不时爆发出阵阵笑声与欢呼声。同学们在奔跑冲刺中挥洒汗水，在配合接力里增进默契，同班级的伙伴也在你追我赶的比拼中加深了友谊。参赛同学们多数表示：这次比赛竞争很激烈，但也是有史以来举办得最好的一次乐动比赛。老师们的参与增进了新鲜感。大家争取回来的零食与同学们分享，进一步增进了同学们之间的友谊。", body_font, LH, indent=IND)
flow.para("此次抢零食大赛不仅为同学们提供了释放学业压力、舒展身心的平台，更让大家在轻松有趣的互动中感受到了校园生活的别样乐趣，充分展现了我校学子青春昂扬、团结向上的精神风貌。不少参赛同学赛后表示，这是自己参加过最有意思的校园活动，在跑步接力抢零食的过程中，既玩得尽兴，又收获了和同学、老师相处的珍贵回忆，希望未来学校能举办更多这类充满趣味的校园活动。本次“乐动比赛日”抢零食大赛在同学们的欢声笑语中圆满落下帷幕，接下来我校还将推出更多贴合学生需求的趣味文体活动，持续打造活力满格的校园文化，让同学们在学习之余收获更多欢乐与成长。", body_font, LH, indent=IND)

flow.para("作者：王馨恬、顾益谦、雷舒雯、都朔祎、施逸文、丁梓杰", fnt("NotoSansSC-Regular", 22), LH, indent=0, justify=False, fill=GRAY, after=8)

# —— 2 班来稿 · 独立成篇
section_label(d1, flow, "赛场 · 侧记")
article_head(d1, flow, "我校乐动抢零食比赛圆满落幕")
flow.para("金秋送爽，欢声笑语洒满校园。为丰富校园文体生活，缓解同学们的学习压力，营造轻松活泼、团结奋进的校园氛围，我校趣味运动会特色项目——抢零食大战在操场火热开赛。全校各年级同学踊跃参与，在趣味十足的比拼中释放活力，收获快乐，成为本次运动会最具人气的精彩赛事。", body_font, LH, indent=IND)
flow.para("不同于传统运动会的竞速、竞技比拼，抢零食大战主打趣味与欢乐，兼具灵活性与团队协作性，是专为同学们设计的创意趣味项目。赛前，工作人员提前布置好赛场，将饼干、糖果、面包、小零食等各类美味零食整齐摆放在赛场指定区域，琳琅满目的零食瞬间吸引了全场同学的目光。裁判老师详细讲解比赛规则，比赛以班级为单位分组进行，在规定时间内，参赛同学有序冲刺入场，在遵守规则的前提下抢夺零食，最终以班级累计抢夺零食数量及团队秩序综合评分决出优胜班级。", body_font, LH, indent=IND)
flow.para("随着裁判一声令下，比赛正式开始！原本安静的赛场瞬间沸腾起来。各班参赛同学精神抖擞、蓄势待发，听到口令后立刻飞奔而出，向着摆放零食的终点奋勇冲刺。赛场上一个个身影如同闪电般穿梭着。出发、冲刺、接零食、折返、击掌，一个个零食归入各班的“囊中”，现场气氛热烈高涨，加油声、欢呼声、笑语声此起彼伏。", body_font, LH, indent=IND)
flow.para("比赛过程中，同学们尽情投入，尽显少年活力。各班班主任也没闲着，他们一个个站在终点，一只手向前方跟来的同学递去一包包零食，有些老师还用上了妙招，直接“提前预定”把一大堆零食揽入自己的手中，一劳永逸。场外的观众们热情高涨，纷纷为自己班级的选手呐喊助威，镜头频频定格下同学们奔跑、欢笑、收获的美好瞬间。", body_font, LH, indent=IND)
flow.para("短短几分钟的比拼转瞬即逝，在裁判老师公正的统计下，本次抢零食大战落下帷幕，多个班级凭借高效的协作和良好的秩序斩获佳绩。赛后，参赛同学们手持满满的“战利品”，脸上洋溢着灿烂的笑容。大家相互分享零食、交流比赛趣事，校园里处处洋溢着温馨欢乐的氛围。有同学表示，这场特别的零食大战，不仅收获了美味的零食，更在轻松的游戏中放松了身心，增进了和同学之间的情谊。", body_font, LH, indent=IND)
flow.para("本次抢零食趣味赛事，是我校落实素质教育、打造多彩校园生活的生动缩影。没有激烈的竞技压力，却有满满的快乐与温暖，既锻炼了同学们的反应能力与协作能力，又有效舒缓了学业压力。相信同学们将带着赛场收获的快乐与活力，以更饱满的热情、更昂扬的状态投入到今后的学习生活中，不负时光，向阳成长。", body_font, LH, indent=IND)
# 署名行避开中缝图片，避免在窄栏里折出孤字
_cover_bottom = _img_y0 + 600 + 267 + 68 + 17
if flow.col == 1 and flow.y < _cover_bottom:
    flow.y = _cover_bottom + 4
flow.para("作者：王怡蓓、严茹萱、陈艺嘉、黄昕甜、王睿琪、王博嘉", fnt("NotoSansSC-Regular", 22), LH, indent=0, justify=False, fill=GRAY, after=8)

# —— 师者访谈（自第 2 版移来）
section_label(d1, flow, "师者 · 访谈")
article_head(d1, flow, "于细微处看见，于温暖中成长", "——专访余丹丹老师")
flow.para("“被看见”，是近来校园里的热门话题。在同学们心中，“被看见”代表着被尊重、被重视。那么站在教师的角度，教育里的“看见”究竟有着怎样的内涵？我们专访了余丹丹老师，聆听她对于教育中“看见”的理解。", body_font, LH, indent=IND)
flow.para("谈及教育中的“被看见”，余老师给出了质朴的答案：看见每个学生的优点。在她看来，每个孩子身上都藏着独属于自己的闪光点，教育不是只用分数评判学生，而是善于发掘学生身上不一样的长处。", body_font, LH, indent=IND)
flow.para("当问到“被看见”对中学生是否重要时，余老师十分肯定。青春期的学生内心敏感，非常渴望得到他人的关注与认可。一份及时的留意，一次真诚的肯定，都能给予学生前行的底气，帮助他们建立自信。", body_font, LH, indent=IND)
flow.para("说起真正“看见”一名学生的瞬间，余老师印象最深的，是内向的学生鼓起勇气主动举手回答问题的时候。平日里安静腼腆的孩子愿意突破自我，这份勇敢格外珍贵。而这份发现，往往藏在日常点滴之中，比如课后留下来陪同学背课文，耐心陪伴、用心倾听，就是她“看见”学生的方式。", body_font, LH, indent=IND)
flow.para("面对渴望被看见的同学们，余老师送上寄语：相信你自己。不是只有站在聚光灯下才算是被看见，不必等待别人来发现你的光芒。只要坚定相信自己，默默耕耘，你的努力与成长终会被看见。", body_font, LH, indent=IND)
flow.para("教育的本质，就是一场温柔的看见。老师用心读懂每一位少年，让每一份不张扬的努力都不被辜负。", body_font, LH, indent=IND)
flow.para("作者：柴雨轩、陈知行、王冠程、黄嘉睿、包晓妍、李玥瑶", fnt("NotoSansSC-Regular", 22), LH, indent=0, justify=False, fill=GRAY, after=8)

footer(d1, 1)
img1.save(f"{ROOT}/欣竹文化报-第1版.png")

# ================= 第 2 版 =================
img2 = Image.new("RGB", (W, H), "white")
d2 = ImageDraw.Draw(img2)

y2 = page_label(d2, MT, "第 2 版 · 歌声 校园")

COL_TOP2 = y2
COL_BOT2 = H - MB - 120

flow2 = Flow(d2, img2, COL_TOP2, COL_BOT2)
body_font2 = fnt("NotoSansSC-Regular", 26)
LH2 = 41
IND2 = 75
author_font2 = fnt("NotoSansSC-Regular", 22)

# —— 文章一（头条）：十佳歌手大赛报道
article_head(d2, flow2, "校园歌声绽芳华　青春逐梦展风采", "——我校十佳歌手大赛圆满落幕")
right_text(d2, flow2.y, "校园记者站 综合报道", author_font2, GRAY)
flow2.y += 16
flow2.top = flow2.y  # 右栏从报头下方起排

flow2.image(SINGER, col1_x + COLW - 390, flow2.y + 430, 780, 521, "刘彦君与搭档在十佳歌手比赛现场同台演唱", CAP)

flow2.para("近日，我校校园十佳歌手大赛顺利落下帷幕。全校热爱歌唱的学子齐聚舞台，以歌声传递青春力量，展现我校学子积极向上的精神风貌，丰富了校园文化生活。", body_font2, LH2, indent=IND2)
flow2.para("比赛现场氛围热烈，掌声与欢呼声此起彼伏，观众互动积极，为参赛选手营造了良好的表演氛围。参赛选手精心筹备、从容登台，用饱满的状态完成演唱作品，一次次将赛场气氛推向高潮。", body_font2, LH2, indent=IND2)
flow2.para("本次大赛中，不少选手凭借扎实的唱功和真挚的演绎收获现场好评。选手何紫欣为本次比赛精心筹备许久，选取偶像经典舞台曲目作为参赛作品。她坦言，登台前内心紧张忐忑，但站上舞台后迅速调整状态，全身心投入演唱，全程发挥稳定。她表示，校园十佳歌手大赛为文艺爱好者搭建了展示自我、锤炼胆识、提升能力的优质平台，是校园文化建设中极具意义的文体活动。", body_font2, LH2, indent=IND2)
flow2.para("与此同时，部分选手在比赛中经历了别样的备战过程。选手刘彦君原本为初赛精心准备了专属曲目，受节目统筹调整影响，因其初赛排名靠后，原有节目被合并更改。为顺利参与决赛比拼，她临时调整参赛方案，重新学习、练习全新曲目，仓促备赛的经历让她倍感遗憾与惋惜。", body_font2, LH2, indent=IND2)
flow2.para("据悉，校园十佳歌手大赛是我校经典校园文体活动，长期以来致力于为学子提供多元化的才艺展示渠道。本次活动不仅为同学们提供了绽放才华的舞台，更营造了积极健康、朝气蓬勃的校园文艺氛围，进一步丰富了校园文化内涵。", body_font2, LH2, indent=IND2)
flow2.para("作者：严雨阳、戴语骏、郑天星、朱崇璟、潘若水、胡沐儒", author_font2, LH2, indent=0, justify=False, fill=GRAY, after=22)

section_label(d2, flow2, "人物 · 访谈")
article_head(d2, flow2, "意外搭档下的歌唱舞台")
flow2.para("聚光灯灼灼亮起，悠扬的歌声回荡舞台。众人所见的是从容演绎的精彩瞬间，却鲜有人知晓，这份光鲜背后藏着一段仓促波折、充满意外的备赛经历。校园十佳歌手比赛落幕后，我们采访了一位特殊的参赛选手——刘彦君，聆听她独一无二的舞台故事。", body_font2, LH2, indent=IND2)
flow2.para("本次合唱参赛，全程仓促而匆忙。临近比赛，她才恍然记起登台日程。紧凑的周末里，她只能仓促熟悉曲目、简单反复排练、临时置办服装道具，几乎没有充足的时间打磨细节。初次站上舞台，紧张与局促瞬间涌上心头。", body_font2, LH2, indent=IND2)
flow2.para("比仓促备赛更让她难以适应的，是突如其来的搭档调换。原本计划单人参赛的她，被临时重组队伍，迎来一位全新的搭档，心中满是失落与无奈。两人音乐喜好、演唱风格截然不同，挑选曲目时屡屡碰壁。为了顺利完成比赛，她主动妥协，从零学习搭档选定的曲目，努力适配全新的舞台风格。", body_font2, LH2, indent=IND2)
flow2.para("纵使全程充满变数与遗憾，她依旧认真站上舞台，圆满完成了整场表演。她坦言，自己十分欣赏新搭档的能力与为人，却对这次仓促重组的安排倍感无奈。回望整场比赛，《海底》是她最为偏爱、印象最深的曲目。", body_font2, LH2, indent=IND2)
flow2.para("璀璨舞台从来不只有鲜花与掌声，更藏着少年不为人知的纠结、磨合与坚持。这场充满意外的合唱之旅褪去了舞台的滤镜，让我们看见：青春赛场从不是一帆风顺的完美演绎，那些突如其来的考验、仓促奔赴的成长，亦是舞台最动人的底色。", body_font2, LH2, indent=IND2)
flow2.para("作者：黄昕甜、陈艺嘉、王怡蓓、王博嘉、王睿琪、严茹萱", author_font2, LH2, indent=0, justify=False, fill=GRAY, after=14)

# —— 文章：评委问答（十佳歌手活动）
section_label(d2, flow2, "现场 · 问答")
article_head(d2, flow2, "丰富校园生活，展现青春风采", "——我校成功开展“校园十佳歌手”活动")
flow2.para("为丰富校园文化生活，提升学生综合素养，营造积极向上的校园氛围，近日，我校顺利开展“校园十佳歌手”活动。六七八年级师生积极参与，活动现场秩序井然、气氛热烈。", body_font2, LH2, indent=IND2)
flow2.para("活动前期，学校精心策划、周密部署，明确活动流程与分工，为本次活动顺利开展奠定了良好的基础。活动过程中，同学们积极参与，精神饱满、投入。各评委老师，评分公平公正。大家在竞歌中体验乐趣，在实践中收获成长，充分体现出新时代中学生朝气蓬勃、团结进取的良好精神风貌。", body_font2, LH2, indent=IND2)
flow2.para("为进一步获得本次活动信息，我团队特别采访了一位评委老师，采访结果如下：", body_font2, LH2, indent=IND2)
QA = [
    ("问：您认为学生参与“十佳歌手”活动有什么意义？",
     "答：丰富校园生活，鼓励学生积极参与艺术活动，增加了学生的胆识和表现，是很有意义的一项活动。"),
    ("问：您看完孩子们比赛后，有什么感受，有什么令您印象深刻的吗？",
     "答：看到学生们自己独立准备比赛用具，制作PPT，在台上积极展示自我，我作为观赛者深受触动，也希望孩子们绽放光芒。"),
    ("问：您对下次举办活动，同学们参与有什么建议？",
     "答：这次活动举办的很成功，希望下次能有更多学生积极参与。"),
    ("问：您觉得同学们参与活动时，有什么要加强的地方吗？",
     "答：我觉得部分学生还是不够放开，这一点有待继续努力。"),
    ("问：您认为办理这种活动，对教职工来说会很麻烦吗？",
     "答：在准备活动时或许要做很多事，投入时间，但丰富校园生活是很重要的，同学和教职工也应该在课余时间多参与艺术性活动。"),
]
q_font2 = fnt("NotoSansSC-Bold", 26)
for q, a in QA:
    flow2.para(q, q_font2, LH2, indent=0, after=30, justify=True, fill=GREEN_D)
    flow2.para_card(a, body_font2, LH2, indent=IND2, after=40, band=GREEN_L, bar=GREEN_M, vpad=14, band_in=16)
flow2.para("据采访可知，本次活动不仅丰富了同学们的课余生活，缓解了学习压力，更是得到了各教职工的支持。教发部也发布消息，表明我校于十月份会继续开展校艺体节活动，打造活力满满的文明校园。", body_font2, LH2, indent=IND2)
flow2.para("作者：刘子晴、姜嘉悦、张嘉琦、肖凡非、熊泽楷、李沛霖", author_font2, LH2, indent=0, justify=False, fill=GRAY, after=14)

flow2.box("编后小语", [
    "从奔跑的赛场到放声的歌台，青春的姿态有千百种，热爱与成长是共同的注脚。愿每位欣竹学子都能在自己的舞台上发光。",
], fnt("NotoSansSC-Regular", 24), 60, fnt("NotoSansSC-Bold", 28), pad=36, bg=(251, 246, 236), border=GOLD)

footer(d2, 2)
img2.save(f"{ROOT}/欣竹文化报-第2版.png")
print("page1 max_y =", flow.max_y, " bottom =", H - MB - 60)
print("page2 max_y =", flow2.max_y)
