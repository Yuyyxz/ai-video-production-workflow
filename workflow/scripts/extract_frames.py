#!/usr/bin/env python3
"""extract_frames.py — 尾帧/关键帧提取 (ffmpeg)
用法: python extract_frames.py 视频文件 [输出目录]
提取视频最后一帧, 用于尾帧续接。
"""
import os
import sys
import subprocess

def extract_last_frame(video_path, out_dir="."):
    """提取视频最后一帧"""
    if not os.path.exists(video_path):
        print(f"错误: 找不到 {video_path}")
        sys.exit(1)
    os.makedirs(out_dir, exist_ok=True)

    base = os.path.splitext(os.path.basename(video_path))[0]
    out = os.path.join(out_dir, f"{base}_tail.png")

    # 获取总帧数
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-count_frames", "-select_streams", "v:0",
         "-show_entries", "stream=nb_read_frames", "-of", "csv=p=0", video_path],
        capture_output=True, text=True)
    if probe.returncode != 0 or not probe.stdout.strip():
        print("❌ ffprobe 失败")
        sys.exit(1)
    total = int(probe.stdout.strip())

    cmd = ["ffmpeg", "-y", "-i", video_path,
           "-vf", f"select=eq(n\\,{total-1})", "-vframes", "1", out]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print("❌ ffmpeg 失败:", result.stderr[-300:])
        sys.exit(1)
    print(f"✅ 尾帧: {out}")
    return out

def extract_frame(video_path, out_dir, time_s):
    """提取指定时间点帧"""
    os.makedirs(out_dir, exist_ok=True)
    base = os.path.splitext(os.path.basename(video_path))[0]
    out = os.path.join(out_dir, f"{base}_t{time_s}s.png")
    cmd = ["ffmpeg", "-y", "-ss", str(time_s), "-i", video_path,
           "-frames:v", "1", out]
    subprocess.run(cmd, capture_output=True, text=True, check=True)
    print(f"✅ 关键帧({time_s}s): {out}")
    return out

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python extract_frames.py 视频文件 [输出目录]")
        print("      python extract_frames.py 视频文件 --at 3 [输出目录]  (指定时间)")
        sys.exit(1)
    video = sys.argv[1]
    if "--at" in sys.argv:
        idx = sys.argv.index("--at")
        t = float(sys.argv[idx + 1])
        out_dir = sys.argv[idx + 2] if len(sys.argv) > idx + 2 else "."
        extract_frame(video, out_dir, t)
    else:
        out_dir = sys.argv[2] if len(sys.argv) > 2 else "."
        extract_last_frame(video, out_dir)
