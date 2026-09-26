"""QA 门禁离线测试夹具。
ffmpeg lavfi 合成小视频到临时目录; 全程零网络、零真实 VLM、零可灵请求。
"""
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = REPO_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

NOISE = "noise=alls=8:allf=t"  # 轻时间噪声: 防 freezedetect 把纯色误判冻结, 不影响切点判定


def _ffmpeg(args):
    cmd = ["ffmpeg", "-nostdin", "-y", "-v", "error"] + args
    r = subprocess.run(cmd, capture_output=True, text=True,
                       stdin=subprocess.DEVNULL, errors="replace")
    if r.returncode != 0:
        raise RuntimeError(f"ffmpeg 失败: {r.stderr[-400:]}")


requires_ffmpeg = pytest.mark.skipif(shutil.which("ffmpeg") is None,
                                     reason="ffmpeg 不可用")


@pytest.fixture(scope="session")
def solid_video(tmp_path_factory):
    """3s 纯红+轻噪声+全程正弦音: 0 切点, 音画齐长, 无尾静音 (happy path)"""
    out = tmp_path_factory.mktemp("fix") / "solid.mp4"
    _ffmpeg(["-f", "lavfi", "-i", f"color=c=red:s=320x240:d=3:r=10,{NOISE}",
             "-f", "lavfi", "-i", "sine=frequency=440:duration=3",
             "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", str(out)])
    return out


def _concat_video(tmp_path_factory, name, colors, audio_dur=None):
    """多段纯色 concat → 段数-1 个硬切点; audio_dur 给定则带全程正弦音"""
    d = tmp_path_factory.mktemp("fix")
    inputs, labels = [], []
    for i, c in enumerate(colors):
        inputs += ["-f", "lavfi", "-i", f"color=c={c}:s=320x240:d=2:r=10,{NOISE}"]
        labels.append(f"[{i}:v]")
    seg = 2 * len(colors)
    fc = f"{''.join(labels)}concat=n={len(colors)}:v=1:a=0[out]"
    args = inputs[:]
    maps = ["-map", "[out]"]
    if audio_dur:
        args += ["-f", "lavfi", "-i", f"sine=frequency=440:duration={audio_dur}"]
        maps += ["-map", f"{len(colors)}:a"]
    out = d / name
    _ffmpeg(args + ["-filter_complex", fc] + maps +
            ["-c:v", "libx264", "-pix_fmt", "yuv420p"] +
            (["-c:a", "aac"] if audio_dur else []) + [str(out)])
    return out


@pytest.fixture(scope="session")
def cut_one_video(tmp_path_factory):
    """红→蓝 1 个硬切点 (带全程音轨)"""
    return _concat_video(tmp_path_factory, "cut1.mp4", ["red", "blue"], audio_dur=4)


@pytest.fixture(scope="session")
def cut_two_video(tmp_path_factory):
    """红→蓝→绿 2 个硬切点 (无音轨): >1 判异常"""
    return _concat_video(tmp_path_factory, "cut2.mp4", ["red", "blue", "green"])


@pytest.fixture(scope="session")
def avdrift_video(tmp_path_factory):
    """视频 3s / 音频 1.5s: 音画时长差 ~1.5s > 0.5s"""
    out = tmp_path_factory.mktemp("fix") / "avdrift.mp4"
    _ffmpeg(["-f", "lavfi", "-i", f"color=c=red:s=320x240:d=3:r=10,{NOISE}",
             "-f", "lavfi", "-i", "sine=frequency=440:duration=1.5",
             "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", str(out)])
    return out


@pytest.fixture(scope="session")
def tailsil_video(tmp_path_factory):
    """音频 1s 后 apad 静音到 4s: 尾静音 ~3s > 2s (警告级)"""
    out = tmp_path_factory.mktemp("fix") / "tailsil.mp4"
    _ffmpeg(["-f", "lavfi", "-i", f"color=c=red:s=320x240:d=4:r=10,{NOISE}",
             "-f", "lavfi", "-i", "sine=frequency=440:duration=1",
             "-af", "apad=whole_dur=4",
             "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", str(out)])
    return out


@pytest.fixture(scope="session")
def frame_pngs(tmp_path_factory):
    """qa_judge 帧输入: 3 张纯色小图 (等价 extract_frames.py 产物形态)"""
    d = tmp_path_factory.mktemp("frames")
    pngs = []
    for i, c in enumerate(["red", "blue", "green"]):
        p = d / f"f{i}.png"
        _ffmpeg(["-f", "lavfi", "-i", f"color=c={c}:s=64x64:d=0.1",
                 "-frames:v", "1", str(p)])
        pngs.append(str(p))
    return {"pngs": pngs}
