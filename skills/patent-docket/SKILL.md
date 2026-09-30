---
name: patent-docket
description: "按发明人/工程师给的材料一趟写出交底书和申请文件；申请问题清单上的缺口最多改三轮。缺技术事实就问人，不编。触发：交底申请一起做、从零出交底和申请、一条龙、帮写交底再出申请、按清单改、会稿、案卷、/patent-docket。"
user-invocable: false
---

# 案卷会稿

## 用途

单 agent 协调者：立案、分诊、派工、记轮次。按发明人/工程师给的材料一趟串起交底书和申请文件。本包只调度与记案卷，不写交底正文、不出四件套。

## 何时用

须用户点名（交底申请一起做、从零出交底和申请、一条龙、帮写交底再出申请、按清单改、会稿、案卷、`/patent-docket`）。只写交底、或已有交底只出四件套 → **不要**进案卷。不要自动进入审查答复或政策简报。

## 输入

发明人/工程师材料；已有则读磁盘上的交底 md、申请 md、问题清单。状态以 `outputs/docket/{case_id}/docket.yaml` 为准。缺技术事实就问人，不编、不以聊天记忆当事实。

## 步骤

**先 `Read` `prompts/guardrails.md`，再 `Read` `prompts/intake.md`。** 禁止跳过 intake 直接派工。派工时 **`Read`** 对方 `SKILL.md` 并按该包执行。

每次进入都走：

1. `prompts/guardrails.md`
2. `prompts/intake.md`（判定 `from_zero` / `from_disclosure` / `from_application` / `resume`）
3. 按 intake 结果只加载下列之一，不要一次读完所有 prompt：
   - 新开或从零 → `prompts/bootstrap.md`
   - 已有 `docket.yaml` → `prompts/resume.md`
4. 之后按 `docket.yaml` 的 `phase` **只读**对应文件。阶段表在 `references/phases.yaml`。

| `phase` | 再读 |
|---------|------|
| `bootstrap_disclosure` / `wait_disclosure` / `dispatch_disclosure` | `prompts/dispatch_disclosure.md` |
| `bootstrap_application` / `wait_application` / `dispatch_application` | `prompts/dispatch_application.md` |
| `triage` | `prompts/triage.md` → `references/issue_taxonomy.md` |
| `ask_human` | `prompts/ask_human.md` |
| `round_close` | `prompts/round_close.md` |
| `terminal_*` | `prompts/round_close.md`（只做收口陈述 + **`## 交付后请确认`**，不再派工） |

阶段合法跳转：`references/phases.yaml`。机器校验：`tools/validate_docket.py`。tracker 落盘：`tools/emit_tracker.py`。交接只传路径：`references/handoff_contract.md`。

轮次上限 **`config.yaml` 的 `max_rounds`（默认 3）**，细则 `references/max_rounds.md`。从零：首套交底 + 首套申请记为第 1 轮。之后每「分诊 → 派工 → 再出申请并核清单」加 1 轮。第 3 轮结束后必须停。

```bash
python skills/patent-docket/tools/init_docket.py --case-id 案件slug --mode from_zero
python skills/patent-docket/tools/validate_docket.py --yaml outputs/docket/案件slug/docket.yaml
python skills/patent-docket/tools/emit_tracker.py --yaml outputs/docket/案件slug/docket.yaml
```

机读前缀：`DOCKET_DIR:` / `DOCKET_YAML:` / `DOCKET_OK:` / `DOCKET_ERROR:`。

## 护栏

- 细则 `prompts/guardrails.md`。**禁止**调用其他子技能 `tools/`（含交底包、申请包）；需要脚本时让被派工的那一包自己跑。
- **禁止**为销问题清单条目而编造结构、参数、步骤、查新命中。
- 存在 `blocking: true` 且 `status: open` 的 `ask_human` 时，不得 `dispatch_*`，不得加轮次。
- 不做审查答复、政策简报、著录检索当会稿引擎、多 agent 分发。

## 产出物

`outputs/docket/{case_id}/`：`docket.yaml`、`TRACKER.md`（脚本生成，不要手搓后与 yaml 分叉）、可选 `ROUND-{n}.md`。交底正文与四件套分别在交底包、申请包目录。收口对话末块标题 **交付后请确认**。
