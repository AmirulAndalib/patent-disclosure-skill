---
name: patent-chart
description: "权利要求对照表：独权拆成技术特征，逐格比对对比文件/产品/标准，附证据与强弱。用于无效对照、FTO 初筛、侵权/EoU、SEP、可专利性底稿。须点名。不出法律意见。"
user-invocable: false
---

# 权利要求对照表

须用户点名（对照表 / claim chart / 无效对照 / FTO 初筛 / 侵权对照 / `/patent-chart`）。  
**先 `Read` `prompts/guardrails.md`，再 `Read` `prompts/intake.md`。** 禁止跳过 intake 直接填表。

本包只填矩阵并导出。左列特征、右列原文、补搜命中由解读包 / 检索包生产。

**派工**：必须先 `Read` 对方 `SKILL.md`，再**按其流程跑该包 `tools/`**。禁止没读 SKILL 就直接调对方脚本；禁止调交底包 `cnipa_epub_search.py`。解读包被对照表派工时：不要因 Obsidian 库路径暂停；默认把从属权也拆进 `claim_features.json`。

1. `prompts/guardrails.md` → `intake.md`（先 `--alloc`；三件套不齐只提问，**禁止**解读/检索/填格；收齐并 `INTAKE_OK:1` 后才分析）
2. 缺 `claim_features.json` → **`Read` `skills/patent-reader/SKILL.md`**，跑完读磁盘路径
3. 用户允许补 D 且有空格 → **`Read` `skills/patent-search/SKILL.md`**，再按其 `covers_rank.md` 出旁路
4. `prompts/fill_chart.md` 填格（跨列同色、书面对应说明、完整摘录）
5. `python skills/patent-chart/tools/emit_chart.py --json <payload.json> --into <INTAKE_DIR>`
6. 交付末块 **`Read` `prompts/delivery_confirm.md`**

产出：`outputs/patent-chart/{案件}/{会话}/` 下 **`intake.json`（本轮输入归档）** + **`chart.xlsx`（主交付）** + **`chart.json`（机读底稿，供再导出）**。不要把 `chart.json` 整份贴进对话。材料在对话里收集，不够就提问，收齐才落盘分析。**不出 `.md` / `.yaml` 对照副本，不出 `.docx`，不出 HTML 工作面**。**不出法律意见**。
