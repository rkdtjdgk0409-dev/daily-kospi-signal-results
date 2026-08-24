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


def replace_once(path: str, old: str, new: str) -> None:
    p = Path(path)
    if not p.exists():
        return
    text = p.read_text(encoding="utf-8")
    if old in text:
        p.write_text(text.replace(old, new, 1), encoding="utf-8")


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


def patch_korea_structure_scroll():
    """Keep the stock-scan column the same height as the detail column and scroll it internally."""
    path = "docs/price-structure/index.html"

    old_css = (
        '.layout{display:grid;grid-template-columns:minmax(620px,1.15fr) minmax(420px,.85fr);gap:12px;align-items:start}'
        '.panel{background:rgba(14,21,38,.9);border:1px solid var(--line);border-radius:14px;overflow:hidden}'
        '.panelhead{padding:12px 14px;border-bottom:1px solid var(--line);display:flex;justify-content:space-between;align-items:center}'
        '.tablewrap{max-height:none;overflow-x:auto;overflow-y:visible}'
    )
    new_css = (
        '.layout{display:grid;grid-template-columns:minmax(620px,1.15fr) minmax(420px,.85fr);gap:12px;align-items:stretch}'
        '.panel{background:rgba(14,21,38,.9);border:1px solid var(--line);border-radius:14px;overflow:hidden}'
        '.scan-panel{display:flex;flex-direction:column;min-height:0;contain:size}'
        '.panelhead{padding:12px 14px;border-bottom:1px solid var(--line);display:flex;justify-content:space-between;align-items:center;flex:0 0 auto}'
        '.tablewrap{flex:1;min-height:0;overflow:auto;overscroll-behavior:contain;scrollbar-gutter:stable}'
    )
    replace_once(path, old_css, new_css)

    old_panel = (
        '<section class="panel">\n'
        '    <div class="panelhead"><strong>종목 스캔</strong>'
    )
    new_panel = (
        '<section class="panel scan-panel">\n'
        '    <div class="panelhead"><strong>종목 스캔</strong>'
    )
    replace_once(path, old_panel, new_panel)

    old_tablet = (
        '@media(max-width:1050px){.cards{grid-template-columns:repeat(3,1fr)}'
        '.layout{grid-template-columns:1fr}.tablewrap{max-height:none}.chart{height:360px}}'
    )
    new_tablet = (
        '@media(max-width:1050px){.cards{grid-template-columns:repeat(3,1fr)}'
        '.layout{grid-template-columns:1fr;align-items:start}'
        '.scan-panel{contain:none;height:62vh;min-height:360px}'
        '.tablewrap{max-height:none;overflow-y:auto}.chart{height:360px}}'
    )
    replace_once(path, old_tablet, new_tablet)

    old_mobile = '.chart{height:315px}.tablewrap{max-height:none}.hide-mobile{display:none}'
    new_mobile = '.chart{height:315px}.scan-panel{height:58vh;min-height:340px}.tablewrap{max-height:none;overflow-y:auto}.hide-mobile{display:none}'
    replace_once(path, old_mobile, new_mobile)


patch_korea_home()
patch_us_home()
patch_korea_position()
patch_korea_structure()
patch_korea_structure_scroll()
print("Navigation normalized and Korea price-structure stock scan made scrollable.")
