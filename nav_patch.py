#!/usr/bin/env python3
from pathlib import Path


def replace_once(path: str, old: str, new: str, sentinel: str) -> None:
    p = Path(path)
    if not p.exists():
        return
    t = p.read_text(encoding="utf-8")
    if sentinel in t:
        return
    if old in t:
        t = t.replace(old, new, 1)
        p.write_text(t, encoding="utf-8")


def patch_korea():
    p = Path("docs/index.html")
    if not p.exists():
        return
    t = p.read_text(encoding="utf-8")
    if 'href="price-structure/"' in t:
        return
    us = '<a class="market-link" href="us/">미국 시장</a>'
    position = '<a class="market-link" href="position/">포지션 관리</a>'
    insertion = us + '<a class="market-link" href="price-structure/">차트 구조</a>'
    if us + position in t:
        t = t.replace(us + position, insertion + position, 1)
    elif us in t:
        t = t.replace(us, insertion + position, 1)
    p.write_text(t, encoding="utf-8")


def patch_us():
    replace_once(
        "docs/us/index.html",
        '<div class="actions">',
        '<div class="actions"><a class="btn" href="../">한국 시장</a><a class="btn" href="../price-structure/">차트 구조</a><a class="btn" href="../position/">포지션 관리</a>',
        '../price-structure/',
    )


def patch_position():
    p = Path("docs/position/index.html")
    if not p.exists():
        return
    t = p.read_text(encoding="utf-8")
    if '../price-structure/' in t:
        return
    # Support either .btn or .market-link based position page versions.
    if '<div class="actions">' in t:
        t = t.replace('<div class="actions">', '<div class="actions"><a class="btn" href="../price-structure/">차트 구조</a>', 1)
    elif '</header>' in t:
        t = t.replace('</header>', '<a href="../price-structure/">차트 구조</a></header>', 1)
    p.write_text(t, encoding="utf-8")


patch_korea()
patch_us()
patch_position()
print("Navigation patched: Korea / US / Position / Price Structure")
