#!/usr/bin/env python3
"""
submit_and_wait.py — ComfyUI 一键出图脚本
把"提交→轮询→取图"三步封装成一条命令。

用法:
    python submit_and_wait.py <工作流.json> [-o 输出目录]

依赖: pip install requests   （本机已装）
"""
import argparse
import json
import os
import sys
import time

import requests

API = "http://127.0.0.1:8188"


def submit(prompt_data: dict) -> str:
    """① 提交工作流，返回 prompt_id"""
    r = requests.post(f"{API}/prompt", json=prompt_data)
    r.raise_for_status()
    pid = r.json()["prompt_id"]
    print(f"[①提交] prompt_id = {pid}")
    return pid


def wait(pid: str, interval: int = 5) -> dict:
    """② 轮询 /history 直到 success，返回历史记录"""
    print("[②等待] 生成中", end="", flush=True)
    while True:
        hist = requests.get(f"{API}/history/{pid}").json()
        if pid in hist:
            status = hist[pid].get("status", {}).get("status_str", "")
            if status == "success":
                print(" → success ✅")
                return hist[pid]
            print(f"\n[✗失败] status = {status}")
            sys.exit(1)
        print(".", end="", flush=True)
        time.sleep(interval)


def download(record: dict, out_dir: str) -> list:
    """③ 把输出图下载到 out_dir"""
    saved = []
    for node_out in record.get("outputs", {}).values():
        for img in node_out.get("images", []):
            fn = img["filename"]
            r = requests.get(f"{API}/view", params={"filename": fn, "type": "output"})
            path = os.path.join(out_dir, fn)
            with open(path, "wb") as f:
                f.write(r.content)
            saved.append(path)
            print(f"[③下载] {path}")
    return saved


def main():
    ap = argparse.ArgumentParser(description="ComfyUI 一键出图")
    ap.add_argument("workflow", help="工作流 JSON 文件路径")
    ap.add_argument("-o", "--out", default="./output", help="输出目录")
    args = ap.parse_args()

    with open(args.workflow, encoding="utf-8") as f:
        prompt_data = json.load(f)

    pid = submit(prompt_data)
    record = wait(pid)
    download(record, args.out)


if __name__ == "__main__":
    main()
