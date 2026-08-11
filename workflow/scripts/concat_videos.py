#!/usr/bin/env python3
"""concat_videos.py — 视频拼接 (ffmpeg)
用法: python concat_videos.py 项目目录
读取 06-edit/concat-list.txt, 按顺序拼接:
  # 注释
  SB-001_video.mp4
  SB-002_video.mp4
输出: 06-edit/versions/FIN-VXX.mp4
"""
import os
import sys
import subprocess

def main():
    if len(sys.argv) < 2:
        print("用法: python concat_videos.py 项目目录")
        sys.exit(1)
    proj = os.path.abspath(sys.argv[1])
    concat_list = os.path.join(proj, "06-edit", "concat-list.txt")
    videos_dir = os.path.join(proj, "05-assets", "videos")
    versions_dir = os.path.join(proj, "06-edit", "versions")

    if not os.path.exists(concat_list):
        print(f"错误: 找不到 {concat_list}")
        sys.exit(1)
    os.makedirs(versions_dir, exist_ok=True)

    files = []
    with open(concat_list, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            files.append(line)

    if not files:
        print("错误: concat-list.txt 为空")
        sys.exit(1)

    # 检查文件
    missing = [fn for fn in files if not os.path.exists(os.path.join(videos_dir, fn))]
    if missing:
        print("❌ 缺少文件:")
        for m in missing:
            print(f"  - {m}")
        sys.exit(1)

    # 生成 concat 文件
    concat_file = os.path.join(proj, "06-edit", "concat_ffmpeg.txt")
    with open(concat_file, "w", encoding="utf-8") as f:
        for fn in files:
            f.write(f"file '{os.path.join(videos_dir, fn)}'\n")

    # 确定版本号
    existing = [x for x in os.listdir(versions_dir) if x.startswith("FIN-V")]
    next_v = len(existing) + 1
    out = os.path.join(versions_dir, f"FIN-V{next_v:02d}.mp4")

    print(f"=== 拼接 {len(files)} 个视频 ===")
    print(f"输出: {out}")

    cmd = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0",
        "-i", concat_file,
        "-c", "copy",
        out,
    ]
    print(" ".join(cmd))
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print("❌ ffmpeg 失败:")
        print(result.stderr[-500:])
        sys.exit(1)

    print(f"✅ 完成: {out}")
    print(f"  大小: {os.path.getsize(out) / 1024 / 1024:.1f} MB")

if __name__ == "__main__":
    main()
