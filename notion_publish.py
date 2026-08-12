#!/usr/bin/env python3
from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path

import pandas as pd
import requests


NOTION_VERSION = "2026-03-11"


def fmt_num(v, decimals=1):
    if pd.isna(v):
        return "-"
    return f"{float(v):,.{decimals}f}"


def fmt_price(v):
    if pd.isna(v):
        return "-"
    return f"{int(round(float(v))):,}"


def build_markdown(results_dir: str = "results") -> str:
    base = Path(results_dir)

    summary = json.loads((base / "summary.json").read_text(encoding="utf-8"))
    buy = pd.read_csv(base / "latest_buy_signals.csv")
    active = pd.read_csv(base / "latest_active_trends.csv")

    generated = summary.get("generated_at", "")
    signal_date = summary.get("latest_signal_date", "-")
    params = summary.get("parameters", {})

    lines = []
    lines.append("> **자동 업데이트 페이지** · GitHub Actions가 평일 장 마감 후 갱신")
    lines.append("")
    lines.append(
        f"**기준일:** {signal_date}  ·  **업데이트:** {generated}  ·  "
        f"**신규 매수신호:** {len(buy)}개  ·  **상승추세 유지:** {len(active)}개"
    )
    lines.append("")
    lines.append("## 신규 매수 신호")
    lines.append("")
    lines.append(
        f"조건: **CCI({params.get('cci_period', 9)}) 0선 상향돌파 + "
        f"+DI > -DI + ADX({params.get('dmi_period', 14)}) ≥ {params.get('adx_threshold', 20)}**"
    )
    lines.append("")

    if buy.empty:
        lines.append("오늘 신규 매수 조건을 만족하는 종목이 없습니다.")
    else:
        lines.append("| 순위 | 종목 | 코드 | 종가 | CCI | +DI | -DI | ADX | CVD | 점수 |")
        lines.append("|---:|---|---|---:|---:|---:|---:|---:|---|---:|")
        for i, (_, r) in enumerate(buy.iterrows(), start=1):
            cvd = "강세" if bool(r["cvd_bull"]) else "중립/약세"
            lines.append(
                f"| {i} | {r['name']} | `{str(r['ticker']).zfill(6)}` | "
                f"{fmt_price(r['close'])} | {fmt_num(r['cci'])} | "
                f"{fmt_num(r['plus_di'])} | {fmt_num(r['minus_di'])} | "
                f"{fmt_num(r['adx'])} | {cvd} | {fmt_num(r['signal_score'])} |"
            )

    lines.append("")
    lines.append("## 현재 상승추세 유지 종목")
    lines.append("")
    lines.append("신규 신호가 아니더라도 현재 조건이 유지되는 종목입니다.")
    lines.append("")

    if active.empty:
        lines.append("현재 상승추세 유지 조건을 만족하는 종목이 없습니다.")
    else:
        # Keep Notion page compact.
        active_show = active.head(30)
        lines.append("| 순위 | 종목 | 코드 | 종가 | CCI | ADX | CVD | 점수 |")
        lines.append("|---:|---|---|---:|---:|---:|---|---:|")
        for i, (_, r) in enumerate(active_show.iterrows(), start=1):
            cvd = "강세" if bool(r["cvd_bull"]) else "중립/약세"
            lines.append(
                f"| {i} | {r['name']} | `{str(r['ticker']).zfill(6)}` | "
                f"{fmt_price(r['close'])} | {fmt_num(r['cci'])} | "
                f"{fmt_num(r['adx'])} | {cvd} | {fmt_num(r['signal_score'])} |"
            )

        if len(active) > 30:
            lines.append("")
            lines.append(f"_상승추세 유지 종목 {len(active)}개 중 상위 30개만 표시._")

    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("### 지표 해석")
    lines.append("")
    lines.append("- **신규 매수 신호:** CCI가 당일 처음 0선을 상향 돌파하면서 DMI/ADX 상승추세 조건을 동시에 만족")
    lines.append("- **CVD:** 일봉 OHLCV 기반 proxy이며 실제 bid/ask 체결 CVD가 아님")
    lines.append("- **점수:** ADX 50% + CCI 35% + CVD 확인 15%의 랭킹용 점수")
    lines.append("- 실제 주문 전에는 거래비용, 시가 갭, 거래정지 등 별도 확인 필요")

    return "\n".join(lines)


def update_notion_page(markdown: str):
    token = os.environ.get("NOTION_TOKEN")
    page_id = os.environ.get("NOTION_PAGE_ID")

    if not token:
        raise RuntimeError("Missing GitHub Secret: NOTION_TOKEN")
    if not page_id:
        raise RuntimeError("Missing GitHub Secret: NOTION_PAGE_ID")

    # Notion URLs sometimes get pasted instead of the raw page id.
    if "notion.so/" in page_id or "notion.site/" in page_id:
        page_id = page_id.rstrip("/").split("/")[-1].split("?")[0].split("-")[-1]

    url = f"https://api.notion.com/v1/pages/{page_id}/markdown"
    headers = {
        "Authorization": f"Bearer {token}",
        "Notion-Version": NOTION_VERSION,
        "Content-Type": "application/json",
    }
    payload = {
        "type": "replace_content",
        "replace_content": {
            "new_str": markdown
        }
    }

    r = requests.patch(url, headers=headers, json=payload, timeout=30)

    if r.status_code >= 400:
        raise RuntimeError(
            f"Notion API error {r.status_code}: {r.text[:1000]}"
        )

    print("[notion] page updated successfully")
    print(r.text[:500])


if __name__ == "__main__":
    md = build_markdown("results")
    Path("results/notion_preview.md").write_text(md, encoding="utf-8")
    update_notion_page(md)
