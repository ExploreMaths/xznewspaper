# -*- coding: utf-8 -*-
"""PIL → reportlab 垫片：让 render_paper.py 的排版代码原样输出矢量文字 PDF。"""
import io
import os
from reportlab.pdfgen import canvas as _canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont as _RLTTFont
from reportlab.lib.colors import Color
from reportlab.lib.utils import ImageReader
from pypdf import PdfWriter, PdfReader
from PIL import Image as _PILImage

W, H = 2339, 3307
S = 841.92 / W          # px → pt 缩放（A3）
_registered = set()


def _reg(path, name, index=0):
    if name not in _registered:
        pdfmetrics.registerFont(_RLTTFont(name, path, subfontIndex=index))
        _registered.add(name)


class FontShim:
    def __init__(self, name, size):
        self.name, self.size = name, size

    def getlength(self, s):
        return pdfmetrics.stringWidth(s, self.name, self.size)


class ImageFont:
    @staticmethod
    def truetype(path, size, index=0):
        base = os.path.basename(path).lower()
        mapping = {
            "simsun.ttc": "Song",
            "stzhongs.ttf": "Zhong",
            "stxingka.ttf": "Xingkai",
        }
        name = mapping.get(base, base.rsplit(".", 1)[0])
        _reg(path, name, index)
        return FontShim(name, size)


class _Photo:
    def __init__(self, im):
        self._im = im

    @property
    def size(self):
        return self._im.size

    @property
    def width(self):
        return self._im.size[0]

    @property
    def height(self):
        return self._im.size[1]

    def convert(self, mode):
        return _Photo(self._im.convert(mode))

    def resize(self, size, filt=None):
        return _Photo(self._im.resize(size, _PILImage.LANCZOS))

    def crop(self, box):
        return _Photo(self._im.crop(box))


def _col(c):
    r, g, b = c
    return Color(r / 255, g / 255, b / 255)


_pages = []


class _Page:
    def __init__(self, c):
        self.c = c

    def paste(self, photo, xy):
        self.c.drawImage(ImageReader(photo._im), xy[0] * S, H * S - (xy[1] + photo.height) * S,
                         photo.width * S, photo.height * S)


class Draw:
    def __init__(self, page):
        self._image = page
        self.c = page.c

    def text(self, xy, s, font, fill):
        self.c.setFont(font.name, font.size * S)
        self.c.setFillColor(_col(fill))
        self.c.drawString(xy[0] * S, H * S - (xy[1] + font.size * 0.86) * S, s)

    def line(self, pts, fill, width=1):
        self.c.setStrokeColor(_col(fill))
        self.c.setLineWidth(width * S)
        self.c.line(pts[0] * S, H * S - pts[1] * S, pts[2] * S, H * S - pts[3] * S)

    def rectangle(self, box, outline=None, width=1, fill=None):
        x0, y0, x1, y1 = box
        self.c.setLineWidth(width * S)
        if outline is not None:
            self.c.setStrokeColor(_col(outline))
        if fill is not None:
            self.c.setFillColor(_col(fill))
        self.c.rect(x0 * S, H * S - y1 * S, (x1 - x0) * S, (y1 - y0) * S,
                    stroke=1 if outline is not None else 0, fill=1 if fill is not None else 0)


class Image:
    LANCZOS = 1

    @staticmethod
    def open(path):
        return _Photo(_PILImage.open(path))

    @staticmethod
    def new(mode, size, color):
        buf = io.BytesIO()
        c = _canvas.Canvas(buf, pagesize=(W * S, H * S))
        c.setFillColor(Color(1, 1, 1))
        c.rect(0, 0, W * S, H * S, fill=1, stroke=0)
        page = _Page(c)
        page._buf = buf
        _pages.append(page)
        return page


class ImageDraw:
    @staticmethod
    def Draw(page):
        return Draw(page)


def save_pdf(path):
    writer = PdfWriter()
    for p in _pages:
        p.c.showPage()
        p.c.save()
        p._buf.seek(0)
        writer.append(PdfReader(p._buf))
    with open(path, "wb") as f:
        writer.write(f)
