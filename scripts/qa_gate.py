#!/usr/bin/env python3
"""qa_gate.py — 质量门禁串联 CLI (Gate-A 技术门 → Gate-B 审美门)
用法:
  python qa_gate.py 资产1.mp4 [资产2.mp4 ...] [--level L2] --mock
  python qa_gate.py shot_*.mp4 --level L0                     (仅 Gate-A, 零成本)
流程:
  Gate-A: qa_tech.py + qa_scenes.py 逐资产全量跑 (ffmpeg, 零成本, 硬失败)
          → 任一 FAIL 判 fail, 不进 Gate-B (不花 VLM 钱)
  Gate-B: qa_judge.py 按成本漏斗评审 (L0 跳过 / L1 抽帧粗筛 / L2 逐镜五维)
汇总: 每资产 pass/hold/fail + 扣分明细; 报告 JSON 落盘
退出码: 全 pass=0 / 有 hold=1 / 有 fail=2
"""
import datetime
import glob
import json
import os
import subprocess
import sys

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))

def run_script(name, args, timeout=600):
    cmd = [sys.executable, os.path.join(SCRIPTS_DIR, name)] + args
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout,
                           stdin=subprocess.DEVNULL)
        return r.returncode, r.stdout + r.stderr
    except Exception as e:
        return 1, f"ERR: {e}"

def load_json(path):
    if not os.path.exists(path):
        return None
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None

def run_gate_a(video, tech_args, scenes_args):
    """Gate-A: 技术门 (qa_tech + qa_scenes), 全量零成本; 返回 (passed, report 片段)"""
    rc_t, out_t = run_script("qa_tech.py", [video] + tech_args)
    rc_s, out_s = run_script("qa_scenes.py", [video] + scenes_args)
    tech = load_json(os.path.splitext(video)[0] + "_qa.json")
    scenes = load_json(os.path.splitext(video)[0] + "_qa_scenes.json")
    piece = {"qa_tech": tech, "qa_scenes": scenes, "passed": True,
             "deductions": [], "notes": []}
    if tech is None:
        piece["passed"] = False
        piece["deductions"].append(f"[qa_tech] 无报告输出 (rc={rc_t}): {out_t.strip()[-200:]}")
    else:
        piece["deductions"] += [f"[qa_tech] {m}" for m in tech.get("issues", [])]
        piece["notes"] += [f"[qa_tech] {m}" for m in tech.get("issues", [])
                           if tech.get("passed")]  # 技术告警(响度等)不翻车但留痕
    if scenes is None:
        piece["passed"] = False
        piece["deductions"].append(f"[qa_scenes] 无报告输出 (rc={rc_s}): {out_s.strip()[-200:]}")
    else:
        piece["deductions"] += [f"[qa_scenes] {m}" for m in scenes.get("issues", [])]
        piece["notes"] += [f"[qa_scenes] {m}" for m in scenes.get("warnings", [])]
        if scenes.get("issues"):
            piece["passed"] = False
    return piece

def run_gate_b(video, judge_args):
    """Gate-B: 审美门 (qa_judge), 按漏斗; 返回 (verdict, report)"""
    rc, out = run_script("qa_judge.py", [video] + judge_args)
    judge = load_json(os.path.splitext(video)[0] + "_qa_judge.json")
    if judge is None:
        return "hold", {"error": f"qa_judge 无报告输出 (rc={rc}): {out.strip()[-200:]}",
                        "verdict": "hold", "reason": "评审未产出报告"}
    return judge.get("verdict", "hold"), judge

