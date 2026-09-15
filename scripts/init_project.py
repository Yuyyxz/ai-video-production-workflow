#!/usr/bin/env python3
"""init_project.py — 一键初始化长视频生产项目
用法: python init_project.py 项目名 [--type 短剧|动画|实验片] [--duration 300]
示例: python init_project.py my-drama --type 短剧集 --duration 600
"""
import os
import sys
import shutil
import datetime

WORKFLOW_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # ai-project/workflow/
BASE_DIR = os.path.dirname(WORKFLOW_DIR)  # ai-project/

def main():
    if len(sys.argv) < 2:
        print("用法: python init_project.py 项目名 [--type TYPE] [--duration SECONDS]")
        sys.exit(1)

    name = sys.argv[1]
    proj_type = "短剧集"
    duration = 300
    args = sys.argv[2:]
    for i, a in enumerate(args):
        if a == "--type" and i + 1 < len(args):
            proj_type = args[i + 1]
        if a == "--duration" and i + 1 < len(args):
            duration = int(args[i + 1])

    proj_dir = os.path.join(BASE_DIR, name)
    if os.path.exists(proj_dir):
        print(f"错误: {proj_dir} 已存在")
        sys.exit(1)

    dirs = [
        "00-planning", "01-script", "02-characters", "03-world",
        "04-storyboards/images", "05-assets/keyframes",
        "05-assets/videos", "05-assets/audio/voice", "05-assets/audio/bgm",
        "05-assets/audio/sfx", "05-assets/subtitles",
        "06-edit/versions", "07-qa", "08-delivery",
    ]
    for d in dirs:
        os.makedirs(os.path.join(proj_dir, d), exist_ok=True)

    today = datetime.date.today().isoformat()

    # PROJECT_STATUS.md
    status = f"""# 项目状态卡

## 项目元数据

| 字段 | 值 |
|------|-----|
| 项目编号 | PRJ-XXX |
| 项目名称 | {name} |
| 类型 | {proj_type} |
| 总时长目标 | {duration}秒 |
| 画幅 | 16:9 |
| 模型配置 | kling-v3 / pro / sound=on |
| 申报状态 | 剧本开发阶段 |
| 开始日期 | {today} |
| 截止日期 | |
| 当前阶段 | P0 立项 |

## 项目一句话


## 阶段进度

| 阶段 | 状态 | 完成日期 | 关键产出 | 备注 |
|------|------|---------|---------|------|
| P0 立项 | 🔄 | | | |
| P1 剧本 | ☐ | | | |
| P2 角色/世界观 | ☐ | | | |
| P3 分镜 | ☐ | | | |
| P4 素材生成 | ☐ | | | |
| P5 音频 | ☐ | | | |
| P6 后期 | ☐ | | | |
| P7 质检交付 | ☐ | | | |

## 当前进行中

- 正在做什么: 立项
- 上次会话结束位置: -
- 下一步动作: 写一页纸提案
- 阻塞项: -

## 资产统计

| 类型 | 总数 | 已完成 | 失败/重试 | 成本累计 |
|------|------|--------|----------|---------|
| 分镜图 | 0 | 0 | 0 | 0 |
| 视频 | 0 | 0 | 0 | 0 |
| 音频 | 0 | 0 | 0 | 0 |
| 字幕 | 0 | 0 | 0 | 0 |
"""
    with open(os.path.join(proj_dir, "PROJECT_STATUS.md"), "w", encoding="utf-8") as f:
        f.write(status)

    # manifest.csv header
    manifest = "asset_id,type,description,source,status,created_at,updated_at,cost,note\n"
    with open(os.path.join(proj_dir, "05-assets", "manifest.csv"), "w", encoding="utf-8") as f:
        f.write(manifest)

    # README.md
    readme = f"""# {name}

{proj_type} | {duration}秒 | 开始于 {today}

工作流: 见 `../workflow/` 目录
状态: 见 `PROJECT_STATUS.md`
"""
    with open(os.path.join(proj_dir, "README.md"), "w", encoding="utf-8") as f:
        f.write(readme)

    print(f"✅ 项目已创建: {proj_dir}")
    print(f"   类型: {proj_type} | 时长: {duration}秒")
    print(f"   下一步: 打开 PROJECT_STATUS.md, 开始 P0 立项")

if __name__ == "__main__":
    main()
