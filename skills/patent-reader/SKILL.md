---
name: patent-reader
description: "中国专利通俗解读：公开号/PDF 成通俗笔记、图谱与 Obsidian 入库。"
user-invocable: false
---

# 专利通俗解读

## 用途

把公开号 / PDF / 全文读成通俗笔记、图谱，并可写入 Obsidian。独权拆成稳定特征行（`claim_features.json`），说明书段落可机读（`description_paragraphs.json`），给对照表当输入。

## 何时用

用户说读专利、给出公开号或 PDF 且目标是「读懂」，或 `/patent-read`、`/读专利`。对照表派工缺 `claim_features.json` 时由对照表点名进入。不要跑交底 Step 1–8；不要因解读自动进对照表或专利地图。

## 输入

公开号、专利 PDF、或粘贴的权利要求/说明书。对照表派工时默认把从属权也拆进 `claim_features.json`；Obsidian 未就绪则降级 `outputs/patent_reader/`，不要暂停等库路径。

## 步骤

1. **`Read`** `prompts/patent_plain_reader.md`（含 Obsidian 门禁；对照表派工除外可降级继续）
2. 实用新型或外观：**`Read`** `prompts/type_hooks.md` + `prompts/fill_*`
3. 笔记 / 自检：`obsidian_ofm_companion.md`、`patent_reader_self_check.md`

工具在本包 **`tools/`**（`extract/` · `analyze/` · `vault/`）。PDF：`tools/extract/fetch_patent_pdf.py`；入库：`tools/vault/write_patent_obsidian_note.py`。特征行校验：`tools/analyze/validate_claim_features.py`。

## 护栏

- 解读不跑交底 Step 1–8，不自动进对照表 / 专利地图。
- 禁止跨包调用其他子技能 `tools/`。
- 对照表派工时不要因 Obsidian 库路径暂停。

## 产出物

工作区 **`outputs/patent_reader/`**：通俗笔记、图谱中间产物、`claim_features.json`、`description_paragraphs.json`（含 `source_url`）。有库则另写入 Obsidian。对话给出笔记路径。
