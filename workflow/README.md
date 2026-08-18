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
| `qa_tech.py` | 成片技术质检(黑帧/冻结/静音/响度/分辨率, 纯 ffmpeg 无需视觉, 支持 --fix 自动修分辨率) |

## 实测验证

> 2026-08 用真实素材 + 真实项目完整压测, 全部通过。

### 1. 脚本全链路(用 kling-drama 示例项目《视线》3 段真实视频)

| 脚本 | 实测结果 |
|------|---------|
| `extract_frames.py` | ✅ 提取尾帧 1916×1080 |
| `concat_videos.py` | ✅ 3段→15.17s 成片(21.6MB) |
| `manifest_check.py` | ✅ 抓到 ghost.mp4 缺失(检测有效) |
| `kling_generate.py` | ✅ dry-run + 真实提交(走到余额报错 429/1102, 契约正确) |
| `qa_tech.py` | ✅ 抓出可灵真实尺寸 1916×1080 不足 1920 的硬伤, --fix 规整到 1920×1080 |

### 2. LumenX Studio 端到端(本地部署 + 可灵 API 2.0 适配)

- ✅ 前后端跑通(后端 17177 + 前端 3008), DeepSeek 驱动 LLM 层
- ✅ 可灵适配 API 2.0(认证 Bearer 单 key / 路径式端点 / 三层请求体), 契约验证走到余额报错
- ✅ 风格预设「新海诚光·2000年代中国」注入 style_presets.json, 后端 API 返回
- ✅ 三主角人设(陈汉升/沈幼楚/萧容鱼)手动注入, 从《我真没想重生啊》小说提取
- ✅ LLM 剧本分析: 小说第一段 → 7 个分镜(景别/运镜/动作到部位级), 导演质量好

### 3. 可灵 API 2.0 契约验证

```
HTTP 429: {"code":1102, "message":"Account balance not enough"}
```

鉴权 ✅(Bearer 被接受, 非 401) / 路径 ✅(/image-to-video/kling-3.0, 非 404) / 格式 ✅(三层 body, 非 400) / 业务层 ✅(余额不足)。充值后即可出片。

### 4. 关键发现

- **可灵实际生成尺寸是 1916×1080, 不足 1920** — 人眼看不出, 但创投申报分辨率规则会打回, qa_tech.py --fix 可自动规整
- **LumenX 部署有 6 个依赖坑**(见 skill lumenx-studio), 已全部解决并记录

## 相关项目

- [kling-prompt-engineering (KPE)](https://github.com/Yuyyxz/kling-prompt-engineering) — 导演级可灵提示词工程库,本工作流的方法论层
- [Master-director](https://github.com/liangie7420/Master-director) — 导演方法论(四大一致性机制/题材执导手册), 已整合为 Hermes skill `master-director`
- [LumenX](https://github.com/alibaba/lumenx) — AI 短剧生产平台, 本地部署 + 可灵 API 2.0 适配(见 skill `lumenx-studio`)

## License

MIT
