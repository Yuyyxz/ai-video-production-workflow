# AI 长视频生产工作流 (AI Video Production Workflow)

> **从创意到成片的完全体生产流水线** — 面向 AI 短剧 / 短剧集 / 动画 / 电影实验片
> 含资产管理、跨会话接力、质量门禁、自动化脚本

## 为什么需要这个

用 AI 做长视频(短剧/电影实验片)和做单条短片完全不同:

- 10-20 个会话接力,下一个会话要记得上一个的状态
- 几十个角色/场景/镜头资产,没有编号就乱
- 生成失败/角色变脸/参数翻车,教训必须沉淀
- 一个镜头没审过就批量生成 = 烧钱

这套工作流解决的就是这些:**资产可追溯、状态可接力、质量有门禁、成本可追踪**。

## 特性

- 🏷️ **资产编号体系** — 14 种类型(PRJ/WLD/SCR/CHR/SCN/SB/KF/VD/AU/SUB/FIN...),7 态状态机,manifest.csv 账本,全链路可追溯
- 📋 **项目状态卡** — 跨会话核心,新会话读卡续跑,结束更新卡
- 🔄 **8 阶段流水线** — P0立项→P1剧本→P2角色/世界观→P3分镜→P4素材→P5音频→P6后期→P7质检交付
- 🚧 **质量门禁** — 每阶段验收清单 + 人工审核门槛(剧本确认后才生成人物,人物确认后才生成视频)
- 🧩 **可插拔工具链** — DeepSeek/KPE 写剧本,可灵生成视频,Gemini/Confucius-TTS 配音,ffmpeg 拼接
- 🤖 **自动化脚本** — 一键初始化项目、资产校验、批量生成、拼接、帧提取

## 快速开始

```bash
# 1. 初始化一个项目
python workflow/scripts/init_project.py 我的短剧 --type 短剧集 --duration 600

# 2. 打开项目状态卡, 开始 P0 立项
#    my-drama/PROJECT_STATUS.md

# 3. 按 workflow/04-pipeline-stages.md 的 8 阶段推进
#    每阶段完成过质量门禁(workflow/05-quality-gates.md)
```

## 目录结构

```
workflow/
├── 01-asset-numbering.md      # 资产编号体系
├── 02-project-status-card.md  # 项目状态卡模板
├── 03-directory-structure.md  # 项目目录结构
├── 04-pipeline-stages.md      # 8阶段流水线定义
├── 05-quality-gates.md        # 质量门禁/验收标准
├── 06-toolchain.md            # 工具链选型
├── 07-templates/              # 10个模板(角色卡/剧本/分镜/音色/质检...)
└── scripts/                   # 5个自动化脚本
```

## 8 阶段流水线

```
P0 立项 → P1 剧本 → P2 角色/世界观 → P3 分镜
       → P4 素材生成 → P5 音频 → P6 后期 → P7 质检交付
```

每阶段含:输入 / 动作 / 输出 / 质量门禁 / 工具。详见 `04-pipeline-stages.md`。

## 核心原则

1. **状态卡是入口** — 新会话先读卡,结束更新卡
2. **manifest.csv 是账本** — 资产必须登记,有文件必有登记
3. **编号即文件名** — 一切产物有唯一编号
4. **版本只增不改** — 重做开新版本,不覆盖
5. **一切可追溯** — 成片→视频→关键帧→分镜→剧本
6. **门禁不过不入下一阶段**

## 工具链

| 环节 | 推荐 | 说明 |
|------|------|------|
| 剧本 | DeepSeek + KPE 导演引擎 | KPE: github.com/Yuyyxz/kling-prompt-engineering |
| 角色 | 角色卡 + Image2 参考图 | 逐字复制规则 |
| 分镜 | KPE keyframe-generator | |
| 视频生成 | 可灵 Kling v3 (API 2.0) | |
| 配音 | Confucius4-TTS / GPT-SoVITS | 中文配音硬要求 |
| 拼接 | ffmpeg | 自动化脚本 |
| 精修 | 剪映 / DaVinci | |
| 质检 | ffmpeg blackdetect + 人工抽检 | |

## 脚本

| 脚本 | 功能 |
|------|------|
| `init_project.py` | 一键初始化项目(18目录+状态卡+manifest) |
| `manifest_check.py` | 资产注册表完整性校验 |
| `kling_generate.py` | 可灵批量生成(轮询/重试/日志) |
| `concat_videos.py` | ffmpeg 顺序拼接 |
| `extract_frames.py` | 尾帧/关键帧提取 |

## 相关项目

- [kling-prompt-engineering (KPE)](https://github.com/Yuyyxz/kling-prompt-engineering) — 导演级可灵提示词工程库,本工作流的方法论层

## License

MIT
