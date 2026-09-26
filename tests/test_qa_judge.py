"""qa_judge.py 离线测试: 等级映射 / rubric 解析 / gate 判定 / mock HTTP。
绝不真调 VLM——live 通道用替换 requests.post 的 fake 响应。
"""
import json
import os
import subprocess
import sys

import pytest

import qa_judge  # noqa: E402  (conftest 已把 scripts/ 加入 sys.path)
from conftest import SCRIPTS_DIR  # noqa: E402

GOOD_LEVELS = {
    "visual_quality": "good",
    "temporal_consistency": "good",
    "dynamic_degree": "fair",
    "text_video_alignment": "good",
    "factual_consistency": "good",
}


def _l2_raw(levels):
    return json.dumps({d: {"level": lv, "reason": "r"} for d, lv in levels.items()},
                      ensure_ascii=False)


class _FakeResp:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self._payload


# ---------- Q-Align 离散等级映射 ----------

def test_level_map_all_five_levels():
    assert qa_judge.LEVEL_MAP == {
        "excellent": (5, 4), "good": (4, 3), "fair": (3, 2), "poor": (2, 1), "bad": (1, 1)}
    for lv, (q, v) in qa_judge.LEVEL_MAP.items():
        sc = qa_judge.level_to_scores(lv)
        assert sc == {"level": lv, "score_qalign": q, "score": v}


def test_level_map_unknown_and_tolerant():
    assert qa_judge.level_to_scores("AMAZING") is None
    assert qa_judge.level_to_scores("") is None
    assert qa_judge.level_to_scores(None) is None
    # 大小写 / 首尾空白容错
    assert qa_judge.level_to_scores("  Good ")["score"] == 3


def test_poor_bad_merge_on_1to4_scale():
    """1-4 制下 poor/bad 合并为 1 分, 但 Q-Align 1-5 制保留区分"""
    assert qa_judge.level_to_scores("poor")["score"] == \
        qa_judge.level_to_scores("bad")["score"] == 1
    assert qa_judge.level_to_scores("poor")["score_qalign"] == 2
    assert qa_judge.level_to_scores("bad")["score_qalign"] == 1


# ---------- rubric 解析 ----------

def test_parse_l2_scores_and_total():
    dims, scores, ok = qa_judge.parse_judgement(_l2_raw(GOOD_LEVELS), "L2")
    assert ok is True
    assert len(scores) == 5
    assert scores["dynamic_degree"] == 2
    assert scores["visual_quality"] == 3
    assert dims["visual_quality"]["score_qalign"] == 4
    assert dims["visual_quality"]["reason"] == "r"


def test_parse_tolerates_markdown_fence():
    raw = "```json\n" + _l2_raw(GOOD_LEVELS) + "\n```"
    dims, scores, ok = qa_judge.parse_judgement(raw, "L2")
    assert ok is True and len(scores) == 5


def test_parse_missing_dimension_not_trusted():
    levels = dict(GOOD_LEVELS)
    del levels["factual_consistency"]
    dims, scores, ok = qa_judge.parse_judgement(_l2_raw(levels), "L2")
    assert ok is False and dims is None


def test_parse_bad_level_not_trusted():
    levels = dict(GOOD_LEVELS, factual_consistency="AMAZING")
    dims, scores, ok = qa_judge.parse_judgement(_l2_raw(levels), "L2")
    assert ok is False


def test_parse_garbage_not_trusted():
    dims, scores, ok = qa_judge.parse_judgement("抱歉我无法评审这段视频", "L2")
    assert ok is False


def test_parse_l1_overall():
    raw = json.dumps({"overall": {"level": "fair", "reason": "x"}})
    dims, scores, ok = qa_judge.parse_judgement(raw, "L1")
    assert ok is True and scores == {"overall": 2}


# ---------- gate 判定 ----------

def test_verdict_pass_above_threshold():
    verdict, reason = qa_judge.decide_verdict(
        {d: 3 for d in qa_judge.DIMENSIONS}, min_total=2.5, min_dim=2.0, level="L2")
    assert verdict == "pass"


def test_verdict_hold_low_total():
    scores = {d: 2 for d in qa_judge.DIMENSIONS}  # 全 fair → 总分 2.0 < 2.5
    verdict, reason = qa_judge.decide_verdict(scores, 2.5, 2.0, "L2")
    assert verdict == "hold" and "2.0" in reason


