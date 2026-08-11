#!/usr/bin/env python3
"""kling_generate.py — 可灵图生视频批量生成
用法: python kling_generate.py 项目目录 --scene-list scenes.json [--dry-run]
scenes.json 格式:
[
  {
    "id": "SB-001",
    "image": "path/to/first_frame.png",   # 分镜图或尾帧
    "prompt": "女孩缓缓转头...",           # 运动prompt, 不写外貌
    "duration": "5",
    "mode": "pro",
    "sound": "on"
  }
]
"""
import os
import sys
import json
import time
import urllib.request
import urllib.parse
import ssl

API_BASE = "https://api-beijing.klingai.com"
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE


def get_api_key():
    key = os.environ.get("KLING_API_KEY", "")
    if not key:
        # 尝试从 D:\hermes\.env 读取
        env_path = r"D:\hermes\.env"
        if os.path.exists(env_path):
            with open(env_path, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("KLING_API_KEY="):
                        key = line.split("=", 1)[1].strip()
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


def upload_image(image_path, api_key):
    """上传图片到可灵CDN, 返回URL (简化版: 用data URL替代或要求已上传)"""
    # 注意: 完整实现需要 multipart 上传, 此处简化
    # 实际流程: POST /v1/files/upload (multipart/form-data)
    raise NotImplementedError("完整上传需要 multipart 实现, 请参考可灵开放平台文档")


def poll_task(task_id, api_key, timeout=600, interval=15):
    start = time.time()
    while time.time() - start < timeout:
        resp = api_get(f"/v1/videos/image2video/{task_id}", api_key)
        data = resp.get("data", {})
        status = data.get("task_status")
        if status == "succeed":
            videos = data.get("task_result", {}).get("videos", [])
            if videos:
                return videos[0]["url"], videos[0].get("duration", 0)
            return None, 0
        elif status == "failed":
            raise RuntimeError(f"任务失败: {data.get('task_status_msg', 'unknown')}")
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
        print("错误: 未找到 KLING_API_KEY")
        sys.exit(1)

    videos_dir = os.path.join(proj, "05-assets", "videos")
    os.makedirs(videos_dir, exist_ok=True)

    log_path = os.path.join(proj, "05-assets", "generation_log.md")
    log = open(log_path, "a", encoding="utf-8")

    print(f"=== 可灵批量生成: {len(scenes)} 个场景 ===")
    print(f"输出: {videos_dir}\n")

    results = []
    for scene in scenes:
        sid = scene["id"]
        prompt = scene.get("prompt", "")
        duration = scene.get("duration", "5")
        mode = scene.get("mode", "pro")
        sound = scene.get("sound", "on")

        print(f"[{sid}] 提交: {prompt[:60]}...")
        if dry_run:
            print(f"  (dry-run) 跳过")
            results.append({"id": sid, "status": "dry-run"})
            continue

        image_url = scene.get("image_url", "")
        if not image_url and scene.get("image"):
            # 本地图片需要先上传, 简化: 提示
            print(f"  ⚠️ 图片需要先上传到CDN: {scene.get('image')}")
            continue

        payload = {
            "model_name": "kling-v3",
            "image": image_url,
            "prompt": prompt,
            "duration": str(duration),
            "mode": mode,
            "sound": sound,
            "cfg_scale": scene.get("cfg_scale", 0.5),
        }
        if scene.get("negative_prompt"):
            payload["negative_prompt"] = scene["negative_prompt"]

        try:
            resp = api_post("/v1/videos/image2video", payload, api_key)
            if resp.get("code") != 0:
                raise RuntimeError(f"API错误: {resp.get('message')}")
            task_id = resp["data"]["task_id"]
            print(f"  task_id: {task_id}, 轮询中...")
            url, dur = poll_task(task_id, api_key)
            if url:
                out_name = f"{sid}_video.mp4"
                out_path = os.path.join(videos_dir, out_name)
                # 下载
                req = urllib.request.Request(url)
                with urllib.request.urlopen(req, timeout=120, context=ctx) as r:
                    with open(out_path, "wb") as out:
                        out.write(r.read())
                print(f"  ✅ {out_path} ({dur}s)")
                results.append({"id": sid, "task_id": task_id, "status": "succeed", "file": out_name})
                log.write(f"| {sid} | {task_id} | kling-v3 | {duration}s | succeed | {out_name} |\n")
            else:
                raise RuntimeError("无视频返回")
        except Exception as e:
            print(f"  ❌ {e}")
            results.append({"id": sid, "status": "failed", "error": str(e)})
            log.write(f"| {sid} | - | kling-v3 | {duration}s | failed | {str(e)[:80]} |\n")

    log.close()
    print(f"\n=== 完成: {sum(1 for r in results if r['status']=='succeed')}/{len(scenes)} 成功 ===")
    for r in results:
        print(f"  {r['id']}: {r['status']}")

if __name__ == "__main__":
    main()
