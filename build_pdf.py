# -*- coding: utf-8 -*-
"""复用 render_paper.py 的排版逻辑，经 pdf_shim 输出文字版 PDF。"""
import os
import pdf_shim

src = open("render_paper.py", encoding="utf-8").read()
src = src.replace(
    "from PIL import Image, ImageDraw, ImageFont",
    "from pdf_shim import Image, ImageDraw, ImageFont")
src = src.replace('img1.save(f"{ROOT}/欣竹文化报-第1版.png")', "pass")
src = src.replace('img2.save(f"{ROOT}/欣竹文化报-第2版.png")', "pass")

exec(compile(src, "render_paper", "exec"), {"__name__": "__main__"})

DST = r"C:\Users\kylez\Documents\欣竹文化报\欣竹文化报-文字版.pdf"
TMP = DST.replace(".pdf", "-tmp.pdf")
pdf_shim.save_pdf(TMP)
try:
    os.replace(TMP, DST)
    print("PDF saved:", DST)
except PermissionError:
    print("LOCKED, saved as:", TMP)