def test_verdict_hold_weak_dimension():
    scores = dict.fromkeys(qa_judge.DIMENSIONS, 3)
    scores["visual_quality"] = 1  # 总分 2.6 达标但单维崩
    verdict, reason = qa_judge.decide_verdict(scores, 2.5, 2.0, "L2")
    assert verdict == "hold" and "visual_quality=1" in reason


def test_verdict_l1_borderline_suggests_l2():
    verdict, reason = qa_judge.decide_verdict({"overall": 2}, 2.5, 2.0, "L1")
    assert verdict == "hold" and "L2" in reason
    verdict, _ = qa_judge.decide_verdict({"overall": 3}, 2.5, 2.0, "L1")
    assert verdict == "pass"


# ---------- prompt 三段式 ----------

def test_prompt_single_v1_three_parts():
    p = qa_judge.build_prompt("红墙前主角回眸", "L2")
    assert "[Instruction]" in p and "[Start of Prompt]" in p and "[End of Prompt]" in p
    for dim, desc in qa_judge.DIMENSIONS.items():
        assert dim in p
    assert "excellent" in p and "只输出" in p  # 离散等级法 + 强制 JSON


def test_prompt_l1_single_dimension():
    p1 = qa_judge.build_prompt("x", "L1")
    assert '"overall"' in p1 and "粗筛" in p1


# ---------- live 通道 (mock HTTP, 零真实网络) ----------

def test_live_via_fake_http(monkeypatch, frame_pngs, solid_video):
    calls = {}

    def fake_post(url, **kw):
        calls["url"] = url
        calls["auth"] = kw["headers"]["Authorization"]
        calls["model"] = kw["json"]["model"]
        calls["n_images"] = sum(1 for c in kw["json"]["messages"][0]["content"]
                                if c.get("type") == "image_url")
        return _FakeResp({"choices": [{"message": {"content": _l2_raw(GOOD_LEVELS)}}],
                          "usage": {"total_tokens": 42}})

    monkeypatch.setattr(qa_judge.requests, "post", fake_post)
    monkeypatch.setenv("QA_JUDGE_API_KEY", "test-dummy-not-a-real-key")
    monkeypatch.setenv("QA_JUDGE_BASE_URL", "http://127.0.0.1:1/v1")
    monkeypatch.setenv("QA_JUDGE_MODEL", "mock-vlm")
    rep = qa_judge.run_judge(str(solid_video), frames=frame_pngs["pngs"],
                             level="L2", mode="live", prompt="红墙前主角回眸")
    assert calls["url"] == "http://127.0.0.1:1/v1/chat/completions"
    assert calls["auth"] == "Bearer test-dummy-not-a-real-key"
    assert calls["model"] == "mock-vlm"
    assert calls["n_images"] == 3
    assert rep["verdict"] == "pass"
    assert rep["tokens"] == 42
    assert rep["total"] == 2.8


def test_live_missing_key_no_frame_extraction(monkeypatch, solid_video, tmp_path):
    """缺 key 报 error, 且在抽帧前就拦截 (frames_dir 应保持为空)"""
    monkeypatch.delenv("QA_JUDGE_API_KEY", raising=False)
    rep = qa_judge.run_judge(str(solid_video), frames=None, level="L2", mode="live",
                             frames_dir=str(tmp_path))
    assert rep["verdict"] == "error"
    assert list(tmp_path.iterdir()) == []


# ---------- CLI 行为 ----------

def test_cli_default_refuses_network(solid_video):
    """默认运行零真实请求: 不给 --mock/--live 必须拒绝 (exit 2)"""
    r = subprocess.run([sys.executable, str(SCRIPTS_DIR / "qa_judge.py"),
                        str(solid_video), "--level", "L2"],
                       capture_output=True, text=True, errors="replace", env=os.environ)
    assert r.returncode == 2
    assert "--mock" in r.stdout


def test_cli_l0_skip(solid_video):
    r = subprocess.run([sys.executable, str(SCRIPTS_DIR / "qa_judge.py"),
                        str(solid_video), "--level", "L0"],
                       capture_output=True, text=True, errors="replace", env=os.environ)
    assert r.returncode == 0
    assert "skip" in r.stdout
