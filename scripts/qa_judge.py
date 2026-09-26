#!/usr/bin/env python3
"""qa_judge.py — VLM-as-judge 视频审美评审 (Gate-B)
用法:
  python qa_judge.py 视频文件 --frames a.png b.png [--prompt "镜头描述"] --level L2 --mock
  python qa_judge.py 视频文件 --level L1 --live        (不给 --frames 时自动抽 帧)
级别 (成本漏斗):
  L0 = 跳过 VLM 评审 (只跑 Gate-A 技术门, 零成本)
  L1 = 抽帧全量粗筛 (单维 overall 等级; 边界分建议进 L2 复审)
  L2 = 逐镜评审 (VideoScore 五维 rubric)
环境变量 (仅 live 需要, 代码与测试不落任何 key):
  QA_JUDGE_BASE_URL  默认 https://dashscope.aliyuncs.com/compatible-mode/v1
  QA_JUDGE_MODEL     默认 qwen-vl-max
  QA_JUDGE_API_KEY   必填 (如: 从 D:\\hermes\\.env 导出)
rubric: VideoScore 五维各 1-4 分 (Visual Quality / Temporal Consistency / Dynamic Degree
        / Text-to-Video Alignment / Factual Consistency)
打分法: Q-Align 离散文本等级——VLM 先输出 excellent/good/fair/poor/bad 再映射 5..1 (比直接要数字稳),
        1-4 制下 poor/bad 合并为 1
prompt: MT-bench single-v1 三段式 (给评分标准 → 给内容 → 强制只输出 JSON)
安全: 默认运行与测试零真实 VLM 请求; 仅显式 --live 才真调; --mock 用确定性假响应
输出: JSON 报告 (<视频名>_qa_judge.json); 退出码 pass=0 / hold=1 / 配置错误=2
"""
import base64
import json
import os
import re
import subprocess
import sys

import requests

DEFAULT_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
DEFAULT_MODEL = "qwen-vl-max"

# VideoScore 五维 (adapt: 维度说明译成漫剧/短剧语境)
DIMENSIONS = {
    "visual_quality": "画面质量——清晰度、畸变、脏斑、构图是否达标",
    "temporal_consistency": "时序一致性——角色形象是否漂移、画面是否闪烁、背景是否跳变",
    "dynamic_degree": "动态程度——动作/运镜幅度是否与镜头意图匹配（不僵硬也不乱动）",
    "text_video_alignment": "文本一致性——画面内容是否吻合镜头文本/prompt 描述",
    "factual_consistency": "事实一致性——道具、服装、常识、物理逻辑是否崩坏",
}
# Q-Align 离散等级 → (Q-Align 1-5 分, VideoScore 1-4 分); poor/bad 在 1-4 制下合并为 1
LEVEL_MAP = {
    "excellent": (5, 4),
    "good": (4, 3),
    "fair": (3, 2),
    "poor": (2, 1),
    "bad": (1, 1),
}

def run(cmd, timeout=120):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout,
                           stdin=subprocess.DEVNULL)
        return r.stdout + r.stderr
    except Exception as e:
        return f"ERR: {e}"

def video_duration(video):
    out = run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
               "-of", "csv=p=0", video], 60)
    try:
        return float(out.strip().splitlines()[-1])
    except Exception:
        return None

def ensure_frames(video, frames, out_dir, max_frames):
    """无显式帧时用 extract_frames.py 的抽帧约定自动取 均匀分布 max_frames 帧"""
    if frames:
        return frames
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from extract_frames import extract_frame
    dur = video_duration(video)
    if not dur:
        raise SystemExit("错误: 无法读视频时长, 请手动给 --frames")
    os.makedirs(out_dir, exist_ok=True)
    times = [round(dur * f, 2) for f in
             [i / (max_frames - 1) for i in range(max_frames)]] if max_frames > 1 else [dur / 2]
    return [extract_frame(video, out_dir, t) for t in times]

def encode_image(path):
    ext = "jpeg" if path.lower().endswith((".jpg", ".jpeg")) else "png"
    with open(path, "rb") as f:
        return f"data:image/{ext};base64,{base64.b64encode(f.read()).decode()}"

