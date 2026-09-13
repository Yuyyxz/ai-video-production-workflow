#!/usr/bin/env python3
"""kling_generate.py — 可灵图生视频批量生成 (API 2.0)

用法: python kling_generate.py 项目目录 --scene-list scenes.json [--dry-run]

scenes.json 格式:
[
  {
    "id": "SB-001",
    "image": "path/to/first_frame.png",   # 分镜图或尾帧
    "prompt": "女孩缓缓转头...",           # 运动prompt, 不写外貌
    "duration": "5",
    "mode": "pro",                        # std / pro (内部映射 720p / 1080p)
    "sound": "on"                         # on / off (映射 audio)
  }
]

可灵 API 2.0 说明:
- 端点: POST /image-to-video/{model_id}   (模型 ID 在路径, 新版标准)
- 鉴权: Bearer <API Key> (开放平台单 key, 不再用 AK/SK JWT)
- 请求体: contents[] / settings{} / options{} 三层结构
- 轮询: GET /tasks?task_ids=xxx (批量, status 枚举 succeeded)
"""
import os
import sys
import json
import time
import urllib.request
import urllib.parse
import ssl

API_BASE = "https://api-beijing.klingai.com"
# 默认模型 ID (路径式, 新版标准) — 旧 "kling-v3" 映射到 factory/此处保留
DEFAULT_MODEL = "kling-3.0"
# 参数翻译: 旧 std/pro → 新版 resolution 值
RESOLUTION_MAP = {"std": "720p", "standard": "720p", "pro": "1080p"}

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE


def get_api_key():
    """从环境变量或项目根 .env 读取 KLING_API_KEY (不硬编码本机路径)."""
    key = os.environ.get("KLING_API_KEY", "")
    if not key:
        # 在当前目录/上级目录找 .env
        for base in [os.getcwd(), os.path.dirname(os.path.abspath(__file__))]:
            env_path = os.path.join(base, ".env")
            if os.path.exists(env_path):
                with open(env_path, encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line.startswith("KLING_API_KEY="):
                            key = line.split("=", 1)[1].strip()
                            break
                if key:
                    break
    return key


def api_post(path, payload, api_key):
    url = API_BASE + path
    data = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Authorization", f"Bearer {api_key}")
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=60, context=ctx) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")
        raise RuntimeError(f"HTTP {e.code}: {body[:300]}")


def api_get(path, api_key):
    url = API_BASE + path
    req = urllib.request.Request(url)
    req.add_header("Authorization", f"Bearer {api_key}")
    try:
        with urllib.request.urlopen(req, timeout=60, context=ctx) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")
        raise RuntimeError(f"HTTP {e.code}: {body[:300]}")


def poll_task(task_id, api_key, timeout=600, interval=15):
    """轮询: GET /tasks?task_ids=xxx (批量, status 枚举 succeeded/failed)."""
    start = time.time()
    while time.time() - start < timeout:
        resp = api_get(f"/tasks?task_ids={urllib.parse.quote(task_id)}", api_key)
        if resp.get("code") != 0:
            raise RuntimeError(f"轮询错误: {resp.get('message')}")
        tasks = resp.get("data", []) or []
        if tasks:
            status = tasks[0].get("status")
            if status == "succeeded":
                outputs = tasks[0].get("outputs", []) or []
                video_url = None
                for out in outputs:
                    if out.get("type") == "video" and out.get("url"):
                        video_url = out["url"]
                        break
                if not video_url and outputs:
                    video_url = outputs[0].get("url")
                if video_url:
                    return video_url, 0
                raise RuntimeError("任务成功但无视频 URL")
            elif status == "failed":
                raise RuntimeError(f"任务失败: {tasks[0].get('message', 'unknown')}")
        time.sleep(interval)
    raise TimeoutError(f"任务 {task_id} 超时")


