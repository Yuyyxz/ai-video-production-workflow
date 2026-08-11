# AI 长视频生产工作流 (Complete Production Workflow)

> 版本: 1.0 | 适用: 可灵创投项目 / AI短剧 / 电影实验片
> 定位: 从创意到交付的**完全体**生产流水线, 含资产管理

## 这是什么

一个端到端的长视频生产工作流, 解决:
1. **跨会话接力** — 状态卡机制, 每个会话读卡续跑
2. **资产管理** — 一切产物有编号, 可追溯
3. **质量控制** — 8阶段 + 质量门禁
4. **执行落地** — 脚本 + 模板 + 工具链

## 体系结构

```
workflow/
├── 01-asset-numbering.md      ← 资产编号体系(一切资产有唯一编号)
├── 02-project-status-card.md  ← 项目状态卡(跨会话核心)
├── 03-directory-structure.md  ← 目录结构(物理载体)
├── 04-pipeline-stages.md      ← 8阶段流水线定义
├── 05-quality-gates.md        ← 质量门禁(验收标准)
├── 06-toolchain.md            ← 工具链(各环节最佳方案)
├── 07-templates/              ← 模板(角色卡/分镜表/大纲/音色)
└── scripts/                   ← 自动化脚本
    ├── init_project.py        ← 一键初始化项目
    ├── manifest_check.py      ← 资产注册表校验
    ├── kling_generate.py      ← 可灵批量生成
    ├── concat_videos.py       ← 视频拼接
    └── extract_frames.py      ← 尾帧/关键帧提取
```

## 使用流程

```
1. 新项目: python workflow/scripts/init_project.py 项目名
2. 每个会话开始: 读 PROJECT_STATUS.md
3. 按 04-pipeline-stages.md 的 8 阶段推进
4. 每阶段完成: 过质量门禁(05), 更新状态卡
5. 每个会话结束: 更新状态卡 + 资产统计
```

## 8 阶段总览

```
P0 立项 → P1 剧本 → P2 角色/世界观 → P3 分镜
       → P4 素材生成 → P5 音频 → P6 后期 → P7 质检交付
```

## 核心原则

1. **状态卡是入口**: 新会话先读卡, 结束更新卡
2. **manifest.csv 是账本**: 资产必须登记
3. **编号即文件名**: 禁止随意命名
4. **版本只增不改**: 重做开新版本
5. **一切可追溯**: 成片 → 视频 → 关键帧 → 分镜 → 剧本
6. **门禁不过不入下一阶段**

## 工具链速查(详见 06-toolchain.md)

| 环节 | 当前方案 | 状态 |
|------|---------|------|
| 剧本 | DeepSeek + KPE 导演引擎 | ✅ |
| 角色 | 角色卡 + Image2 参考图 | ✅ |
| 分镜 | KPE keyframe-generator | ✅ |
| 素材生成 | 可灵 v3 API | ⚠️ 需充值 |
| 配音 | 调研中 | 🔄 |
| 音乐 | 调研中 | 🔄 |
| 拼接 | ffmpeg | ✅ |
| 字幕 | 调研中 | 🔄 |
| 质检 | ffmpeg blackdetect + 调研中 | 🔄 |
