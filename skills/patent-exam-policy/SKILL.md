---
name: patent-exam-policy
description: "给交底用的政策简报：对照国知局近期口径，说明对交底写法/本稿的影响，并提示申请书式。技能进化仅为旁路，默认只改交底包，须另点名才改文件。"
user-invocable: false
---

# 政策简报（交底用）

## 用途

对照国知局近期口径，说明对交底写法 / 本稿的影响，并提示申请书式（只说明，默认不改申请包）。技能进化仅为旁路：同一套检索，仍先出简报。

## 何时用

须用户点名（政策简报 / 政策雷达 / 审查政策更新 / `/政策简报` / `/patent-brief` / `/patent-exam-policy`）。「技能进化 / `/patent-evolve`」同一入口，仍先出简报；只有用户再点名改技能时才 `Read` `apply_after_confirm.md`。不要挂进每次交底或解读的默认步骤。

## 输入

信源种子 `references/sources.yaml`（A 可支撑交底口径；B 与地方预审不得单独改技能）。主题→文件：`references/topic_prompt_map.md`（交底表可进 E*；申请表仅简报说明）。

## 步骤

1. **`Read`** `prompts/guardrails.md` → `intake.md`
2. **`Read`** `prompts/research.md`（A/B 分层种子 + 实用新型/外观/实施细则 + 相对上次增量）
3. **`Read`** `prompts/emit_backlog.md` → `outputs/exam-policy/`（含施行日历、对交底写法、对申请文件写法；进化附录默认不执行）
4. **仅当**用户明确要求改交底技能 → **`Read`** `prompts/apply_after_confirm.md`

## 护栏

- 细则 `prompts/guardrails.md`。**默认只出简报，不改技能。**
- 无人值守自动改任何 `SKILL.md` / `prompts/**` / `references/**` 并提交。
- 仅凭 B 源或无准确 URL 的传闻不得单独改技能。
- 「全部采纳」时不得改到交底包白名单以外。未收到改技能确认前，禁止 Edit/Write 技能正文（简报落盘除外）。

## 产出物

`outputs/exam-policy/` 政策简报。对话末块标题 **交付后请确认**（口令「按简报改交底技能」「采纳 E…」「沉淀到 docs/」）。不要把「全部采纳」当成默认下一步。