def main():
    if len(sys.argv) < 3:
        print("用法: python kling_generate.py 项目目录 --scene-list scenes.json [--dry-run]")
        sys.exit(1)
    proj = os.path.abspath(sys.argv[1])
    scenes_file = None
    dry_run = False
    args = sys.argv[2:]
    for i, a in enumerate(args):
        if a == "--scene-list" and i + 1 < len(args):
            scenes_file = os.path.abspath(args[i + 1])
        if a == "--dry-run":
            dry_run = True

    if not scenes_file:
        print("错误: 需要 --scene-list")
        sys.exit(1)
    if not os.path.exists(scenes_file):
        print(f"错误: 找不到 {scenes_file}")
        sys.exit(1)

    with open(scenes_file, encoding="utf-8") as f:
        scenes = json.load(f)

    api_key = get_api_key()
    if not api_key:
        print("错误: 未找到 KLING_API_KEY (设置环境变量或放置 .env)")
        sys.exit(1)

    videos_dir = None
    for cand in [os.path.join(proj, "05-assets", "videos"), os.path.join(proj, "05-videos")]:
        if os.path.isdir(cand):
            videos_dir = cand
            break
    if videos_dir is None:
        videos_dir = os.path.join(proj, "05-assets", "videos")
    os.makedirs(videos_dir, exist_ok=True)

    log_path = os.path.join(proj, "05-assets", "generation_log.md")
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    log = open(log_path, "a", encoding="utf-8")

    print(f"=== 可灵 API 2.0 批量生成: {len(scenes)} 个场景 ===")
    print(f"输出: {videos_dir}\n")

    results = []
    for scene in scenes:
        sid = scene["id"]
        prompt = scene.get("prompt", "")
        duration = int(scene.get("duration", 5))
        mode = scene.get("mode", "pro")
        sound = scene.get("sound", "off")
        model_id = scene.get("model", DEFAULT_MODEL)

        print(f"[{sid}] 提交: {prompt[:60]}...")
        if dry_run:
            print(f"  (dry-run) 跳过")
            results.append({"id": sid, "status": "dry-run"})
            continue

        image_url = scene.get("image_url", "")
        if not image_url and scene.get("image"):
            print(f"  ⚠️ 图片需要先上传到可灵 CDN/对象存储: {scene.get('image')}")
            continue

        # 参数翻译: 旧 std/pro → resolution; 旧 sound → audio
        resolution = RESOLUTION_MAP.get(mode, mode)
        audio = sound  # "on" / "off"

        # 三层 body (API 2.0)
        contents = [{"type": "prompt", "text": prompt}]
        if scene.get("negative_prompt"):
            contents.append({"type": "negative_prompt", "text": scene["negative_prompt"]})
        if image_url:
            contents.append({"type": "first_frame", "url": image_url})

        settings = {
            "resolution": resolution,
            "duration": duration,
            "audio": audio,
            "multi_shot": False,
        }
        if scene.get("cfg_scale") is not None:
            settings["cfg_scale"] = scene["cfg_scale"]
        if scene.get("aspect_ratio"):
            settings["aspect_ratio"] = scene["aspect_ratio"]

        payload = {"contents": contents, "settings": settings, "options": {}}

        try:
            resp = api_post(f"/image-to-video/{model_id}", payload, api_key)
            if resp.get("code") != 0:
                raise RuntimeError(f"API错误: {resp.get('message')}")
            task_id = resp["data"]["id"]
            print(f"  task_id: {task_id}, 轮询中...")
            url, dur = poll_task(task_id, api_key)
            if url:
                out_name = f"{sid}_video.mp4"
                out_path = os.path.join(videos_dir, out_name)
                req = urllib.request.Request(url)
                with urllib.request.urlopen(req, timeout=120, context=ctx) as r:
                    with open(out_path, "wb") as out:
                        out.write(r.read())
                print(f"  ✅ {out_path}")
                results.append({"id": sid, "task_id": task_id, "status": "succeed", "file": out_name})
                log.write(f"| {sid} | {task_id} | {model_id} | {duration}s | succeed | {out_name} |\n")
            else:
                raise RuntimeError("无视频返回")
        except Exception as e:
            print(f"  ❌ {e}")
            results.append({"id": sid, "status": "failed", "error": str(e)})
            log.write(f"| {sid} | - | {model_id} | {duration}s | failed | {str(e)[:80]} |\n")

    log.close()
    print(f"\n=== 完成: {sum(1 for r in results if r['status']=='succeed')}/{len(scenes)} 成功 ===")
    for r in results:
        print(f"  {r['id']}: {r['status']}")


if __name__ == "__main__":
    main()
