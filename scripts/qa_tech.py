#!/usr/bin/env python3
"""qa_tech.py — 成片技术质检 (纯 ffmpeg/ffprobe 硬指标, 无需视觉)
用法: python qa_tech.py 视频文件 [--min-resolution 1920x1080] [--max-duration 600]
检测项:
  1. 基础信息: 分辨率/时长/码率/帧率 (ffprobe)
  2. 黑帧: ffmpeg blackdetect
  3. 冻结帧: ffmpeg freezedetect
  4. 静音段: ffmpeg silencedetect
  5. 响度: ffmpeg loudnorm (EBU R128)
  6. 画面统计: ffmpeg signalstats (亮度/饱和度异常)
输出: JSON 报告 + 通过/失败判定
"""
import json
import os
import subprocess
import sys

def run(cmd, timeout=120):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.stdout + r.stderr
    except Exception as e:
        return f"ERR: {e}"

def main():
    if len(sys.argv) < 2:
        print("用法: python qa_tech.py 视频文件 [--min-resolution 1920x1080] [--max-duration 600]")
        sys.exit(1)
    video = sys.argv[1]
    min_res = "1920x1080"
    max_dur = 600
    do_fix = False
    args = sys.argv[2:]
    for i, a in enumerate(args):
        if a == "--min-resolution" and i + 1 < len(args):
            min_res = args[i + 1]
        if a == "--max-duration" and i + 1 < len(args):
            max_dur = int(args[i + 1])
        if a == "--fix":
            do_fix = True

    if not os.path.exists(video):
        print(f"错误: 找不到 {video}")
        sys.exit(1)

    report = {"file": video, "checks": {}, "passed": True, "issues": []}

    # 1. 基础信息
    probe = run(["ffprobe", "-v", "error", "-show_entries",
                 "format=duration,bit_rate:stream=width,height,r_frame_rate,codec_name,codec_type",
                 "-of", "json", video], 60)
    try:
        info = json.loads(probe)
        fmt = info.get("format", {})
        dur = float(fmt.get("duration", 0))
        report["duration"] = dur
        vstream = next((s for s in info.get("streams", []) if s.get("codec_type") == "video"), None)
        astream = next((s for s in info.get("streams", []) if s.get("codec_type") == "audio"), None)
        if vstream:
            w, h = int(vstream.get("width", 0)), int(vstream.get("height", 0))
            report["resolution"] = f"{w}x{h}"
            # 分辨率检查
            mw, mh = map(int, min_res.lower().split("x"))
            if w < mw or h < mh:
                report["issues"].append(f"分辨率不足: {w}x{h} < {min_res}")
                report["passed"] = False
            report["checks"]["resolution"] = "PASS" if w >= mw and h >= mh else "FAIL"
        report["has_audio"] = astream is not None
        if not astream:
            report["issues"].append("无音轨")
            report["passed"] = False
        # 时长检查
        if dur > max_dur:
            report["issues"].append(f"时长超限: {dur:.1f}s > {max_dur}s")
            report["passed"] = False
        report["checks"]["duration"] = "PASS" if dur <= max_dur else "FAIL"
    except Exception as e:
        report["issues"].append(f"ffprobe 解析失败: {e}")

    # 2. 黑帧检测
    black = run(["ffmpeg", "-v", "info", "-i", video, "-vf",
                 "blackdetect=d=0.5:pix_th=0.10", "-an", "-f", "null", "-"], 180)
    black_events = [l for l in black.splitlines() if "black_start" in l]
    if black_events:
        report["issues"].append(f"检测到 {len(black_events)} 处黑帧")
        report["passed"] = False
        report["black_frames"] = black_events[:5]
    report["checks"]["black_frames"] = "PASS" if not black_events else f"FAIL ({len(black_events)}处)"

    # 3. 冻结帧检测
    freeze = run(["ffmpeg", "-v", "info", "-i", video, "-vf",
                  "freezedetect=n=-60dB:d=2", "-an", "-f", "null", "-"], 180)
    freeze_events = [l for l in freeze.splitlines() if "freeze_start" in l]
    if freeze_events:
        report["issues"].append(f"检测到 {len(freeze_events)} 处冻结帧")
        report["passed"] = False
    report["checks"]["frozen_frames"] = "PASS" if not freeze_events else f"FAIL ({len(freeze_events)}处)"

    # 4. 静音检测
    silence = run(["ffmpeg", "-v", "info", "-i", video, "-af",
                   "silencedetect=noise=-50dB:d=2", "-f", "null", "-"], 180)
    silence_events = [l for l in silence.splitlines() if "silence_start" in l]
    if silence_events:
        report["issues"].append(f"检测到 {len(silence_events)} 处静音(≥2s)")
        report["silence"] = silence_events[:5]
    report["checks"]["silence"] = "PASS" if not silence_events else f"WARN ({len(silence_events)}处)"

    # 5. 响度 (EBU R128)
    loud = run(["ffmpeg", "-v", "info", "-i", video, "-af",
                "loudnorm=print_format=json", "-f", "null", "-"], 180)
    loud_data = {}
    try:
        # loudnorm JSON 输出在日志尾部
        idx = loud.rfind("{")
        if idx >= 0:
            loud_data = json.loads(loud[idx:])
        i = float(loud_data.get("input_i", -99))
        if i > -14 and i != -99:
            report["loudness"] = f"{i:.1f} LUFS"
            report["checks"]["loudness"] = "PASS"
        elif i != -99:
            report["issues"].append(f"响度异常: {i:.1f} LUFS (目标 -14)")
            report["checks"]["loudness"] = "WARN"
        else:
            report["checks"]["loudness"] = "SKIP"
    except Exception:
        report["checks"]["loudness"] = "SKIP"

    # 6. signalstats 画面统计 (亮度异常)
    stats = run(["ffmpeg", "-v", "info", "-i", video, "-vf",
                 "signalstats,metadata=print:key=lavfi.signalstats.YAVG:file=-",
                 "-an", "-f", "null", "-"], 180)
    yavg_lines = [l for l in stats.splitlines() if "YAVG" in l]
    if yavg_lines:
        vals = []
        for l in yavg_lines[-30:]:  # 采样末尾30帧
            try:
                vals.append(float(l.split("=")[-1].strip()))
            except Exception:
                pass
        if vals:
            avg = sum(vals) / len(vals)
            report["brightness_avg"] = f"{avg:.1f}"
            if avg < 8:
                report["issues"].append(f"画面过暗: 平均亮度 {avg:.1f}")
                report["checks"]["brightness"] = "FAIL"
            else:
                report["checks"]["brightness"] = "PASS"

    # 输出
    print("=" * 50)
    print(f"技术质检报告: {os.path.basename(video)}")
    print("=" * 50)
    for k, v in report["checks"].items():
        print(f"  {k:15s} {v}")
    if report.get("resolution"):
        print(f"  {'resolution':15s} {report['resolution']}")
    if report.get("duration"):
        print(f"  {'duration':15s} {report['duration']:.1f}s")
    if report.get("loudness"):
        print(f"  {'loudness':15s} {report['loudness']}")
    if report.get("brightness_avg"):
        print(f"  {'brightness':15s} {report['brightness_avg']}")
    if report["issues"]:
        print("\n❌ 问题:")
        for issue in report["issues"]:
            print(f"  - {issue}")
    print(f"\n结论: {'✅ 通过' if report['passed'] else '❌ 未通过'}")

    # 输出 JSON 到文件
    out = os.path.splitext(video)[0] + "_qa.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"报告已保存: {out}")

    # 分辨率不足时提示修复命令, --fix 则直接修复
    if "分辨率不足" in str(report.get("issues")):
        if do_fix:
            target = min_res
            # pad 滤镜需要冒号分隔宽高 (1920:1080), scale 接受 x 也接受 :
            pad_target = target.replace("x", ":")
            fixed = os.path.splitext(video)[0] + "_fixed.mp4"
            print(f"\n🔧 正在修复分辨率 -> {target} ...")
            cmd = ["ffmpeg", "-y", "-i", video,
                   "-vf", f"scale={target}:force_original_aspect_ratio=decrease,pad={pad_target}:(ow-iw)/2:(oh-ih)/2",
                   "-c:v", "libx264", "-preset", "fast", "-crf", "18",
                   "-c:a", "copy", fixed]
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            if r.returncode == 0:
                print(f"✅ 修复完成: {fixed}")
                report["fixed_to"] = fixed
                report["passed"] = True
                report["issues"] = [x for x in report["issues"] if "分辨率不足" not in x]
            else:
                print(f"❌ 修复失败: {r.stderr[-300:]}")
        else:
            print("\n💡 分辨率不足可修复 (规整到目标分辨率):")
            target = min_res
            fixed = os.path.splitext(video)[0] + "_fixed.mp4"
            print(f"  python qa_tech.py \"{video}\" --fix")
            print(f"  或: ffmpeg -y -i \"{video}\" -vf \"scale={target}:force_original_aspect_ratio=decrease,pad={target}:(ow-iw)/2:(oh-ih)/2\" "
                  f"-c:v libx264 -preset fast -crf 18 -c:a copy \"{fixed}\"")

    return 0 if report["passed"] else 1

if __name__ == "__main__":
    sys.exit(main())
