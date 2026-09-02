#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
batch_generate.py — 分镜 JSON → 批量出图（L5-2 管线核心）

读 pipeline/storyboard/*.json 的"分镜 JSON"，逐镜头：
  分镜 prompt → 注入 SDXL+LoRA 模板 → 提交 ComfyUI → 轮询 → 下载

用法:
    # 无网验证（只看每镜头生成的 prompt/seed，不提交）：
    python batch_generate.py --storyboard ../storyboard/demo_story.json --dry-run

    # 真实出图（默认连云端隧道 localhost:8190）：
    python batch_generate.py --storyboard ../storyboard/demo_story.json

    # 本机 CPU 沙盒（localhost:8188，需换成 SD1.5 模板）：
    python batch_generate.py --storyboard ../storyboard/demo_story.json \
        --api http://127.0.0.1:8188 --template ../workflows/sdxl_lora_template.json

依赖: requests（已装）
"""
import argparse
import json
import os
import sys
import time

import requests

DEFAULT_API = "http://127.0.0.1:8190"
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_TEMPLATE = os.path.join(BASE_DIR, "workflows", "sdxl_lora_template.json")
DEFAULT_OUT = os.path.join(BASE_DIR, "images")
RETRY = 3
POLL_INTERVAL = 5


# ---------- 分镜 → 工作流 ----------

def load_storyboard(path: str) -> list:
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    shots = data["shots"]
    print(f"[分镜] {data['meta']['title']} · {len(shots)} 镜头 · "
          f"{data['meta']['genre']}")
    return shots


def build_workflow(shot: dict, template: dict, seed: int, prefix: str) -> dict:
    """把分镜字段注入模板，返回可提交的 API 工作流"""
    wf = json.loads(json.dumps(template))  # 深拷贝
    prompt = shot["prompt"]
    text = json.dumps(wf)  # 序列化后整体替换，防止占位符漏网
    text = text.replace("__PROMPT__", prompt.replace('"', '\\"'))
    text = text.replace("__SEED__", str(seed))
    text = text.replace("__PREFIX__", prefix)
    return json.loads(text)


def shot_seed(base_seed: int, index: int) -> int:
    """每个镜头固定种子 → 重跑可复现（幂等）。base_seed + index"""
    return base_seed + index


def out_name(shot: dict, index: int) -> str:
    return f"{shot['id']}_{index:02d}_shot.png"


# ---------- 提交 / 轮询 / 下载 ----------

def submit(api: str, wf: dict) -> str:
    r = requests.post(f"{api}/prompt", json={"prompt": wf}, timeout=30)
    r.raise_for_status()
    pid = r.json()["prompt_id"]
    print(f"  [提交] prompt_id={pid}")
    return pid


def wait(api: str, pid: str, shot_id: str) -> dict:
    while True:
        try:
            hist = requests.get(f"{api}/history/{pid}", timeout=30).json()
        except requests.RequestException:
            print(".", end="", flush=True)
            time.sleep(POLL_INTERVAL)
            continue
        if pid in hist:
            status = hist[pid].get("status", {}).get("status_str", "")
            if status == "success":
                print(f" ✅ {shot_id} 完成")
                return hist[pid]
            if status in ("error", "failed"):
                msg = hist[pid].get("status", {}).get("messages")
                raise RuntimeError(f"{shot_id} 失败: {msg}")
        print(".", end="", flush=True)
        time.sleep(POLL_INTERVAL)


def download(api: str, record: dict, out_dir: str) -> list:
    saved = []
    for node_out in record.get("outputs", {}).values():
        for img in node_out.get("images", []):
            fn = img["filename"]
            r = requests.get(f"{api}/view", params={"filename": fn, "type": "output"},
                             timeout=60)
            path = os.path.join(out_dir, fn)
            with open(path, "wb") as f:
                f.write(r.content)
            saved.append(path)
    return saved


# ---------- 主流程 ----------

def main():
    ap = argparse.ArgumentParser(description="分镜 JSON → 批量出图")
    ap.add_argument("--storyboard", required=True, help="分镜 JSON 路径")
    ap.add_argument("--api", default=DEFAULT_API, help="ComfyUI API 地址")
    ap.add_argument("--template", default=DEFAULT_TEMPLATE, help="工作流模板")
    ap.add_argument("--out", default=DEFAULT_OUT, help="输出目录")
    ap.add_argument("--seed", type=int, default=20260808, help="种子基值")
    ap.add_argument("--dry-run", action="store_true",
                    help="只构建并打印每镜头工作流，不提交（无网验证）")
    args = ap.parse_args()

    shots = load_storyboard(args.storyboard)
    with open(args.template, encoding="utf-8") as f:
        template = json.load(f)

    os.makedirs(args.out, exist_ok=True)

    if args.dry_run:
        print(f"[dry-run] 目标 API={args.api} · 输出={args.out}\n")
        for i, shot in enumerate(shots):
            seed = shot_seed(args.seed, i)
            prefix = f"shot_{shot['id']}"
            wf = build_workflow(shot, template, seed, prefix)
            # 打印关键注入点
            print(f"--- {shot['id']} · {shot['scene']} · {shot['shot']} ---")
            print(f"   seed={seed}")
            print(f"   prompt: {shot['prompt'][:90]}…")
            print(f"   画布: {wf['latent']['inputs']['width']}x"
                  f"{wf['latent']['inputs']['height']}")
            print(f"   模型: {wf['checkpoint']['inputs']['ckpt_name']}"
                  f" + LoRA {wf['lora']['inputs']['lora_name']}")
        print("\n[dry-run 结束] 模板注入无误，可真实出图。")
        return

    print(f"[出图] API={args.api} · 输出={args.out} · 种子基值={args.seed}")
    results = []
    for i, shot in enumerate(shots):
        seed = shot_seed(args.seed, i)
        prefix = f"shot_{shot['id']}"
        wf = build_workflow(shot, template, seed, prefix)

        done = False
        for attempt in range(1, RETRY + 1):
            print(f"\n[{shot['id']}] {shot['scene']} · 尝试 {attempt}/{RETRY}")
            try:
                pid = submit(args.api, wf)
                record = wait(args.api, pid, shot['id'])
                paths = download(args.api, record, args.out)
                print(f"  [下载] {', '.join(paths)}")
                results.append((shot['id'], paths, seed))
                done = True
                break
            except Exception as e:
                print(f"  ✗ {e}")
                if attempt < RETRY:
                    # 换种子重试（视频/出图是概率性的，换 seed 往往能过）
                    seed = seed + 100000
                    wf = build_workflow(shot, template, seed, prefix)
                    time.sleep(2)
        if not done:
            print(f"  ✗ {shot['id']} 重试 {RETRY} 次仍失败，跳过。")

    print(f"\n===== 完成：{len(results)}/{len(shots)} 镜头出图 =====")
    for sid, paths, seed in results:
        print(f"  {sid} · seed={seed} · {os.path.basename(paths[0])}")


if __name__ == "__main__":
    main()
