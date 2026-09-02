# pipeline · 分镜→出图→视频→成片 自动化管线（L5 起）

> 知识库 §11 的工程落地。**分镜 JSON 是唯一真相源**，所有脚本读它。

## 目录结构

```
pipeline/
  storyboard/        # 分镜 JSON（LLM/手动产出）
    demo_story.json  # L5-2 demo：5 镜头古风微故事
  workflows/         # ComfyUI 工作流模板（API 格式，占位符注入）
    sdxl_lora_template.json
  scripts/           # 管线脚本
    batch_generate.py    # 分镜 → 批量出图（L5-2）
  images/            # 出图产物
  clips/             # 视频片段（L5-3）
  audio/             # 配音（L5-4）
  output/            # 拼片成品（L5-4）
```

## 分镜 JSON schema

```json
{
  "meta": {"title", "genre", "character", "aspect", "total_duration", "shots"},
  "shots": [
    {"id", "scene", "shot", "prompt", "dialogue", "duration", "motion", "style"}
  ]
}
```

- `prompt`：出图用提示词，含主角触发词（如 `sxgirl`）
- `duration`：秒，给 L5-3 Vidu 用
- `motion`：运镜描述，给 L5-3 Vidu 用
- 幂等约定：seed 由 `基础种子 + 镜头序号` 派生，重跑可复现

## L5-2 出图命令

```bash
# 无网验证
python scripts/batch_generate.py --storyboard storyboard/demo_story.json --dry-run

# 云端真实出图（隧道 localhost:8190）
python scripts/batch_generate.py --storyboard storyboard/demo_story.json

# 本机沙盒（SD1.5，改模板）
python scripts/batch_generate.py --storyboard storyboard/demo_story.json \
    --api http://127.0.0.1:8188 --template workflows/sdxl_lora_template.json
```

## 后续环节（L5-3 / L5-4）

- 图生视频：`batch_generate.py` 的 images → Vidu API（`api.vidu.cn/ent/v2/img2video`）
- 拼片：FFmpeg（或 moviepy）拼接 clips + audio + 字幕 → output/
