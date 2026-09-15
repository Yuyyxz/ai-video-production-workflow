# AGENTS.md — 长视频生产工作流 (ai-project/workflow)

> 项目级指令。用户级默认在 `~/.zcode/AGENTS.md`。

## 定位

AI 长视频生产工作流的知识库/编排骨架，落盘在 `C:\Users\YY\ai-project\workflow\`。用于把「可灵/Kling 等 AI 视频模型」组织成可复用的生产管线。

## 目录结构（07 编号体系）

```
workflow/
├── 01-asset-numbering.md      # 资产编号规则
├── 02-project-status-card.md  # 项目状态卡
├── 03-directory-structure.md  # 目录结构
├── 04-pipeline-stages.md      # 管线阶段
├── 05-quality-gates.md        # 质量门
├── 06-toolchain.md            # 工具链
├── 07-templates/             # 模板（含角色/场景/道具卡）
├── scripts/                   # 脚本
└── README.md
```

## 生成入口（三 skill 分工）

| Skill | 职责 |
|---|---|
| manju-director（本地 Hermes 目录名 master-director） | 导演方法论：一致性四机制 = 首尾帧关键帧对 > 视频延长 > 尾帧兜底；五题材 + 翻车矩阵；带 check_prompt / diagnose / extract_last_frame 脚本 |
| kling-prompt-engineering | 提示词：KPE 22号 33风格+50氛围，156条；导演引擎方法论移植自 seedance-2.0 |
| workflow 编排/资产/质检 | 生产工作流调度 |

## 关键设定卡

- 真人剧《我真没想重生啊》：2000 南京，陈汉升重生高三，沈幼楚 vs 萧容鱼。
  - 画风 = 高清电影 + 新海诚光影 + 2000年代细节；拒纯日系/旧滤镜/磨皮 CG 脸。
  - 设定卡：`07-templates/character-cards-重生的我们.md`。
- 可灵漫剧《你是说我被人捡走了？》：15 集都市治愈 AI 漫剧，179 镜头，Kling 首尾帧，角色/场景/道具卡；走剧本渠道，不做定妆/视觉样例。

## 约定

- 面向 AI 视频平台的统一导演式提示词工程（可灵/Kling、Seedance、Runway、Sora、Veo、Hailuo）。
- 任务 = 可验证目标（每步配 verify 检查），不要模糊指令。
