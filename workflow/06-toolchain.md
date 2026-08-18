# 工具链 (Toolchain)

> 各环节工具选型。✅=已验证可用, 🔄=推荐方案(待实测), ⛔=不推荐
> 数据来源: GitHub 深挖(2026-08-10) + 本地实测

## 已确认工具链(本地验证过)

### 剧本/文案 — DeepSeek API ✅
- 接口: DeepSeek API(已配置)
- 用途: 剧本、角色卡、分镜 prompt、对白
- 方法论: KPE director-engine(导演五问)
- 注意: 长剧本分段生成, 每段保存到独立文件

### 分镜图 — ChatGPT Image 2 ✅
- 用途: 分镜图生成(画质最高, 一致性靠角色卡逐字复制)
- 工作流: 用户手动生成(Codex中转), 保存到 04-storyboards/images/
- 替代: Midjourney(需要 seed 控制)
- 注意: 可灵图生图画质不达标, 不用

### 图生视频 — 可灵 Kling v3 ✅
- API: https://api-beijing.klingai.com
- 认证: Bearer <KLING_API_KEY>
- 模型: kling-v3 / pro / sound=on
- 参数: duration="5"/"10"/"15", cfg_scale=0.5
- 成本: pro 模式 5s≈¥2, 10s≈¥4, 15s≈¥6
- 注意: 余额不足(code 1102)需先充值

### 拼接/帧提取 — ffmpeg 8.1.1 ✅
- 拼接: concat_videos.py
- 尾帧: extract_frames.py
- 黑帧检测: ffmpeg -vf blackdetect
- 已安装: ffmpeg 8.1.1-full_build

### 精修 — 剪映 / DaVinci ✅
- 用途: 转场、调色、字幕精修
- 用户手动操作

## 深挖结果: 各环节推荐方案

### 中文配音 TTS 🔄 首选: GPT-SoVITS
| 方案 | 项目 | 定位 | 适合度 |
|------|------|------|--------|
| **GPT-SoVITS** ⭐ | RVC-Boss/GPT-SoVITS | 少样本(1min)音色克隆+配音, 可本地 | **首选**: 中文效果最好, 支持角色音色克隆 |
| Fish Speech | fishaudio/fish-speech | 本地 TTS, 多语言 | 备选: 需显卡, 注意 license |
| CosyVoice | FunAudioLLM/CosyVoice | 阿里, 中文强 | 备选 |
| edge-tts | (微软) | 免费云端, 音质一般 | 快速原型用 |
| qianwen TTS | (阿里云) | 你已有 skill | 可先用它出初版 |

**推荐路径**: 初版用 qianwen TTS 快速出片 → 正式版用 GPT-SoVITS 克隆角色音色(需 1min 角色语音样本)

### 背景音乐/音效 🔄
| 方案 | 说明 |
|------|------|
| 可灵 sound=on | 生成环境音效(免费, 已用) |
| Suno AI | 生成 BGM(需账号) |
| 素材库 | 免版权音乐库(如 Pixabay) |
| **注意**: 可灵 audio_prompt 只出音效不出配乐, 完整 BGM 后期叠加 |

### 字幕生成 🔄 首选: pyvideotrans
| 方案 | 项目 | 说明 |
|------|------|------|
| **pyvideotrans** ⭐ | jianchang512/pyvideotrans | 视频翻译/字幕/配音一体, 中文生态 |
| Whisper | openai/whisper | 语音转写基准, 中文需 whisper-large |
| 剪映自动字幕 | (本地) | 中文识别好, 一键 |

**推荐路径**: 剪映自动字幕(快) → 校对 → 导出 srt

### 成片质检 🔄
| 方案 | 说明 |
|------|------|
| ffmpeg blackdetect | 黑帧检测(已有) |
| 人脸一致性 | 抽帧 + 人工对比角色卡(当前) |
| **ai0-video-creator** | 含质量审计工作台, 可参考其 audit 思路 |

### 角色一致性 🔄
| 方案 | 项目 | 说明 |
|------|------|------|
| 角色卡逐字复制 | (已有) | 最基础, 必须做 |
| 参考图锚定 | (已有) | 图生视频用参考图 |
| **StoryDiffusion** | HVision-NKU/StoryDiffusion | Consistent Self-Attention, 学术方案, 可参考 |
| 三视图+表情包 | 借鉴 AIYOU | 角色设计规范, 已写入角色卡模板 |

