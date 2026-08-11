# 长视频生产工作流 — 资产编号体系 (Asset Numbering System)

> 版本: 1.0 | 适用: 可灵AI创投项目 / AI短剧 / 电影实验片
> 原则: 一切产物都是资产, 一切资产都有唯一编号, 一切编号可追溯

## 资产类型前缀

| 前缀 | 类型 | 内容 | 示例 |
|------|------|------|------|
| PRJ | 项目 | 整个项目的元数据/状态卡 | PRJ-001 |
| WLD | 世界观 | 设定集、时间线、地理 | WLD-01 |
| SCR | 剧本 | 大纲/分集/分场/对白 | SCR-001 |
| CHR | 角色 | 角色卡、三视图、参考图集 | CHR-01 |
| SCN | 场景 | 场景设定、环境参考 | SCN-01 |
| PRO | 道具 | 关键道具设定 | PRO-01 |
| STY | 风格 | 风格参考、色彩脚本 | STY-01 |
| SB | 分镜 | 分镜表、分镜图 | SB-001 |
| KF | 关键帧 | 首帧/尾帧图 | KF-01-001 |
| VD | 视频 | 生成的视频片段 | VD-01-001 |
| AU | 音频 | 配音/BGM/音效/混音 | AU-V01-001 |
| SUB | 字幕 | 字幕文件 | SUB-001 |
| FIN | 成片 | 最终输出 | FIN-V01 |
| LOG | 日志 | 生成记录/成本/踩坑 | LOG-001 |

## 编号规则

```
{类型}-{项目号}-{序列号}
```

- 项目号: 项目编号(001起)或角色/场景编号
- 序列号: 该类型下从 001 递增
- 版本: 追加 `-V{n}` (V01, V02...)

示例:
- `CHR-01-V02` = 角色1的参考图 第2版
- `SB-001` = 分镜表第1个镜头
- `KF-01-001` = 角色1的第1个关键帧
- `VD-01-003` = 视频资产中角色/场景1的第3段
- `AU-V01-002` = 配音第1版第2段

## 文件命名规范

```
{资产编号}_{描述}.{ext}
```

示例:
- `CHR-01_V02_ringo_front.png` — 角色1第2版正面图
- `SB-012_classroom_reveal.png` — 分镜12教室揭示镜头
- `VD-01-003_tail_frame.png` — 视频1-3的尾帧

## 状态机 (所有资产共用)

```
draft(草稿) → approved(已批准) → in_production(生产中) → done(完成) → archived(归档)
                              ↘ failed(失败) → retry(重试)
```

| 状态 | 含义 | 可流转到 |
|------|------|---------|
| draft | 刚创建未审核 | approved, failed |
| approved | 人工/AI审核通过 | in_production, draft |
| in_production | 正在生成/处理中 | done, failed |
| done | 生成完成已验证 | archived |
| failed | 生成失败 | retry, draft |
| retry | 重试中 | in_production, failed |
| archived | 已归档 | - |

## 资产注册表 (assets/manifest.csv)

每创建一个资产, 必须登记:

```csv
asset_id,type,description,source,status,created_at,updated_at,cost,note
CHR-01,character,女主林檎角色卡,script,approved,2026-08-10,2026-08-10,0,来自剧本
SB-001,storyboard,教室开场镜头,approved_keyframes,approved,2026-08-10,2026-08-10,0,人工审核通过
VD-01-001,video,教室开场5s,done,2026-08-10,2026-08-10,2积分,kling-v3 pro
```

## 追溯链

```
成片 FIN → 视频 VD → 关键帧 KF → 分镜 SB → 剧本 SCR → 角色 CHR
```

任何环节出问题, 沿追溯链回查根因:
- 成片画质差 → 查 VD 生成参数
- 角色脸变 → 查 CHR 参考图 + KF 首帧来源
- 节奏不对 → 查 SB 分镜表 + SCR 剧本
