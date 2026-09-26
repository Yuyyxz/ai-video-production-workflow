"""qa_gate.py 串联测试: Gate-A→Gate-B 全流程, subprocess 真跑三脚本 (零网络)。"""
import json
import os
import subprocess
import sys
from pathlib import Path

from conftest import SCRIPTS_DIR


def _run_gate(args):
    return subprocess.run([sys.executable, str(SCRIPTS_DIR / "qa_gate.py")] + args,
                          capture_output=True, text=True, errors="replace", env=os.environ)


def test_gate_pass_fail_funnel(tmp_path, solid_video, cut_two_video):
    """好资产 pass; 2 切点资产 Gate-A 拦截 → fail 且不进 Gate-B"""
    out = tmp_path / "gate.json"
    r = _run_gate([str(solid_video), str(cut_two_video), "--level", "L2", "--mock",
                   "--min-resolution", "320x240", "--json-out", str(out)])
    assert r.returncode == 2, r.stdout[-500:]
    rep = json.loads(Path(out).read_text(encoding="utf-8"))
    a_ok, a_bad = rep["assets"]
    assert a_ok["verdict"] == "pass"
    assert a_ok["gate_a"]["passed"] is True
    assert a_ok["gate_b"]["verdict"] == "pass"
    assert a_bad["verdict"] == "fail"
    assert a_bad["gate_b"]["verdict"] == "not_run"
    assert "不花 VLM" in a_bad["gate_b"]["reason"]
    assert any("切点" in d for d in a_bad["deductions"])
    assert rep["summary"] == {"pass": 1, "hold": 0, "fail": 1}


def test_gate_l0_skip_gate_b(tmp_path, solid_video):
    """L0 漏斗: 只跑 Gate-A, 无需 --mock/--live, Gate-B skip, exit 0"""
    out = tmp_path / "g0.json"
    r = _run_gate([str(solid_video), "--level", "L0",
                   "--min-resolution", "320x240", "--json-out", str(out)])
    assert r.returncode == 0, r.stdout[-500:]
    rep = json.loads(Path(out).read_text(encoding="utf-8"))
    assert rep["assets"][0]["gate_b"]["verdict"] == "skip"
    assert rep["summary"] == {"pass": 1, "hold": 0, "fail": 0}


def test_gate_hold_when_judge_below_threshold(tmp_path, solid_video):
    """调高 min-total 逼出 hold: Gate-A 过但 Gate-B 分不够 → exit 1"""
    out = tmp_path / "gh.json"
    r = _run_gate([str(solid_video), "--level", "L2", "--mock", "--min-total", "3.5",
                   "--min-resolution", "320x240", "--json-out", str(out)])
    assert r.returncode == 1, r.stdout[-500:]
    rep = json.loads(Path(out).read_text(encoding="utf-8"))
    asset = rep["assets"][0]
    assert asset["verdict"] == "hold"
    assert asset["gate_b"]["verdict"] == "hold"
    assert any("[qa_judge]" in d for d in asset["deductions"])
    assert rep["summary"] == {"pass": 0, "hold": 1, "fail": 0}


def test_gate_tail_silence_passes_with_note(tmp_path, tailsil_video):
    """尾静音警告: 资产仍 pass, 但留痕可见"""
    out = tmp_path / "gt.json"
    r = _run_gate([str(tailsil_video), "--level", "L0",
                   "--min-resolution", "320x240", "--json-out", str(out)])
    assert r.returncode == 0, r.stdout[-500:]
    rep = json.loads(Path(out).read_text(encoding="utf-8"))
    asset = rep["assets"][0]
    assert asset["verdict"] == "pass"
    assert any("尾静音" in n or "末尾静音" in n for n in asset.get("notes", []))
