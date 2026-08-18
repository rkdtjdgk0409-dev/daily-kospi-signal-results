#!/usr/bin/env python3
from pathlib import Path

def patch_korea():
    p=Path("docs/index.html")
    if not p.exists():
        return
    t=p.read_text(encoding="utf-8")
    if 'href="position/"' in t:
        return
    old='<a class="market-link" href="us/">미국 시장</a>'
    new=old+'<a class="market-link" href="position/">포지션 관리</a>'
    if old in t:
        t=t.replace(old,new,1)
    p.write_text(t,encoding="utf-8")

def patch_us():
    p=Path("docs/us/index.html")
    if not p.exists():
        return
    t=p.read_text(encoding="utf-8")
    if '../position/' in t:
        return
    old='<div class="actions">'
    new='<div class="actions"><a class="btn" href="../">한국 시장</a><a class="btn" href="../position/">포지션 관리</a>'
    if old in t:
        t=t.replace(old,new,1)
    p.write_text(t,encoding="utf-8")

patch_korea()
patch_us()
print("Navigation patched")
