"""qa_scenes.py 离线测试: 切点数 / 音画时长差 / 尾静音 (lavfi 合成夹具)。"""
import pytest

pytest.importorskip("scenedetect")

import qa_scenes  # noqa: E402  (conftest 已把 scripts/ 加入 sys.path)


def test_zero_cuts_solid(solid_video):
    """纯色无切点视频: 0 切点 → PASS"""
    r = qa_scenes.run_qa(str(solid_video))
    assert r["scene_cuts"] == 0
    assert r["cut_points"] == []
    assert r["checks"]["scene_cuts"] == "PASS"
    assert r["passed"] is True


def test_one_cut_ok(cut_one_video):
    """红→蓝单硬切: 恰 1 个切点, 位置在 2s 附近, 阈值内 → PASS"""
    r = qa_scenes.run_qa(str(cut_one_video))
    assert r["scene_cuts"] == 1
    assert r["cut_points"][0] == pytest.approx(2.0, abs=0.5)
    assert r["checks"]["scene_cuts"] == "PASS"
    assert r["passed"] is True


def test_two_cuts_fail(cut_two_video):
    """三段 concat 2 个切点 > 1 → FAIL, 问题里含切点时间"""
    r = qa_scenes.run_qa(str(cut_two_video))
    assert r["scene_cuts"] == 2
    assert len(r["cut_points"]) == 2
    assert r["cut_points"][0] == pytest.approx(2.0, abs=0.5)
    assert r["cut_points"][1] == pytest.approx(4.0, abs=0.5)
    assert r["passed"] is False
    assert any("切点" in i for i in r["issues"])


def test_av_duration_drift_fail(avdrift_video):
    """视频 3s / 音频 1.5s: 时长差 > 0.5s → FAIL"""
    r = qa_scenes.run_qa(str(avdrift_video))
    assert r["av_diff"] > 0.5
    assert r["checks"]["av_duration"].startswith("FAIL")
    assert r["passed"] is False


def test_av_duration_match_pass(solid_video):
    """音画齐长: 时长差 ≤ 0.5s → PASS"""
    r = qa_scenes.run_qa(str(solid_video))
    assert r["av_diff"] <= 0.5
    assert r["checks"]["av_duration"] == "PASS"


def test_trailing_silence_warn_only(tailsil_video):
    """音频 1s 后静音填充到 4s: 尾静音 > 2s → 警告但不翻车"""
    r = qa_scenes.run_qa(str(tailsil_video))
    assert r["trailing_silence_s"] > 2.0
    assert r["checks"]["trailing_silence"].startswith("WARN")
    assert r["warnings"], "尾静音应产生警告"
    assert r["passed"] is True, "警告级问题不应判 fail"


def test_no_silence_no_warn(solid_video):
    """全程正弦音: 无尾静音 → PASS 且无警告"""
    r = qa_scenes.run_qa(str(solid_video))
    assert r["trailing_silence_s"] == 0.0
    assert r["checks"]["trailing_silence"] == "PASS"
    assert r["warnings"] == []
