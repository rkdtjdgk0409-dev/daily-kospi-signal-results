#!/usr/bin/env python3
from pathlib import Path
import re


def patch(path: str, pattern: str, repl) -> None:
    p = Path(path)
    if not p.exists():
        return
    text = p.read_text(encoding="utf-8")
    new, count = re.subn(pattern, repl, text, count=1, flags=re.S)
    if count:
        p.write_text(new, encoding="utf-8")


def patch_korea_home():
    # Korea context => US market + Korea position + Korea chart.
    pattern = r'<div class="hero-actions">.*?(<button id="refresh-btn")'
    def repl(m):
        return (
            '<div class="hero-actions">'
            '<a class="market-link" href="us/">미국 시장</a>'
            '<a class="market-link" href="position/">포지션 관리</a>'
            '<a class="market-link" href="price-structure/">차트 구조</a>'
            + m.group(1)
        )
    patch("docs/index.html", pattern, repl)


def patch_us_home():
    # US context => Korea market + US position + US chart.
    # Replacing the whole nav prefix also removes the accidental duplicated Korea button.
    pattern = r'<div class="actions">.*?(<button class="btn primary" id="refresh")'
    def repl(m):
        return (
            '<div class="actions">'
            '<a class="btn" href="../">한국 시장</a>'
            '<a class="btn" href="../us-position/">포지션 관리</a>'
            '<a class="btn" href="../us-price-structure/">차트 구조</a>'
            + m.group(1)
        )
    patch("docs/us/index.html", pattern, repl)


def patch_korea_position():
    pattern = r'<div class="nav">.*?</div>'
    repl = (
        '<div class="nav">'
        '<a href="../">한국 시장</a>'
        '<a href="../us/">미국 시장</a>'
        '<a class="active" href="./">포지션 관리</a>'
        '<a href="../price-structure/">차트 구조</a>'
        '</div>'
    )
    patch("docs/position/index.html", pattern, repl)


def patch_korea_structure():
    pattern = r'<div class="actions">.*?</div>'
    repl = (
        '<div class="actions">'
        '<a class="market-link" href="../">한국 시장</a>'
        '<a class="market-link" href="../us/">미국 시장</a>'
        '<a class="market-link" href="../position/">포지션 관리</a>'
        '<button class="btn" onclick="location.reload()">새로고침</button>'
        '</div>'
    )
    patch("docs/price-structure/index.html", pattern, repl)


patch_korea_home()
patch_us_home()
patch_korea_position()
patch_korea_structure()
print("Navigation normalized: Korea context and US context are now separated.")