def main():
    args = sys.argv[1:]
    if not args or args[0] in ("-h", "--help"):
        print(__doc__)
        sys.exit(0 if args else 1)
    files = []
    opts = {"level": "L2", "mock": False, "live": False, "prompt": None,
            "min_total": None, "min_dim": None, "max_frames": None, "frames_dir": None,
            "min_resolution": None, "max_duration": None, "json_out": "qa_gate_report.json"}
    flags_pass = {"--prompt": "prompt", "--frames-dir": "frames_dir",
                  "--min-total": "min_total", "--min-dim": "min_dim",
                  "--max-frames": "max_frames", "--min-resolution": "min_resolution",
                  "--max-duration": "max_duration", "--json-out": "json_out"}
    i = 0
    while i < len(args):
        a = args[i]
        if a.startswith("--") and a not in flags_pass and a not in ("--level", "--mock", "--live"):
            break  # 位置参数(资产列表)结束
        if a == "--level" and i + 1 < len(args):
            opts["level"] = args[i + 1].upper(); i += 1
        elif a == "--mock":
            opts["mock"] = True
        elif a == "--live":
            opts["live"] = True
        elif a in flags_pass and i + 1 < len(args):
            opts[flags_pass[a]] = args[i + 1]; i += 1
        else:
            if any(c in a for c in "*?["):
                files.extend(glob.glob(a))
            elif os.path.exists(a):
                files.append(a)
            else:
                print(f"错误: 找不到资产 {a}")
                sys.exit(2)
        i += 1

    if not files:
        print("错误: 未指定资产文件")
        sys.exit(2)
    if opts["level"] not in ("L0", "L1", "L2"):
        print(f"错误: --level 只支持 L0/L1/L2, 得到 {opts['level']}")
        sys.exit(2)
    if opts["level"] != "L0" and not opts["mock"] and not opts["live"]:
        print("默认离线: Gate-B 请显式选 --mock 或 --live (L0 无此限制)")
        sys.exit(2)

    tech_args = []
    if opts["min_resolution"]:
        tech_args += ["--min-resolution", opts["min_resolution"]]
    if opts["max_duration"]:
        tech_args += ["--max-duration", opts["max_duration"]]
    scenes_args = []
    judge_args = ["--level", opts["level"]]
    judge_args += ["--mock"] if opts["mock"] else (["--live"] if opts["live"] else [])
    if opts["prompt"]:
        judge_args += ["--prompt", opts["prompt"]]
    if opts["min_total"]:
        judge_args += ["--min-total", opts["min_total"]]
    if opts["min_dim"]:
        judge_args += ["--min-dim", opts["min_dim"]]
    if opts["max_frames"]:
        judge_args += ["--max-frames", opts["max_frames"]]
    if opts["frames_dir"]:
        judge_args += ["--frames-dir", opts["frames_dir"]]

    report = {"tool": "qa_gate", "generated_at": datetime.datetime.now().isoformat(),
              "level": opts["level"], "mode": "mock" if opts["mock"] else
              ("live" if opts["live"] else "-"),
              "assets": [], "summary": {"pass": 0, "hold": 0, "fail": 0}}

    for f in files:
        asset = {"file": f}
        print(f"\n▶ Gate-A (技术门): {f}")
        gate_a = run_gate_a(f, tech_args, scenes_args)
        asset["gate_a"] = {"passed": gate_a["passed"],
                           "checks": {k: (gate_a[k] or {}).get("checks")
                                      for k in ("qa_tech", "qa_scenes")}}
        if not gate_a["passed"]:
            asset["verdict"] = "fail"
            asset["deductions"] = gate_a["deductions"]
            asset["gate_b"] = {"verdict": "not_run",
                               "reason": "Gate-A 未过, 不花 VLM 成本"}
            print("  ❌ Gate-A 未过 → 不进 Gate-B")
        else:
            asset["deductions"] = []
            asset["notes"] = gate_a["notes"]
            if opts["level"] == "L0":
                asset["gate_b"] = {"verdict": "skip", "reason": "L0 漏斗跳过 VLM 评审"}
                asset["verdict"] = "pass"
                print("  ✅ Gate-A 通过; Gate-B 按 L0 跳过")
            else:
                print(f"▶ Gate-B (审美门, {opts['level']}): {f}")
                verdict, judge = run_gate_b(f, judge_args)
                asset["gate_b"] = {"verdict": verdict, "reason": judge.get("reason"),
                                   "total": judge.get("total")}
                asset["verdict"] = "pass" if verdict == "pass" else "hold"
                if verdict == "hold":
                    asset["deductions"].append(f"[qa_judge] {judge.get('reason')}")
        report["summary"][asset["verdict"]] += 1
        report["assets"].append(asset)

    print("\n" + "=" * 60)
    print(f"质量门禁汇总 (Gate-A→Gate-B, level={opts['level']} mode={report['mode']})")
    print("=" * 60)
    for a in report["assets"]:
        b = a["gate_b"]
        mark = {"pass": "✅", "hold": "⏸ ", "fail": "❌"}[a["verdict"]]
        print(f"  {mark} {a['verdict']:4s} {a['file']}  (A:{'✅' if a['gate_a']['passed'] else '❌'} B:{b['verdict']})")
        for d in a.get("deductions", []):
            print(f"      扣分: {d}")
        for n in a.get("notes", []):
            print(f"      留痕: {n}")
    s = report["summary"]
    print(f"\n汇总: pass={s['pass']} hold={s['hold']} fail={s['fail']}")

    with open(opts["json_out"], "w", encoding="utf-8") as fjs:
        json.dump(report, fjs, ensure_ascii=False, indent=2)
    print(f"报告已保存: {opts['json_out']}")

    return 2 if s["fail"] else (1 if s["hold"] else 0)

if __name__ == "__main__":
    sys.exit(main())
