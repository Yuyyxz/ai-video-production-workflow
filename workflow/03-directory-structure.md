# 项目目录结构 (Project Directory Structure)

> 每个项目一个目录: `ai-project/{项目名}/`
> 完全体工作流的物理载体, 所有资产按编号落盘

## 目录树

```
ai-project/
├── workflow/                          ← 工作流定义(本目录, 全项目共享)
│   ├── 01-asset-numbering.md          ← 资产编号体系
│   ├── 02-project-status-card.md      ← 项目状态卡模板
│   ├── 03-directory-structure.md      ← 本文件
│   ├── 04-pipeline-stages.md          ← 8阶段流水线定义
│   ├── 05-quality-gates.md            ← 质量门禁/验收标准
│   ├── 06-toolchain.md                ← 工具链配置(待调研填充)
│   ├── 07-templates/                  ← 各类模板
│   │   ├── character-card.md          ← 角色卡
│   │   ├── script-outline.md          ← 剧本大纲
│   │   ├── episode-script.md          ← 分集剧本
│   │   ├── one-pager.md               ← 一页纸提案
│   │   ├── dialogue-table.md          ← 对白总表
│   │   ├── storyboard-table.md        ← 分镜表
│   │   ├── scene-setting.md           ← 场景设定
│   │   ├── timeline.md                ← 时间线(SSOT)
│   │   ├── voice-casting.md           ← 音色分配表
│   │   └── qa-report.md               ← 质检报告
│   └── scripts/                       ← 自动化脚本
│       ├── init_project.py            ← 一键初始化项目
│       ├── manifest_check.py          ← 资产注册表校验
│       ├── kling_generate.py          ← 可灵批量生成
│       ├── extract_frames.py          ← 尾帧提取
│       └── concat_videos.py           ← 视频拼接

└── {项目名}/                           ← 单项目(PRJ-XXX)
    ├── PROJECT_STATUS.md              ← 项目状态卡(跨会话核心)
    ├── README.md                      ← 项目说明
    ├── 00-planning/                   ← P0 立项
    │   ├── one-pager.md               ← 一页纸提案
    │   ├── budget.md                  ← 预算表
    │   └── schedule.md                ← 排期表
    ├── 01-script/                     ← P1 剧本
    │   ├── outline.md                 ← 故事大纲
    │   ├── episode-01.md              ← 分集剧本(每集一个文件)
    │   └── dialogue-table.md          ← 对白总表
    ├── 02-characters/                 ← P2 角色
    │   ├── CHR-01_character-card.md   ← 角色卡(含英文外观描述)
    │   ├── CHR-01_refs/               ← 参考图集
    │   └── CHR-01_three-view.png      ← 三视图(可选)
    ├── 03-world/                      ← P2 世界观/场景
    │   ├── WLD-01_setting.md          ← 世界观设定
    │   └── SCN-01_refs/               ← 场景参考图
    ├── 04-storyboards/                ← P3 分镜
    │   ├── SB-001_table.md            ← 分镜表
    │   └── images/                    ← 分镜图
    │       ├── SB-001.png
    │       └── SB-002.png
    ├── 05-assets/                     ← P4 素材
    │   ├── manifest.csv               ← 资产注册表(核心)
    │   ├── keyframes/                 ← 首尾帧
    │   ├── videos/                    ← 生成视频(VD-*)
    │   ├── audio/                     ← 音频(AU-*)
    │   │   ├── voice/                 ← 配音
    │   │   ├── bgm/                   ← 背景音乐
    │   │   └── sfx/                   ← 音效
    │   └── subtitles/                 ← 字幕(SUB-*)
    ├── 06-edit/                       ← P5/P6 后期
    │   ├── timeline.md                ← 时间线(Timeline SSOT)
    │   ├── concat-list.txt            ← 拼接顺序清单
    │   └── versions/                  ← 成片版本
    │       ├── FIN-V01.mp4
    │       └── FIN-V02.mp4
    ├── 07-qa/                         ← P7 质检
    │   ├── qa-report.md               ← 质检报告
    │   └── consistency-check.md       ← 一致性检查记录
    └── 08-delivery/                   ← 交付
        ├── 4k-master.mp4              ← 主交付
        ├── 9x16-vertical.mp4          ← 竖屏版
        └── subtitles.srt              ← 字幕文件
```

## 核心规则

1. **状态卡是入口**: 新会话先读 `PROJECT_STATUS.md`, 结束更新
2. **manifest.csv 是账本**: 每个资产必须登记, 禁止有文件无登记
3. **编号即文件名**: 文件名以资产编号开头, 禁止随意命名
4. **版本只增不改**: 重做就开新版本号, 不覆盖旧版本
5. **一切可追溯**: 成片 → 视频 → 关键帧 → 分镜 → 剧本

## 初始化

```bash
# 一键创建新项目
python workflow/scripts/init_project.py 项目名
```

## 与现有资产的关系

- KPE 仓库 (`C:\Users\YY\kling-prompt-engineering`): 方法论层, 不在此工作流内
- kling-drama skill (`D:\hermes\skills\creative\kling-drama`): 执行参考, 含模板
- 本工作流是两者的落地执行层
