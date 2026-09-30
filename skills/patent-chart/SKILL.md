---
name: patent-chart
description: "权利要求对照表：独权拆成技术特征，逐格比对对比文件/产品/标准，附证据与强弱。用于无效对照、FTO 初筛、侵权/EoU、SEP、可专利性底稿。须点名。不出法律意见。"
user-invocable: false
---

# 权利要求对照表

## 用途

把独权（默认兼从权）拆成技术特征，逐格比对对比文件 / 产品 / 标准，附证据与强弱。用于无效对照、FTO 初筛、侵权/EoU、SEP、可专利性、审查答复驳回映射。本包只填矩阵并导出。左列特征、右列原文、补搜命中由解读包 / 检索包生产。

## 何时用

须用户点名（对照表 / claim chart / 无效对照 / FTO 初筛 / 侵权对照 / `/patent-chart`）。不要因写交底或读专利自动进入。

## 输入

左列须有公开号 / PDF / 权要 / `claim_features.json` / 交底 5.1。材料在对话里收集（`prompts/intake.md` 先 `--alloc`）；三件套不齐只提问。不够就提问，收齐并 `INTAKE_OK:1` 后才分析、才写 `intake.json`。

## 步骤

**先 `Read` `prompts/guardrails.md`，再 `Read` `prompts/intake.md`。** 禁止跳过 intake 直接填表。

派工必须先 `Read` 对方 `SKILL.md`，再按其流程跑**该包** `tools/`。禁止没读 SKILL 就直接调对方脚本。解读包被对照表派工时：不要因 Obsidian 库路径暂停；默认把从属权也拆进 `claim_features.json`。

1. `prompts/guardrails.md` → `intake.md`（先 `--alloc`；三件套不齐只提问，**禁止**解读/检索/填格；收齐并 `INTAKE_OK:1` 后才分析）
2. 缺 `claim_features.json` → **`Read` `skills/patent-reader/SKILL.md`**，跑完读磁盘路径
3. 用户允许补 D 且有空格 → **`Read` `skills/patent-search/SKILL.md`**，再按其 `covers_rank.md` 出旁路
4. `prompts/fill_chart.md` 填格（跨列同色、书面对应说明、完整摘录）
5. `python skills/patent-chart/tools/emit_chart.py --json <payload.json> --into <INTAKE_DIR>`
6. 交付末块 **`Read` `prompts/delivery_confirm.md`**

## 护栏

- 细则 `prompts/guardrails.md`。**不出法律意见**（无效 / 侵权 / 自由实施 / 可专利性结论都不写）。
- 禁止跨包调用 `tools/`；禁止调交底包 `cnipa_epub_search.py`。
- 无出处格子不得写成「公开了」。强度「强」必须有可点开的 `source_url` 或段号+摘录。
- 不出 `.md` / `.yaml` 对照副本，不出 `.docx`，不出 HTML 工作面。不要把 `chart.json` 整份贴进对话。

## 产出物

`outputs/patent-chart/{案件}/{会话}/`：**`intake.json`**（本轮输入归档）+ **`对照表-{场景}-{时间戳}.xlsx`**（主交付）+ **`chart.json`**（机读底稿）。xlsx 固定含总览 / 对照表 / 明细 / 图例；`invalidity` 加「路径备忘」，`fto` 加「风险清单」，`infringement` 加「证据缺口」，`oa` 加「驳回映射」。对话末块标题 **交付后请确认**。
