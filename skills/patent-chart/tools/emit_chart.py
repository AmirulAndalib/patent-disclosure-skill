# -*- coding: utf-8 -*-
"""对照表落盘：chart.xlsx 主交付 + chart.json 底稿。不出 yaml/md，不出 html 工作面、不出 docx。"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from highlights import (
    PALETTE,
    clip_needles,
    clip_quote,
    ensure_highlights,
    format_analysis,
    normalize_highlights,
    paint_runs,
    runs_to_xlsx,
    strength_label,
    tidy_cjk_wrap,
)
from xlsx_minimal import (
    HEATMAP,
    QUOTE_TINT,
    S_CLAIM_NO,
    S_FEATURE,
    S_LABEL,
    S_LINK,
    S_NONE,
    S_WRAP,
    S_ZEBRA,
    STRENGTH_BADGE,
    write_workbook,
)

STRENGTHS = ("强", "中", "弱", "无")
SCENES = ("invalidity", "fto", "infringement", "sep", "patentability")
SCENE_ZH = {
    "invalidity": "无效对照",
    "fto": "FTO 初筛",
    "infringement": "侵权 / EoU",
    "sep": "标准必要专利",
    "patentability": "可专利性",
}
DISCLAIMER = (
    "本对照表是特征—证据底稿，**不构成法律意见**，"
    "不构成无效、侵权、自由实施或可专利性结论。重大决策请咨询专利代理师或律师。"
)


def default_output_dir(start: Path | None = None) -> Path:
    here = (start or Path(__file__).resolve()).resolve()
    cursor = here if here.is_dir() else here.parent
    for parent in [cursor, *cursor.parents]:
        if (parent / ".git").exists() or (parent / "outputs").is_dir():
            return parent / "outputs" / "patent-chart"
    return Path.cwd() / "outputs" / "patent-chart"


def _yaml_scalar(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    text = str(value)
    if text == "":
        return '""'
    if any(c in text for c in ":#{}[]&*?|>'!%@,") or "\n" in text or text.strip() != text:
        escaped = text.replace("\\", "\\\\").replace('"', '\\"')
        return f'"{escaped}"'
    return text


def dump_yaml(obj: Any, indent: int = 0) -> str:
    pad = "  " * indent
    if isinstance(obj, dict):
        if not obj:
            return pad + "{}\n"
        chunks: list[str] = []
        for key, val in obj.items():
            if isinstance(val, (dict, list)):
                chunks.append(f"{pad}{key}:\n{dump_yaml(val, indent + 1)}")
            else:
                chunks.append(f"{pad}{key}: {_yaml_scalar(val)}\n")
        return "".join(chunks)
    if isinstance(obj, list):
        if not obj:
            return pad + "[]\n"
        chunks = []
        for item in obj:
            if isinstance(item, dict):
                inner = dump_yaml(item, indent + 1)
                first, _, rest = inner.partition("\n")
                chunks.append(f"{pad}- {first.lstrip()}")
                if rest:
                    chunks.append("\n" + rest if not rest.startswith("\n") else rest)
                    if not rest.endswith("\n"):
                        chunks.append("\n")
            else:
                chunks.append(f"{pad}- {_yaml_scalar(item)}\n")
        return "".join(chunks)
    return pad + _yaml_scalar(obj) + "\n"


def _list_str(value: Any) -> list[str]:
    if isinstance(value, str) and value.strip():
        return [tidy_cjk_wrap(value.strip())]
    out = []
    for item in value or []:
        text = tidy_cjk_wrap(str(item).strip())
        if text:
            out.append(text)
    return out


def normalize_chart(raw: dict[str, Any]) -> dict[str, Any]:
    scene = str(raw.get("scene") or "patentability").strip().lower()
    if scene not in SCENES:
        scene = "patentability"
    features = []
    for item in raw.get("features") or []:
        if not isinstance(item, dict):
            continue
        features.append(
            {
                "feature_id": str(item.get("feature_id") or "").strip(),
                "claim_no": item.get("claim_no"),
                "text": tidy_cjk_wrap(str(item.get("text") or "").strip()),
            }
        )
    columns = []
    for item in raw.get("columns") or []:
        if not isinstance(item, dict):
            continue
        columns.append(
            {
                "id": str(item.get("id") or "").strip(),
                "label": str(item.get("label") or item.get("pub_number") or "").strip(),
                "pub_number": str(item.get("pub_number") or "").strip(),
                "source_url": str(item.get("source_url") or "").strip(),
            }
        )
    cells = []
    for item in raw.get("cells") or []:
        if not isinstance(item, dict):
            continue
        strength = str(item.get("strength") or "无").strip()
        if strength not in STRENGTHS:
            strength = "无"
        cells.append(
            {
                "feature_id": str(item.get("feature_id") or "").strip(),
                "column_id": str(item.get("column_id") or "").strip(),
                "strength": strength,
                "quote": tidy_cjk_wrap(str(item.get("quote") or "").strip()),
                "analysis": format_analysis(str(item.get("analysis") or "")),
                "source_url": str(item.get("source_url") or "").strip(),
                "desc_para": str(item.get("desc_para") or "").strip(),
                "covered": _list_str(item.get("covered")),
                "missing": _list_str(item.get("missing")),
                "cite": tidy_cjk_wrap(str(item.get("cite") or "").strip()),
                "highlights": normalize_highlights(item.get("highlights")),
            }
        )
    left = raw.get("left") if isinstance(raw.get("left"), dict) else {}
    chart = {
        "scene": scene,
        "left": {
            "pub_number": str(left.get("pub_number") or "").strip(),
            "features_path": str(left.get("features_path") or "").strip(),
        },
        "features": features,
        "columns": columns,
        "cells": cells,
        "highlights": normalize_highlights(raw.get("highlights")),
        "disclaimer": DISCLAIMER,
    }
    return ensure_highlights(chart)


def _cell_map(chart: dict[str, Any]) -> dict[tuple[str, str], dict]:
    out: dict[tuple[str, str], dict] = {}
    for cell in chart.get("cells") or []:
        out[(cell["feature_id"], cell["column_id"])] = cell
    return out


def _hls_for(chart: dict[str, Any], cell: dict | None) -> list[dict[str, str]]:
    base = list(chart.get("highlights") or [])
    if cell:
        base.extend(cell.get("highlights") or [])
    return base


def _para_tag(cell: dict) -> str:
    para = str(cell.get("desc_para") or "").strip()
    if para:
        return f"[{para}]"
    cite = _cite(cell)
    if "【" in cite:
        return cite
    if "[" in cite and "]" in cite:
        start = cite.find("[")
        end = cite.find("]", start)
        if end > start:
            return cite[start : end + 1]
    return ""


def _clip_needles_for(chart: dict[str, Any], feat: dict, cell: dict) -> list[str]:
    feat_text = str(feat.get("text") or "")
    related = []
    for item in _hls_for(chart, cell):
        claim = str(item.get("claim") or "")
        evid = str(item.get("evidence") or "")
        if claim and claim in feat_text:
            related.append(item)
        elif evid and evid in feat_text:
            related.append(item)
    return clip_needles(cell, related)


def _quote_preview(chart: dict[str, Any], feat: dict, cell: dict) -> str:
    quote = cell.get("quote") or ""
    if not quote:
        return ""
    clipped = clip_quote(quote, _clip_needles_for(chart, feat, cell))
    tag = _para_tag(cell)
    if tag and not clipped.startswith(tag):
        return f"{tag} {clipped}"
    return clipped


def _cite(cell: dict) -> str:
    if cell.get("cite"):
        return str(cell["cite"])
    para = cell.get("desc_para") or ""
    if para:
        return f"说明书 [{para}]"
    return ""


def _pending(chart: dict[str, Any]) -> list[str]:
    cmap = _cell_map(chart)
    pending: list[str] = []
    for feat in chart.get("features") or []:
        fid = feat["feature_id"]
        for col in chart.get("columns") or []:
            cell = cmap.get((fid, col["id"]))
            if cell is None or cell["strength"] in ("无", "弱") or not cell.get("quote"):
                pending.append(f"{fid} × {col['id']}")
    return pending


def _paint_md(text: str, highlights: list[dict[str, str]], *, side: str) -> str:
    parts = []
    for chunk, hid in paint_runs(text, highlights, side=side):
        if hid:
            parts.append(f"**{chunk}**")
        else:
            parts.append(chunk)
    return "".join(parts) or text


def _md_cell(text: str) -> str:
    return (text or "").replace("|", "\\|").replace("\n", " ")


def render_chart_md(chart: dict[str, Any]) -> str:
    scene = SCENE_ZH.get(chart["scene"], chart["scene"])
    left = (chart.get("left") or {}).get("pub_number") or "（未标公开号）"
    cols = chart.get("columns") or []
    pending = _pending(chart)
    cmap = _cell_map(chart)
    hls = chart.get("highlights") or []
    lines = [
        f"# 权利要求对照表 · {scene}",
        "",
        f"> {DISCLAIMER}",
        "",
        "预览用。**给人看、给人传的主文件是同目录 `chart.xlsx`**（总览可进入明细；同色底纹见「图例」）。不出 HTML 工作面。",
        "",
        f"- **场景**：{scene}（`{chart['scene']}`）",
        f"- **左列专利**：{left}",
        "",
        "## 覆盖总览",
        "",
    ]
    head = ["特征", "权要原文"] + [c["label"] or c["id"] for c in cols]
    lines.append("| " + " | ".join(head) + " |")
    lines.append("| " + " | ".join(["---"] * len(head)) + " |")
    for feat in chart.get("features") or []:
        fid = feat["feature_id"]
        bits = [fid, _md_cell(feat.get("text") or "")]
        for col in cols:
            cell = cmap.get((fid, col["id"])) or {}
            token = cell.get("strength") or "无"
            bits.append(strength_label(token))
        lines.append("| " + " | ".join(bits) + " |")
    lines.extend(["", "## 待核清单", ""])
    if pending:
        for item in pending:
            lines.append(f"- {item}")
    else:
        lines.append("- 无（仍须人审，不得视为结论）")
    if hls:
        lines.extend(["", "## 同色图例", ""])
        for h in hls:
            lines.append(
                f"- **{h['id']}** {h.get('label') or ''}：权要「{h.get('claim') or ''}」↔ 对照「{h.get('evidence') or ''}」"
            )
    for col in cols:
        lines.extend(["", f"## 对照表 · {col['label'] or col['id']}", ""])
        lines.append("| 特征 | 权要原文 | 对照摘录 | 对应说明 | 覆盖强弱 |")
        lines.append("| --- | --- | --- | --- | --- |")
        seen_quote: dict[str, str] = {}
        for feat in chart.get("features") or []:
            cell = cmap.get((feat["feature_id"], col["id"])) or {}
            local = _hls_for(chart, cell)
            claim = _paint_md(feat.get("text") or "", local, side="claim")
            preview = _quote_preview(chart, feat, cell)
            if preview and preview in seen_quote:
                tag = _para_tag(cell)
                quote = f"同 {seen_quote[preview]}" + (f" · {tag}" if tag else "")
            else:
                if preview:
                    seen_quote[preview] = feat["feature_id"]
                quote = _paint_md(preview or "（无）", local, side="evidence")
            analysis = cell.get("analysis") or "（未填写对应说明）"
            token = cell.get("strength") or "无"
            badge = strength_label(token)
            lines.append(
                "| "
                + " | ".join(
                    [
                        feat["feature_id"],
                        _md_cell(claim),
                        _md_cell(quote),
                        _md_cell(analysis),
                        badge,
                    ]
                )
                + " |"
            )
    lines.extend(["", "## 逐格摘录", ""])
    for feat in chart.get("features") or []:
        fid = feat["feature_id"]
        for col in cols:
            cell = cmap.get((fid, col["id"]))
            if not cell:
                continue
            local = _hls_for(chart, cell)
            lines.append(f"### {fid} · {col['id']}")
            lines.append("")
            token = cell.get("strength") or "无"
            lines.append(f"- **覆盖强弱**：{strength_label(token)}")
            cite = _cite(cell)
            if cite:
                lines.append(f"- **出处**：{cite}")
            if cell.get("source_url"):
                lines.append(f"- **来源**：{cell['source_url']}")
            if cell.get("covered"):
                lines.append("- **对应**：" + "；".join(cell["covered"]))
            if cell.get("missing"):
                lines.append("- **未记载**：" + "；".join(cell["missing"]))
            if feat.get("text"):
                lines.append("")
                lines.append("权要原文：")
                lines.append("")
                lines.append(_paint_md(feat["text"], local, side="claim"))
            if cell.get("quote"):
                lines.append("")
                lines.append("对照摘录：")
                lines.append("")
                lines.append(_paint_md(cell["quote"], local, side="evidence"))
            if cell.get("analysis"):
                lines.append("")
                lines.append(cell["analysis"])
            lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _rich_cell(text: str, highlights: list[dict[str, str]], *, side: str, style: int) -> dict[str, Any]:
    runs = runs_to_xlsx(paint_runs(text or "", highlights, side=side), highlights)
    return {"v": text or "", "s": style, "runs": runs or [(text or "", None)]}


def _drill_anchors(chart: dict[str, Any]) -> dict[tuple[str, str], int]:
    """明细表数据行号（Excel 行，含标题 3 行之后从 4 起）。每格占 9 行。"""
    anchors: dict[tuple[str, str], int] = {}
    row = 4
    for feat in chart.get("features") or []:
        for col in chart.get("columns") or []:
            anchors[(feat["feature_id"], col["id"])] = row
            row += 9
    return anchors


def _table_anchors(chart: dict[str, Any]) -> dict[tuple[str, str], int]:
    """对照表数据行号（每特征×对照一格一行，自第 4 行起）。"""
    anchors: dict[tuple[str, str], int] = {}
    row = 4
    for feat in chart.get("features") or []:
        for col in chart.get("columns") or []:
            anchors[(feat["feature_id"], col["id"])] = row
            row += 1
    return anchors


def render_xlsx_book(chart: dict[str, Any], *, title: str, subtitle: str) -> list[dict[str, Any]]:
    cols = chart.get("columns") or []
    cmap = _cell_map(chart)
    anchors = _drill_anchors(chart)
    table_anchors = _table_anchors(chart)
    overview_headers = ["特征", "权号", "权要原文"] + [c["label"] or c["id"] for c in cols] + ["打开明细"]
    overview_rows = []
    for feat in chart.get("features") or []:
        fid = feat["feature_id"]
        first = anchors.get((fid, cols[0]["id"])) if cols else 4
        row: list[Any] = [
            {"v": fid, "s": S_FEATURE},
            {"v": str(feat.get("claim_no") or ""), "s": S_CLAIM_NO},
            {"v": feat.get("text") or "", "s": S_WRAP},
        ]
        for col in cols:
            cell = cmap.get((fid, col["id"])) or {}
            token = cell.get("strength") or "无"
            loc_row = anchors.get((fid, col["id"]), first)
            row.append(
                {
                    "v": strength_label(token),
                    "s": HEATMAP.get(token, S_NONE),
                    "loc": f"'明细'!A{loc_row}",
                    "label": strength_label(token),
                }
            )
        row.append(
            {
                "v": "查看摘录",
                "s": S_LINK,
                "loc": f"'明细'!A{first}",
                "label": "查看摘录",
            }
        )
        overview_rows.append(row)

    chart_headers = [
        "特征",
        "权号",
        "权要原文",
        "对照对象",
        "对照摘录",
        "对应说明",
        "覆盖强弱",
        "出处",
        "明细",
    ]
    chart_rows = []
    seen_preview: dict[tuple[str, str], tuple[str, int]] = {}
    table_row_n = 4
    for feat in chart.get("features") or []:
        fid = feat["feature_id"]
        for i, col in enumerate(cols):
            cell = cmap.get((fid, col["id"])) or {}
            token = cell.get("strength") or "无"
            local = _hls_for(chart, cell)
            zebra = S_ZEBRA if i % 2 else S_WRAP
            cite = _cite(cell)
            url = cell.get("source_url") or col.get("source_url") or ""
            loc_row = anchors[(fid, col["id"])]
            quote_style = QUOTE_TINT.get(token, S_WRAP)
            preview = _quote_preview(chart, feat, cell)
            key = (col["id"], preview)
            if preview and key in seen_preview:
                first_fid, _first_row = seen_preview[key]
                tag = _para_tag(cell)
                label = f"同 {first_fid}" + (f" · {tag}" if tag else "")
                quote_cell: dict[str, Any] = {
                    "v": label,
                    "s": S_WRAP,
                    "note": preview,
                }
            else:
                if preview:
                    seen_preview[key] = (fid, table_row_n)
                quote_cell = _rich_cell(preview, local, side="evidence", style=quote_style)
            chart_rows.append(
                [
                    {"v": fid, "s": S_FEATURE},
                    {"v": str(feat.get("claim_no") or ""), "s": S_CLAIM_NO},
                    _rich_cell(feat.get("text") or "", local, side="claim", style=zebra),
                    {"v": col["label"] or col["id"], "s": zebra},
                    quote_cell,
                    {"v": cell.get("analysis") or "", "s": quote_style},
                    {
                        "v": strength_label(token),
                        "s": STRENGTH_BADGE.get(token, S_NONE),
                    },
                    {"v": cite or url, "s": S_LINK, "link": url or None, "label": cite or ("打开公布页" if url else "")},
                    {"v": "查看摘录", "s": S_LINK, "loc": f"'明细'!A{loc_row}", "label": "查看摘录"},
                ]
            )
            table_row_n += 1

    drill_headers = ["项", "内容", "跳转"]
    drill_rows: list[list[Any]] = []
    drill_heights: list[float] = []
    empty = {"v": "", "s": S_WRAP}
    for feat in chart.get("features") or []:
        fid = feat["feature_id"]
        for col in cols:
            cell = cmap.get((fid, col["id"])) or {}
            token = cell.get("strength") or "无"
            local = _hls_for(chart, cell)
            cite = _cite(cell)
            url = cell.get("source_url") or col.get("source_url") or ""
            table_row = table_anchors.get((fid, col["id"]), 4)
            block = [
                (
                    [
                        {"v": f"{fid} × {col['id']}", "s": S_FEATURE},
                        {"v": "返回总览", "s": S_LINK, "loc": "'总览'!A4", "label": "返回总览"},
                        {"v": "返回对照表", "s": S_LINK, "loc": f"'对照表'!A{table_row}", "label": "返回对照表"},
                    ],
                    22,
                ),
                (
                    [{"v": "覆盖强弱", "s": S_LABEL}, {"v": strength_label(token), "s": STRENGTH_BADGE.get(token, S_NONE)}, empty],
                    22,
                ),
                (
                    [
                        {"v": "出处", "s": S_LABEL},
                        {"v": cite or url, "s": S_LINK, "link": url or None, "label": cite or ("打开公布页" if url else "")},
                        empty,
                    ],
                    22,
                ),
                (
                    [{"v": "权要原文", "s": S_LABEL}, _rich_cell(feat.get("text") or "", local, side="claim", style=S_WRAP), empty],
                    36,
                ),
                (
                    [{"v": "对照摘录", "s": S_LABEL}, _rich_cell(cell.get("quote") or "（未见对应原文）", local, side="evidence", style=QUOTE_TINT.get(token, S_WRAP)), empty],
                    36,
                ),
                (
                    [{"v": "对应说明", "s": S_LABEL}, {"v": cell.get("analysis") or "（未填写）", "s": S_WRAP}, empty],
                    36,
                ),
                (
                    [{"v": "对应", "s": S_LABEL}, {"v": "；".join(cell.get("covered") or []) or "—", "s": S_WRAP}, empty],
                    22,
                ),
                (
                    [{"v": "未记载", "s": S_LABEL}, {"v": "；".join(cell.get("missing") or []) or "—", "s": S_WRAP}, empty],
                    22,
                ),
                ([{"v": "", "s": S_WRAP}, empty, empty], 12),
            ]
            for row, ht in block:
                drill_rows.append(row)
                drill_heights.append(ht)

    legend_headers = ["色号", "含义", "权要用语", "对照用语"]
    legend_rows: list[list[Any]] = []
    for h in chart.get("highlights") or []:
        rgb = "FF" + str(h.get("fg") or "2563EB")
        name = next((p["name"] for p in PALETTE if p["id"] == h["id"].split("_")[0]), "")
        token = f"{h['id']} {name}".strip()
        legend_rows.append(
            [
                {"v": token, "s": S_WRAP, "runs": [(token, rgb)]},
                {"v": h.get("label") or "", "s": S_WRAP, "runs": [(h.get("label") or "", rgb)]},
                {"v": h.get("claim") or "", "s": S_WRAP, "runs": [(h.get("claim") or "", rgb)]},
                {"v": h.get("evidence") or "", "s": S_WRAP, "runs": [(h.get("evidence") or "", rgb)]},
            ]
        )
    legend_rows.extend(
        [
            [{"v": "很强", "s": STRENGTH_BADGE["强"]}, {"v": "原文几乎覆盖该限定，且有出处", "s": S_WRAP}, {"v": "", "s": S_WRAP}, {"v": "", "s": S_WRAP}],
            [{"v": "中等", "s": STRENGTH_BADGE["中"]}, {"v": "手段对应但术语或限定不完全对齐", "s": S_WRAP}, {"v": "", "s": S_WRAP}, {"v": "", "s": S_WRAP}],
            [{"v": "偏弱", "s": STRENGTH_BADGE["弱"]}, {"v": "仅可能构成同义或片段相关", "s": S_WRAP}, {"v": "", "s": S_WRAP}, {"v": "", "s": S_WRAP}],
            [{"v": "未见", "s": STRENGTH_BADGE["无"]}, {"v": "对照材料中未见对应原文，单元格留空", "s": S_WRAP}, {"v": "", "s": S_WRAP}, {"v": "", "s": S_WRAP}],
            [
                {"v": "用法", "s": S_LABEL},
                {"v": "对照表摘录按对应短语截取并着色。「同 Fk · [段号]」悬停批注可看摘录；完整原文在明细。", "s": S_WRAP},
                {"v": "", "s": S_WRAP},
                {"v": "", "s": S_WRAP},
            ],
        ]
    )

    return [
        {
            "name": "总览",
            "title": title,
            "subtitle": subtitle + "  ·  点击强弱格进入明细",
            "headers": overview_headers,
            "rows": overview_rows,
            "widths": [9, 7, 36] + [14] * len(cols) + [12],
            "row_height": 28,
            "tab": "1F4E79",
        },
        {
            "name": "对照表",
            "title": title,
            "subtitle": subtitle + "  ·  摘录按对应短语截取并着色；「同 Fk」悬停可看摘录",
            "headers": chart_headers,
            "rows": chart_rows,
            "widths": [9, 7, 34, 14, 52, 40, 18, 20, 12],
            "row_height": 48,
            "tab": "2E7D32",
        },
        {
            "name": "明细",
            "title": title,
            "subtitle": "每格完整摘录。同色底纹见「图例」。可用「返回总览」「返回对照表」跳转。",
            "headers": drill_headers,
            "rows": drill_rows,
            "widths": [16, 80, 16],
            "heights": drill_heights,
            "row_height": 22,
            "tab": "C65911",
            "freeze": True,
        },
        {
            "name": "图例",
            "title": "同色图例与覆盖强弱",
            "subtitle": "色号行：高亮色加粗字。色块区分同一概念在权要与对照中的用语。",
            "headers": legend_headers,
            "rows": legend_rows,
            "widths": [18, 36, 28, 28],
            "row_height": 24,
            "tab": "5B6B7A",
        },
    ]


def write_chart_bundle(
    raw: dict[str, Any],
    *,
    output_dir: Path | None = None,
    case_id: str = "chart",
    into: Path | None = None,
) -> dict[str, Path]:
    chart = normalize_chart(raw)
    if into:
        folder = Path(into)
        folder.mkdir(parents=True, exist_ok=True)
    else:
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        folder = (output_dir or default_output_dir()) / f"{case_id}_{stamp}"
        folder.mkdir(parents=True, exist_ok=True)
    xlsx_path = folder / "chart.xlsx"
    json_path = folder / "chart.json"
    left_pub = (chart.get("left") or {}).get("pub_number") or ""
    scene = SCENE_ZH.get(chart["scene"], chart["scene"])
    subtitle = (
        f"{scene}"
        + (f"  ·  左列 {left_pub}" if left_pub else "")
        + "  ·  底稿，不构成法律意见"
    )
    write_workbook(
        xlsx_path,
        render_xlsx_book(chart, title="权利要求对照表", subtitle=subtitle),
    )
    json_path.write_text(json.dumps(chart, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"dir": folder, "xlsx": xlsx_path, "json": json_path}


def _load(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() in {".yaml", ".yml"}:
        raise ValueError("请传入 JSON（chart.json 或 Agent 打分对象），不要把 yaml 再喂给本脚本")
    data = json.loads(text)
    if not isinstance(data, dict):
        raise ValueError("JSON 须为对象")
    return data


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description="写出对照表 xlsx + json")
    ap.add_argument("--json", required=True, help="chart JSON")
    ap.add_argument("--output-dir", help="默认 outputs/patent-chart")
    ap.add_argument("--case-id", default="chart")
    ap.add_argument("--into", help="写入该会话目录（与 intake.json 同层）")
    args = ap.parse_args(argv)
    try:
        raw = _load(Path(args.json))
        paths = write_chart_bundle(
            raw,
            output_dir=Path(args.output_dir) if args.output_dir else None,
            case_id=args.case_id,
            into=Path(args.into) if args.into else None,
        )
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    print(f"CHART_DIR: {paths['dir']}", flush=True)
    print(f"CHART_XLSX: {paths['xlsx']}", flush=True)
    print(f"CHART_JSON: {paths['json']}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
