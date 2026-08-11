# 8阶段流水线定义 (Pipeline Stages)

> 完全体长视频生产流水线: P0 立项 → P7 交付
> 每阶段含: 输入 / 动作 / 输出 / 质量门禁 / 工具

## 总览

```
P0 立项 → P1 剧本 → P2 角色/世界观 → P3 分镜 → P4 素材生成 → P5 音频 → P6 后期 → P7 质检交付
```

## P0 立项 (Project Initiation)

- **输入**: 创意点子 / 申报方向
- **动作**:
  1. 定类型(短剧/动画/实验片)与时长
  2. 写一页纸提案(one-pager)
  3. 定预算(budget.md)与排期(schedule.md)
  4. 初始化项目目录 + PROJECT_STATUS.md
- **输出**: one-pager.md, budget.md, schedule.md, PROJECT_STATUS.md
- **质量门禁**: 一页纸讲得清"这是什么故事, 为什么能拿奖"
- **工具**: init_project.py, DeepSeek

## P1 剧本 (Script)

- **输入**: 一页纸提案
- **动作**:
  1. 故事大纲(outline.md): 世界观/人物弧光/冲突结构
  2. 分集/分场: 每集一个文件
  3. 对白表(dialogue-table.md): 每句对白登记
  4. 标注"首帧来源"决策(tail_frame / storyboard)
- **输出**: outline.md, episode-*.md, dialogue-table.md
- **质量门禁**:
  - 导演五问已回答
  - 有情绪弧线(起承转合)
  - 对白符合角色人设
  - 每场景有首帧来源标注
- **工具**: DeepSeek + KPE director-engine

## P2 角色/世界观 (Characters & World)

- **输入**: 剧本
- **动作**:
  1. 角色卡(character-card.md): 外观英文描述/服装/性格/音色
  2. 参考图集(CHR-XX_refs/): 每个角色多角度
  3. 世界观设定(WLD-01_setting.md)
  4. 场景设定(SCN-XX_refs/)
- **输出**: CHR-XX 角色卡+参考图, WLD/SCN 设定
- **质量门禁**:
  - 角色卡外观描述逐字固定(一致性根基)
  - 每个角色有 2+ 参考图(不同角度)
  - 场景图符合剧本时间线
- **工具**: DeepSeek + Image2/文生图

## P3 分镜 (Storyboard)

- **输入**: 剧本 + 角色/场景设定
- **动作**:
  1. 分镜表(SB-001_table.md): 镜头号/景别/角度/运镜/时长/台词/首帧来源
  2. 生成分镜图(SB-XXX.png)
  3. 人工审核(高精度/有角色镜头必须人工)
- **输出**: SB 分镜表 + 分镜图
- **质量门禁**:
  - 一个镜头 = 一个节拍 = 一个变化
  - 镜头语言符合 KPE 规范(无空话)
  - 角色外观与角色卡一致
- **工具**: KPE keyframe-generator + Image2

## P4 素材生成 (Asset Generation)

- **输入**: 分镜图 + 角色参考
- **动作**:
  1. 准备首帧: 分镜图(storyboard)或上段尾帧(tail_frame)
  2. 组装视频 prompt(只写运动+声音, 不写外貌)
  3. 可灵 v3 批量生成(image2video, sound=on)
  4. 轮询任务 → 下载视频 → 登记 manifest
- **输出**: VD-XX-XXX.mp4 + 尾帧 KF
- **质量门禁**:
  - task_status == succeed
  - 角色脸没变(与参考图对比)
  - 生成失败 → 重试(最多3次) → 换B-Roll
- **工具**: kling_generate.py + KPE motion-director

## P5 音频 (Audio)

- **输入**: 剧本对白表 + 视频素材
- **动作**:
  1. 配音: TTS生成中文配音(AU-VXX)
  2. 音色分配: 每角色固定音色
  3. BGM: 生成/选曲
  4. 音效: 环境音/拟音
- **输出**: AU-V*/AU-B*/AU-S* 音频文件
- **质量门禁**:
  - 中文配音与台词一致
  - 音色与角色卡设定一致
  - 有 BGM + 至少环境音
- **工具**: qianwen-audio-tts / 其他TTS + 音乐生成

## P6 后期 (Post-production)

- **输入**: 视频 + 音频 + 字幕
- **动作**:
  1. 拼接: 按 concat-list.txt 顺序拼接
  2. 转场/剪辑: 剪映/DaVinci 精修
  3. 字幕: 生成 srt + 烧录
  4. 混音: 配音/BGM/音效平衡
- **输出**: FIN-VXX.mp4
- **质量门禁**:
  - 无黑帧/跳变
  - 音画同步
  - 字幕无错字
- **工具**: ffmpeg + 剪映/DaVinci

## P7 质检交付 (QA & Delivery)

- **输入**: 成片 FIN-VXX
- **动作**:
  1. 一致性检查: 角色脸/服装/场景
  2. 成片质检报告(qa-report.md)
  3. 多平台导出: 4K主版/9:16竖屏/字幕
  4. 申报材料打包
- **输出**: 4k-master.mp4, 9x16-vertical.mp4, subtitles.srt
- **质量门禁**:
  - 满足创投硬要求: AI≥50%可灵 / 中文配音 / 原创
  - 全资产可追溯
- **工具**: ffmpeg + 一致性检查脚本

## 阶段间流转规则

- 每阶段完成必须过质量门禁, 未过不得进入下一阶段
- 阶段状态更新到 PROJECT_STATUS.md
- 资产全部登记 manifest.csv
