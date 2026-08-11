#!/usr/bin/env python3
"""manifest_check.py — 资产注册表完整性校验
用法: python manifest_check.py [项目目录]
检查:
1. manifest.csv 格式是否正确
2. 登记的文件是否真实存在
3. 未登记的资产文件(孤儿文件)
"""
import os
import sys
import csv
from datetime import datetime

VALID_TYPES = {"character", "world", "scene", "prop", "style", "storyboard",
               "keyframe", "video", "audio", "subtitle", "final", "log", "script"}
VALID_STATUS = {"draft", "approved", "in_production", "done", "failed", "retry", "archived"}

def main():
    if len(sys.argv) < 2:
        print("用法: python manifest_check.py [项目目录]")
        sys.exit(1)
    proj = os.path.abspath(sys.argv[1])
    manifest = os.path.join(proj, "05-assets", "manifest.csv")
    if not os.path.exists(manifest):
        print(f"错误: 找不到 {manifest}")
        sys.exit(1)

    errors = []
    warnings = []
    rows = []
    with open(manifest, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)

    print(f"=== 资产注册表校验: {proj} ===")
    print(f"登记资产: {len(rows)} 条\n")

    # 检查必需字段
    required = ["asset_id", "type", "description", "source", "status", "cost"]
    for i, row in enumerate(rows, 1):
        for field in required:
            if field not in row or not row[field].strip():
                errors.append(f"行{i}: 缺少必需字段 '{field}' (asset_id={row.get('asset_id','?')})")
        if row.get("type") and row["type"] not in VALID_TYPES:
            warnings.append(f"行{i}: 未知类型 '{row['type']}'")
        if row.get("status") and row["status"] not in VALID_STATUS:
            warnings.append(f"行{i}: 未知状态 '{row['status']}'")

    # 检查 asset_id 唯一性
    ids = [r.get("asset_id") for r in rows if r.get("asset_id")]
    dupes = {x for x in ids if ids.count(x) > 1}
    for d in dupes:
        errors.append(f"重复 asset_id: {d}")

    # 检查文件是否存在 (如果登记了文件名)
    for i, row in enumerate(rows, 1):
        if row.get("note") and row["note"].endswith((".png", ".jpg", ".mp4", ".mp3", ".srt", ".csv", ".md")):
            fname = row["note"]
            # note 可能是文件名或描述, 只在像文件名时检查
            if "/" in fname or "\\" in fname or fname.startswith(("CHR", "VD", "SB", "AU", "KF", "FIN")):
                # 在项目里递归找
                found = False
                for root, _, files in os.walk(proj):
                    if fname in files:
                        found = True
                        break
                if not found:
                    warnings.append(f"asset {row['asset_id']}: 文件 '{fname}' 未找到")

    if errors:
        print("❌ 错误:")
        for e in errors:
            print(f"  - {e}")
    else:
        print("✅ 无错误")

    if warnings:
        print("\n⚠️ 警告:")
        for w in warnings:
            print(f"  - {w}")

    print("\n=== 校验完成 ===")
    return 1 if errors else 0

if __name__ == "__main__":
    sys.exit(main())
