# L5 方案 · 分镜管线 → 第一条成片

> 更新：2026-08-08 ｜ L5-3 已跑通（5 镜头全出片）
> 模式：AutoDL 云端 + ComfyUI v0.30.1，纯命令

---

## L5-2 分镜 JSON 管线 ✅
- `pipeline/`：storyboard/demo_story.json（5 镜头）+ scripts/batch_generate.py + workflows/
- 角色一致性结论：PuLID-Flux2 是 2026 主流（已跑通）；LoRA 长剧用

---

## L5-3 图生视频 · 最终方案（已跑通）

### 一、目标
LTX-2.3 图生视频：5 镜头 × 4s（97帧）竖屏 832×1216

### 二、环境（最关键）
| 项 | 值 |
|---|---|
| 实例 | AutoDL vGPU-32G（RTX 4080 SUPER）|
| **ComfyUI** | **≥ v0.30.1**（0.9.2 不支持 LTX-2.3！升级法见下）|
| 模型 | 公共库 `/.autodl-model` 零下载 + gemma（下过一次 8.8G）|

**ComfyUI 升级法**（AutoDL 实例）：
```
git config --global url."https://ghfast.top/https://github.com/".insteadOf "https://github.com/"
cd /root/comfy/ComfyUI && git checkout v0.30.1
pip install -r requirements.txt --index-url https://mirrors.aliyun.com/pypi/simple/
# 重启：kill 旧进程（ps 找 python main.py）→ setsid python main.py --listen 0.0.0.0 --port 6006
```

### 三、模型清单（公共库 symlink，零占盘）
| 文件 | 公共库位置 |
|---|---|
| `ltx-2-3-22b-dev_transformer_only_fp8_input_scaled` | Kijai/LTX2.3_comfy/diffusion_models/（**连字符 2-3**！）|
| `ltx-2.3-22b-distilled-lora-dynamic_..._bf16` | Kijai/LTX2.3_comfy/loras/ |
| `LTX23_video_vae_bf16` | Kijai/LTX2.3_comfy/vae/ |
| `ltx-2.3_text_projection_bf16` | Kijai/LTX2.3_comfy/text_encoders/（放 checkpoints/）|
| `gemma_3_12B_it_fp4_mixed` | Comfy-Org/ltx-2 下载（8.8G，留实例复用）|

### 四、工作流（官方模板结构，勿自搭！）
```
UNETLoader(dev transformer, fp8_e4m3fn_fast)
  → LoraLoaderModelOnly(distilled LoRA, 0.5)
LTXAVTextEncoderLoader(text_encoder=gemma, ckpt_name=text_projection)
  → CLIPTextEncode pos/neg → LTXVConditioning(frame_rate=24)
LoadImage(首帧) → LTXVPreprocess(img_compression=18)
EmptyLTXVLatentVideo(832,1216,97,1)
  → LTXVImgToVideoInplace(strength=0.5, bypass=false)
RandomNoise(seed!) + CFGGuider(cfg=2.0) + KSamplerSelect(euler) + ManualSigmas
  → SamplerCustomAdvanced → VAEDecode → CreateVideo(fps=24) → SaveVideo(mp4)
```

### 五、参数配方（s05 v3_tuned 验证）
| 参数 | 值 | 为什么 |
|---|---|---|
| **seed** | **每镜头换** | 固定 seed = 每次同样"转圈"（最大坑）|
| strength | 0.5 | 低 = 运动自由，减木偶 |
| cfg | 2.0 | 高 = 动作服从提示词 |
| 提示词 | **动作导向英文** | 全身转动+微动作+"continuous smooth motion, fluid"；静态描述→转圈 |
| sigmas | 蒸馏 9 值 | 官方模板值 |
| 时长/尺寸 | 97帧/832×1216/蒸馏8步 | ≈4s 竖屏 |

**动作导向提示词模板**（LTX-2.3 用）：
```
A Chinese woman in <服装> <场景>. She <明确动作弧线>,
<肢体细节>, <环境动态>. Continuous smooth motion,
fluid natural movement. Cinematic <景别>, <光线>.
```

### 六、执行流程
```
① 开机 → 升级 ComfyUI（如上）→ 重启
② symlink 公共库模型 → 上传首帧图到 input/
③ 逐镜头改工作流（image+prompt+seed）提交
④ 单视频 ≈ 2-4 分钟
⑤ 拉回 pipeline/clips/ → 关机
```

### 七、成本
单会话 ~40 分钟 ≈ **¥1-2**

### 八、坑（血泪）
1. **ComfyUI 必须 ≥0.30**（0.9.2 缺 VAE 1024 + gemma 加载路径）
2. **seed 必须换**（固定 = 每次同样转圈）
3. **工作流必须官方结构**（SamplerCustomAdvanced，不是 SamplerCustom）
4. **磁盘 30G 别堆模型**（dev-fp8 下载是多余，Kijai split 零占盘）
5. 模型文件名**连字符 2-3** vs 点号 2.3 别搞错

### 九、遗留
- 质量上限：LTX-2.3 开源运动仍偏机械 → 自然动作选 Vidu 商用
- L5-4：配音（GPT-SoVITS）+ FFmpeg 拼片 → 第一条成片

---

## 后续
- L5-4 配音 + 拼片 → 第一条成片
- 视频批量：`batch_shots.py` 模式（多镜头循环提交）已跑通