def build_prompt(shot_prompt, level):
    """MT-bench single-v1 三段式: [Instruction] 评分标准 → [内容] → 强制只输出 JSON"""
    if level == "L1":
        return (
            "[Instruction]\n"
            "你是一个公正严格的 AI 视频质检评审。请对这段生成视频的抽帧做总体质量粗筛。\n"
            "评分方法：从文本等级 excellent / good / fair / poor / bad 中选一个"
            "（优秀/良好/合格/差/不可用），再用一句话给出理由。\n\n"
            f"[Start of Prompt]\n{shot_prompt}\n[End of Prompt]\n\n"
            "[Start of Frames]\n视频抽帧已按时间顺序附在本消息中。\n[End of Frames]\n\n"
            "请只输出如下 JSON，不要输出任何其他文字：\n"
            '{"overall": {"level": "excellent|good|fair|poor|bad", "reason": "..."}}'
        )
    rubric = "\n".join(f"- {k}: {v}" for k, v in DIMENSIONS.items())
    dims_json = json.dumps(
        {k: {"level": "excellent|good|fair|poor|bad", "reason": "..."} for k in DIMENSIONS},
        ensure_ascii=False)
    return (
        "[Instruction]\n"
        "你是一个公正严格的 AI 视频质检评审。请依据以下五个维度对这段生成视频的抽帧逐维评分：\n"
        f"{rubric}\n"
        "评分方法（离散文本等级法）：对每个维度，先从 excellent / good / fair / poor / bad 中选一个"
        "（分别代表 优秀=4分 / 良好=3分 / 合格=2分 / 差=1分 / 不可用=1分），"
        "再用一句话给出该维度的理由。\n\n"
        f"[Start of Prompt]\n{shot_prompt}\n[End of Prompt]\n\n"
        "[Start of Frames]\n视频抽帧已按时间顺序附在本消息中。\n[End of Frames]\n\n"
        "请只输出如下 JSON，不要输出任何其他文字：\n"
        f"{dims_json}"
    )

def build_messages(prompt, frame_paths):
    content = [{"type": "text", "text": prompt}]
    content += [{"type": "image_url", "image_url": {"url": encode_image(p)}}
                for p in frame_paths]
    return [{"role": "user", "content": content}]

def call_vlm(messages, base_url, model, api_key, timeout=120):
    """OpenAI 兼容 chat/completions 薄客户端 (~15 行)"""
    resp = requests.post(
        f"{base_url.rstrip('/')}/chat/completions",
        headers={"Authorization": f"Bearer {api_key}"},
        json={"model": model, "messages": messages, "temperature": 0.1},
        timeout=timeout)
    resp.raise_for_status()
    data = resp.json()
    return data["choices"][0]["message"]["content"], data.get("usage", {})

MOCK_RESPONSES = {
    "L2": json.dumps({
        "visual_quality": {"level": "good", "reason": "[mock] 画面清晰无明显畸变"},
        "temporal_consistency": {"level": "good", "reason": "[mock] 角色形象稳定不漂移"},
        "dynamic_degree": {"level": "fair", "reason": "[mock] 动作幅度略保守"},
        "text_video_alignment": {"level": "good", "reason": "[mock] 与镜头文本吻合"},
        "factual_consistency": {"level": "good", "reason": "[mock] 无常识/道具崩坏"},
    }, ensure_ascii=False),
    "L1": json.dumps(
        {"overall": {"level": "good", "reason": "[mock] 总体质量良好, 无硬伤"}},
        ensure_ascii=False),
}

