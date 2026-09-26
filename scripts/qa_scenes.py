#!/usr/bin/env python3
"""qa_scenes.py — 镜头切点/音画时长/尾静音 质检 (Gate-A 补充项)
用法: python qa_scenes.py 视频文件 [--max-cuts 1] [--av-tolerance 0.5] [--trailing-silence 2.0]
检测项:
  1. 镜头切点: PySceneDetect ContentDetector(threshold=27.0), 每个生成 shot 切点数 > max-cuts 判异常
     (生成镜头理论上只应有 0~1 个切点, >1 = 镜头内意外跳变)
  2. 音画时长差: ffprobe 分别取音/视频流 duration, |差| > av-tolerance 判 fail
  3. 尾静音: silencedetect 末尾静音 > trailing-silence 秒 → 警告 (TTS 尾巴截断信号)
依赖: pip install scenedetect (BSD-3, 会带 opencv-python); 未装时仅跳过切点项, 其余照常
输出: JSON 报告 + 通过/失败判定, 报告结构与 qa_tech.py 同构
"""
import json
import os
import re
import subprocess
import sys

def run(cmd, timeout=180):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout,
                           stdin=subprocess.DEVNULL)
        return r.stdout + r.stderr
    except Exception as e:
        return f"ERR: {e}"

def detect_cuts(video, threshold=27.0):
    """返回切点时间点列表; scenedetect 未安装返回 None"""
    try:
        from scenedetect import ContentDetector, detect
    except ImportError:
        return None
    scene_list = detect(video, ContentDetector(threshold=threshold))
    # 场景边界即切点: n 个场景 → n-1 个切点; 无切点视频 scene_list 为空 → 0
    return [round(nxt[0].seconds, 3) for _, nxt in zip(scene_list, scene_list[1:])]

def stream_durations(video):
    """返回 (视频流时长, 音频流时长), 取不到的为 None; 流缺失时回退容器时长"""
    probe = run(["ffprobe", "-v", "error", "-show_entries",
                 "stream=codec_type,duration:format=duration", "-of", "json", video], 60)
    info = json.loads(probe)
    fmt_dur = float(info.get("format", {}).get("duration") or 0) or None
    v_dur = a_dur = None
    for s in info.get("streams", []):
        d = s.get("duration") or fmt_dur
        d = float(d) if d else None
        if s.get("codec_type") == "video" and v_dur is None:
            v_dur = d
        elif s.get("codec_type") == "audio" and a_dur is None:
            a_dur = d
    return v_dur, a_dur

def trailing_silence_seconds(video, file_duration, noise_db=-50, min_silence=2.0):
    """末尾静音时长(秒); 无静音段返回 0.0"""
    out = run(["ffmpeg", "-nostdin", "-v", "info", "-i", video, "-af",
               f"silencedetect=noise={noise_db}dB:d={min_silence}", "-f", "null", "-"])
    if out.startswith("ERR:"):
        return 0.0
    starts = [float(m) for m in re.findall(r"silence_start:\s*([\d.]+)", out)]
    segs = [(float(s), float(e), float(d)) for s, e, d in
            zip(re.findall(r"silence_start:\s*([\d.]+)", out),
                re.findall(r"silence_end:\s*([\d.]+)", out),
                re.findall(r"silence_duration:\s*([\d.]+)", out))]
    if not starts:
        return 0.0
    last_start = starts[-1]
    if segs and abs(segs[-1][0] - last_start) < 0.05:
        # 最后一段静音有明确的 end (ffmpeg 在 EOF 时也会补 silence_end)
        s, e, d = segs[-1]
        # 仅当静音延续到文件末尾才算"尾静音"; 中段静音不算
        return round(d, 3) if e >= (file_duration or e) - 0.5 else 0.0
    # 有 silence_start 无对应 end → 静音持续到 EOF
    return round(max((file_duration or 0) - last_start, 0.0), 3)