## 可借鉴的完整工作流项目(深挖结果)

| 项目 | 核心借鉴点 |
|------|-----------|
| **drasstry/shortdrama-pipeline** ⭐ | **人工审核门槛**: 剧本确认后才生成人物, 人物确认后才生成视频(已吸收进质量门禁) |
| yfge/ai-video-studio | Timeline 单一事实源(已吸收: 06-edit/timeline.md) |
| oidahdsah0/llm-script-factory | DTG 短剧理论(爽点/冲突/标签库, 已吸收进剧本大纲模板) |
| yubowen123/AIYOU | 12节点全流程, 角色三视图/九宫格(已吸收进角色卡) |
| krillinai/KrillinAI | 配音翻译(与本项目场景不符, 仅参考) |
| ajoesoft/ai0-video-creator | Tauri 桌面工作台, 质量审计思路(仅参考) |
| Gentleman-Programming/engram | 跨 agent 记忆(与本项目无关, 但理念佐证状态卡方案) |

## 工具链速查

| 环节 | 工具 | 自动化 | 手动 | 状态 |
|------|------|--------|------|------|
| 剧本 | DeepSeek + KPE | ✅ | | ✅ |
| 角色卡 | 模板 + DeepSeek | ✅ | | ✅ |
| 参考图 | Image 2 | | ✅ | ✅ |
| 分镜表 | KPE keyframe-generator | ✅ | | ✅ |
| 分镜图 | Image 2 | | ✅ | ✅ |
| 视频生成 | 可灵 v3 API | ✅ | | ⚠️ 充值 |
| 配音 | qianwen → GPT-SoVITS | 🔄 | | 🔄 |
| BGM/音效 | 可灵sound + Suno/素材库 | 🔄 | | 🔄 |
| 拼接 | ffmpeg | ✅ | | ✅ |
| 精修 | 剪映/DaVinci | | ✅ | ✅ |
| 字幕 | 剪映 → srt | 🔄 | | 🔄 |
| 质检 | ffmpeg + 抽检 | ✅ | ✅ | ✅ |

---

## 方法论分工表(三 skill 协同)

> 工作流执行时, 按环节调用对应 skill, 三者优势互补不重复。

| 环节 | 用哪个 skill | 为什么 |
|------|-------------|--------|
| 流程编排/资产追踪/技术质检 | 工作流(本项目) | 资产编号+状态卡+8阶段+qa_tech.py |
| 剧本工程(标准分镜剧本) | master-director | script-format + 题材情绪曲线 |
| 资产卡/定妆/一致性机制 | master-director | 四大机制(首尾帧/资产卡锁定/关键帧插入) |
| 逐镜提示词精修 | KPE + master-director | KPE 导演五问+Anti-Slop; md 动作幅度+参考图粘性 |
| 拍摄执行/翻车处理 | master-director | 尾帧/首尾帧/翻车矩阵+diagnose.py |
| 提示词交付门禁 | master-director | check_prompt.py(反模式扫描) |
| 成片技术质检 | 工作流 qa_tech.py | 黑帧/冻结/静音/响度/分辨率, 无需视觉 |
| 风格库/负面词库 | KPE | 156条提示词库 + 风格隔离 |

### 三个 skill 的定位边界

- **master-director**(新): 导演方法论 + 一致性机制 + 题材执导手册。管"怎么拍得一致、少抽卡"。
- **KPE**(已有): 提示词工程 + 风格库 + 反空话。管"提示词怎么写得更精准"。
- **工作流**(本项目): 编排 + 资产追踪 + 技术质检。管"流程怎么不丢、资产怎么不乱、成片怎么不翻车"。

### 整合时的关键约定

1. 可灵适配层: **统一走 master-director 的 kling.md(API 2.0 覆盖版)**, KPE 里旧的 kling-v3 版本号不再使用。
2. 一致性机制: 以 master-director 四大机制为准(首尾帧优先 > 视频延长 > 尾帧兜底), KPE 的尾帧续接作为兜底能力保留。
3. 题材: 都市/言情用 master-director 的 genres/urban.md + romance.md; 《我真没想重生啊》属都市言情交叉, 以 romance 为主线 + urban 场景参考。
4. 画风: 高清电影感 + 新海诚式光影 + 2000年代环境细节(不做旧滤镜), 此定位写入风格预设, 三 skill 共用。