def extract_json(text):
    """容忍 markdown 围栏与前后杂文, 抓第一处 {..最后}"""
    text = text.strip()
    text = re.sub(r"^```[a-zA-Z]*\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    i, j = text.find("{"), text.rfind("}")
    if i < 0 or j <= i:
        raise ValueError(f"响应中无 JSON: {text[:200]}")
    return json.loads(text[i:j + 1])

def level_to_scores(level):
    """'good' → {'level','score_qalign':4,'score':3}; 未知等级返回 None"""
    lv = str(level).strip().lower()
    if lv not in LEVEL_MAP:
        return None
    q, v = LEVEL_MAP[lv]
    return {"level": lv, "score_qalign": q, "score": v}

def parse_judgement(raw, level):
    """解析 VLM 输出 → (dimensions|overall, scores, ok)。解析失败返回 (None, raw, False)"""
    try:
        data = extract_json(raw)
    except (ValueError, json.JSONDecodeError):
        return None, raw, False
    if level == "L1":
        sc = level_to_scores((data.get("overall") or {}).get("level", ""))
        if not sc:
            return None, raw, False
        sc["reason"] = (data.get("overall") or {}).get("reason", "")
        return {"overall": sc}, {"overall": sc["score"]}, True
    dims, scores = {}, {}
    for name in DIMENSIONS:
        entry = data.get(name) or {}
        sc = level_to_scores(entry.get("level", ""))
        if not sc:
            return None, raw, False  # 任一维度缺失/等级非法 → 整体不采信
        sc["reason"] = entry.get("reason", "")
        dims[name] = sc
        scores[name] = sc["score"]
    return dims, scores, True

def decide_verdict(scores, min_total, min_dim, level):
    if level == "L1":
        return ("pass", "粗筛达标") if scores["overall"] >= 3 else \
               ("hold", f"粗筛等级不足 good (score={scores['overall']}), 建议进 L2 逐镜复审")
    total = round(sum(scores.values()) / len(scores), 2)
    weak = [f"{k}={v}" for k, v in scores.items() if v < min_dim]
    if total >= min_total and not weak:
        return "pass", f"五维总分 {total} ≥ {min_total} 且无单维低于 {min_dim}"
    return "hold", f"总分 {total} / 弱维 {weak or '—'} 未达阈值 (min_total={min_total}, min_dim={min_dim})"

def run_judge(video, frames=None, prompt=None, level="L2", mode="mock",
              min_total=2.5, min_dim=2.0, max_frames=4, frames_dir=None):
    frames_dir = frames_dir or os.path.dirname(video) or "."
    if mode == "live":
        api_key = os.environ.get("QA_JUDGE_API_KEY", "")
        if not api_key:
            return {"file": video, "tool": "qa_judge", "level": level, "mode": mode,
                    "verdict": "error", "reason": "live 模式需要环境变量 QA_JUDGE_API_KEY",
                    "checks": {}, "issues": ["缺 QA_JUDGE_API_KEY"], "warnings": []}
    frames = ensure_frames(video, frames or [], frames_dir, max_frames)
    prompt = prompt or f"镜头: {os.path.basename(video)}（未提供镜头文本, 以文件名为准）"
    report = {"file": video, "tool": "qa_judge", "level": level, "mode": mode,
              "model": os.environ.get("QA_JUDGE_MODEL", DEFAULT_MODEL),
              "frames": frames, "prompt": prompt,
              "checks": {}, "issues": [], "warnings": []}

    if mode == "live":
        base_url = os.environ.get("QA_JUDGE_BASE_URL", DEFAULT_BASE_URL)
        messages = build_messages(build_prompt(prompt, level), frames)
        raw, usage = call_vlm(messages, base_url, report["model"], api_key)
        report["tokens"] = usage.get("total_tokens")
    else:
        raw = MOCK_RESPONSES[level]

    report["raw_response"] = raw
    dims, scores, ok = parse_judgement(raw, level)
    if not ok:
        report["verdict"] = "hold"
        report["reason"] = "VLM 输出无法解析为合法 rubric JSON, 不采信"
        report["checks"]["rubric_parse"] = "FAIL"
        report["passed"] = False
        return report

    report["checks"]["rubric_parse"] = "PASS"
    if level == "L1":
        report["overall"] = dims["overall"]
    else:
        report["dimensions"] = dims
    report["scores"] = scores
    report["total"] = round(sum(scores.values()) / len(scores), 2) \
        if level == "L2" else scores["overall"]
    verdict, reason = decide_verdict(scores, min_total, min_dim, level)
    report["verdict"] = verdict
    report["reason"] = reason
    report["passed"] = verdict == "pass"
    if verdict == "hold":
        report["issues"].append(reason)
    return report

def main():
    args = sys.argv[1:]
    if not args or args[0] in ("-h", "--help"):
        print(__doc__)
        sys.exit(0 if args else 1)
    video = args[0]
    opts = {"frames": [], "prompt": None, "level": "L2", "mock": False, "live": False,
            "min_total": 2.5, "min_dim": 2.0, "max_frames": 4, "frames_dir": None}
    i = 0
    while i < len(args):
        a = args[i]
        if a == "--frames":
            j = i + 1
            while j < len(args) and not args[j].startswith("--"):
                opts["frames"].append(args[j]); j += 1
            i = j - 1
        elif a == "--prompt" and i + 1 < len(args):
            opts["prompt"] = args[i + 1]; i += 1
        elif a == "--level" and i + 1 < len(args):
            opts["level"] = args[i + 1].upper(); i += 1
        elif a == "--min-total" and i + 1 < len(args):
            opts["min_total"] = float(args[i + 1]); i += 1
        elif a == "--min-dim" and i + 1 < len(args):
            opts["min_dim"] = float(args[i + 1]); i += 1
        elif a == "--max-frames" and i + 1 < len(args):
            opts["max_frames"] = int(args[i + 1]); i += 1
        elif a == "--frames-dir" and i + 1 < len(args):
            opts["frames_dir"] = args[i + 1]; i += 1
        elif a == "--mock":
            opts["mock"] = True
        elif a == "--live":
            opts["live"] = True
        i += 1

    if opts["level"] not in ("L0", "L1", "L2"):
        print(f"错误: --level 只支持 L0/L1/L2, 得到 {opts['level']}")
        sys.exit(2)
    if not os.path.exists(video):
        print(f"错误: 找不到 {video}")
        sys.exit(2)
    if opts["mock"] and opts["live"]:
        print("错误: --mock 与 --live 互斥")
        sys.exit(2)

    # 默认零真实请求: L0 不联网可直跑; L1/L2 必须显式选 --mock 或 --live
    if opts["level"] != "L0" and not opts["mock"] and not opts["live"]:
        print("默认离线: 请显式选择 --mock (确定性假响应, 不发网络请求) 或 --live (真调 VLM)")
        sys.exit(2)

    if opts["level"] == "L0":
        report = {"file": video, "tool": "qa_judge", "level": "L0", "verdict": "skip",
                  "reason": "L0 按成本漏斗跳过 VLM 评审 (仅 Gate-A 技术门)",
                  "checks": {}, "issues": [], "warnings": [], "passed": True}
    else:
        report = run_judge(video, frames=opts["frames"], prompt=opts["prompt"],
                           level=opts["level"],
                           mode="mock" if opts["mock"] else "live",
                           min_total=opts["min_total"], min_dim=opts["min_dim"],
                           max_frames=opts["max_frames"], frames_dir=opts["frames_dir"])

    print("=" * 50)
    print(f"VLM 评审报告: {os.path.basename(video)}  [level={report['level']} mode={report.get('mode', '-')}]")
    print("=" * 50)
    dims_block = report.get("dimensions") or \
        ({"overall": report["overall"]} if "overall" in report else {})
    for dim, sc in dims_block.items():
        if isinstance(sc, dict):
            print(f"  {dim:24s} {sc['level']:10s} score={sc['score']}  {sc.get('reason', '')[:40]}")
    if "total" in report:
        print(f"  {'total':24s} {report['total']}")
    print(f"\n结论: {report['verdict']} — {report.get('reason', report.get('error', '-'))}")

    out = os.path.splitext(video)[0] + "_qa_judge.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"报告已保存: {out}")

    return {"pass": 0, "skip": 0}.get(report["verdict"], 2 if report["verdict"] == "error" else 1)

if __name__ == "__main__":
    sys.exit(main())