def run_qa(video, max_cuts=1, av_tolerance=0.5, trailing_silence_limit=2.0):
    report = {"file": video, "tool": "qa_scenes", "checks": {},
              "passed": True, "issues": [], "warnings": []}

    # 1. 镜头切点数
    cuts = detect_cuts(video)
    if cuts is None:
        report["checks"]["scene_cuts"] = "SKIP (scenedetect 未安装: pip install scenedetect)"
        report["warnings"].append("scenedetect 未安装, 跳过切点检测")
    else:
        n = len(cuts)
        report["scene_cuts"] = n
        report["cut_points"] = cuts
        if n > max_cuts:
            report["issues"].append(f"镜头切点过多: {n} 个 (阈值 ≤{max_cuts}), 疑似镜头内意外跳变 @ {cuts}")
            report["passed"] = False
        report["checks"]["scene_cuts"] = "PASS" if n <= max_cuts else f"FAIL ({n}个切点)"

    # 2. 音画时长差
    v_dur, a_dur = stream_durations(video)
    report["video_duration"] = v_dur
    report["audio_duration"] = a_dur
    if v_dur is None:
        report["checks"]["av_duration"] = "SKIP (无视频流)"
    elif a_dur is None:
        report["checks"]["av_duration"] = "SKIP (无音轨)"
    else:
        diff = abs(a_dur - v_dur)
        report["av_diff"] = round(diff, 3)
        if diff > av_tolerance:
            report["issues"].append(f"音画时长差过大: |{a_dur:.2f}-{v_dur:.2f}|={diff:.2f}s > {av_tolerance}s")
            report["passed"] = False
        report["checks"]["av_duration"] = "PASS" if diff <= av_tolerance else f"FAIL ({diff:.2f}s)"

    # 3. 尾静音
    if a_dur is None:
        report["checks"]["trailing_silence"] = "SKIP (无音轨)"
    else:
        tail = trailing_silence_seconds(video, file_duration=v_dur or a_dur)
        report["trailing_silence_s"] = tail
        if tail > trailing_silence_limit:
            report["warnings"].append(f"末尾静音 {tail:.2f}s > {trailing_silence_limit}s (TTS 尾巴截断信号)")
        report["checks"]["trailing_silence"] = \
            "PASS" if tail <= trailing_silence_limit else f"WARN ({tail:.2f}s)"

    return report

def main():
    if len(sys.argv) < 2:
        print("用法: python qa_scenes.py 视频文件 [--max-cuts 1] [--av-tolerance 0.5] [--trailing-silence 2.0]")
        sys.exit(1)
    video = sys.argv[1]
    opts = {"max_cuts": 1, "av_tolerance": 0.5, "trailing_silence_limit": 2.0}
    key_map = {"--max-cuts": "max_cuts", "--av-tolerance": "av_tolerance",
               "--trailing-silence": "trailing_silence_limit"}
    args = sys.argv[2:]
    for i, a in enumerate(args):
        if a in key_map and i + 1 < len(args):
            opts[key_map[a]] = float(args[i + 1])

    if not os.path.exists(video):
        print(f"错误: 找不到 {video}")
        sys.exit(1)

    report = run_qa(video, **opts)

    print("=" * 50)
    print(f"镜头/音画质检报告: {os.path.basename(video)}")
    print("=" * 50)
    for k, v in report["checks"].items():
        print(f"  {k:18s} {v}")
    for k in ("scene_cuts", "video_duration", "audio_duration", "av_diff", "trailing_silence_s"):
        if k in report:
            print(f"  {k:18s} {report[k]}")
    if report["issues"]:
        print("\n❌ 问题:")
        for issue in report["issues"]:
            print(f"  - {issue}")
    if report["warnings"]:
        print("\n⚠️ 警告:")
        for w in report["warnings"]:
            print(f"  - {w}")
    print(f"\n结论: {'✅ 通过' if report['passed'] else '❌ 未通过'}")

    out = os.path.splitext(video)[0] + "_qa_scenes.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"报告已保存: {out}")

    return 0 if report["passed"] else 1

if __name__ == "__main__":
    sys.exit(main())
