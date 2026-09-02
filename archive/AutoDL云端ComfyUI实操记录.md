# AutoDL 云端 ComfyUI 实操记录（L1-L3）

> 日期：2026-08-07 至 2026-08-08 ｜ 模式：autodl-cli 纯命令
> 配套：`../images/出图命令复盘.md`（命令链）＋ `../images/出图记录.txt`（每张图参数）

## 一句话总结

> 用 `autodl-cli` 完成云端 ComfyUI 的完整闭环：**建实例 → SSH 连接 → 隧道访问 → 下载模型 → API 出图 → 传回本地**。三课共花约 **¥2**，出了 6 张图。

---

## 环境与配置（已定稿）

| 项 | 值 |
|---|---|
| 应用 | ComfyUI纯净版 `2U7NVqfvXy:v1` ／ tzwm整合包 `dMyRZqDsgL:v20` |
| 显卡 | `v-32g-p`（vGPU-32GB，物理 RTX 4080 分片）**¥1.77/时** |
| CLI | autodl-cli（Rust，`~/.cargo/bin`）|
| API 主机 | `www.autodl.art`（应用实例）／ `api.autodl.com`（容器 Pro）|

## L1 · 实例生命周期（5 个命令）

```bash
autodl-cli create --application 2U7NVqfvXy --app-version v1 --gpu-spec v-32g-p --name xx
autodl-cli status <uuid>      # starting → running
autodl-cli info <uuid>        # SSH/密码/服务域名/价格
autodl-cli stop <uuid>        # 关机（停止 GPU 计费）
autodl-cli rm <uuid> -y       # 释放（删数据）
```
- 花费：**¥0.04**（约 1.4 分钟）
- 关键：`info` 返回的 `payg_price` **单位是"厘"**（1770 = ¥1.77/时），不是分

## L2 · 连接 ComfyUI（三条路）

1. **服务域名直连**：`https://u{uid}-{uuid}.bjb1.seetacloud.com:8443`（应用实例自带）
2. **SSH 登录**：`ssh -p <port> root@connect.xxx.seetacloud.com`（密码在 info）
3. **SSH 隧道**（绕代理）：`ssh -fN -L 8190:127.0.0.1:6006 -p <port> root@...`
   → 浏览器开 `http://localhost:8190`

**坑**：ComfyUI纯净版 启动时 ComfyUI-Manager 拉境外注册表（github/ComfyRegistry）会超时卡死，端口不监听。tzwm 整合包没这个问题。

## L3 · 出第一张图（7 步命令链，详见出图命令复盘.md）

```
搭隧道 → 下模型(hf-mirror) → 确认后端 → POST /prompt → 轮询 /history → /view 取图 → SCP 传回
```

- 模型：SD1.5 `v1-5-pruned-emaonly.safetensors`（4GB，hf-mirror，272-382 MB/s）
- 出图：512×512/768，22 步，**单张 2.2s**
- 产出：6 张图在 `cc/comfyui/images/`

---

## 技术发现（重要）

1. **两套 API 轨道**：autodl-cli 走 `www.autodl.art`（应用实例，`--application`）；官方 Pro API 走 `api.autodl.com`（`image_uuid`）。钱包似乎独立 —— 充值注意充对平台。
2. **应用市场接口**：`POST /api/v1/global/search`（body `{"keyword":"xx"}`）可搜应用；应用数字 ID 用 `square/detail` 查。
3. **GPU 规格**：CLI 轨道可用 `4090D`/`v-32g-p`/`v-48g-350w`/`pro6000-p` 等；3060/3080Ti 等便宜卡**不在 CLI 轨道**（只在网页）。
4. **模型下载**：一律走 `HF_ENDPOINT=https://hf-mirror.com`（国内镜像），wget `-c` 断点续传。
5. **价格真相**：CLI/应用实例轨道价格 = 网页算力市场价格（vGPU-32G = ¥1.77/时），无溢价。

## 踩坑清单（血泪）

- ❌ 探测规格 ID 用真实 `create` → 生成**未付款订单**挡住下单（自动过期，或控制台取消）
- ❌ 余额不足 ≠ 钱包没钱，可能是**充错平台**（autodl.com vs autodl.art）
- ❌ 应用描述"集成模型" ≠ 预装出图 checkpoint（tzwm 只是预装插件辅助模型）
- ❌ Windows 本机代理会挡云端域名 → 用 SSH 隧道绕
- ❌ 后台启动远程进程：`setsid + </dev/null + >log`，否则 SSH 断开进程被杀
- ✅ 学术加速 `source /etc/network_turbo` 加速 github/huggingface（可能不稳定）

## 花费汇总

| 会话 | 内容 | 花费 |
|---|---|---|
| L1 | 生命周期 | ¥0.04 |
| L2（纯净版） | 连接尝试（app bug）| ~¥0.5 |
| L3（tzwm） | 出图 6 张 | ~¥1.0 |
| **合计** | | **~¥1.5-2** |

## L4 · 角色 LoRA 训练（完成 2026-08-08）

**关键突破**：发现 AutoDL 实例有 `/.autodl-model`（14T 公共模型库），FLUX.2-Klein / SDXL / Qwen3-4B 等模型**符号链接直接可用，零下载零占盘**。

**流程**：SDXL 出 24 张角色图（`sxgirl` 触发词）→ 字幕 → kohya 训练 1920 步（39 分钟，loss 0.31→0.114）→ 产出 LoRA。

**训练命令要点**（kohya sd-scripts）：
- 数据集子文件夹命名 **`10_sxgirl`**（`重复数_类名` 前缀）—— 之前一直"找不到数据"的根因
- 用 **CLI 参数**（非 TOML），`--dataset_repeats` 是这个版本的正确名
- `HF_ENDPOINT=https://hf-mirror.com` 必须设（否则拉 CLIP 配置超时）
- 参数：SDXL 1024²、rank32、lr1e-4、8 epochs、1920 步、bf16

**产出**（在 `cc/comfyui/images/lora/`）：
- `hongyi_lora.safetensors`（最终版，218M）+ epoch2/4/6 中间检查点
- 24 张训练素材在 `comfyui/images/char_dataset/`（按场景 24 个子目录）

**遗留问题（下次做）**：
1. **训练素材是"文字生成"的，脸一致性不完美** → 下次用 IPAdapter 锁脸重新生成 24 张（更稳）
2. LoRA 训练完成但**没测试**（用户外出）→ 下次挂 `sxgirl` 出图验证
3. 训练用基底 SDXL（FLUX.2-Klein 编码器与 tzwm ComfyUI 版本不兼容，需更新 ComfyUI 才能用 FLUX.2）

**费用**：L4 训练 ~39 分钟 × ¥1.77/时 ≈ ¥1.2（图片生成 ~¥0.5）

## FLUX.2 重做 30 张现代同脸图（进行中 2026-08-08）

**关键突破**：市场里找到 **Flux-2-Klein-ComfyUI 应用**（aistudent, id=129, v1）—— **自带 torch 2.8 + FLUX.2-Klein 全模型预装 + flux2 编码器类型**，开箱即用，不用碰 tzwm 的旧环境。

**FLUX.2-Klein 锁脸链路（已跑通）**：
- 模型：`flux-2-klein-base-4b`（50步高清）/ `flux-2-klein-4b`（蒸馏4步，快8倍）→ **全预装**
- 编码器：`qwen_3_4b` + CLIPLoader **type=flux2**（关键！老 ComfyUI 没有这个类型）
- 锁脸：**PuLID-Flux2** 节点 + `pulid_flux2_klein_v1.safetensors`（1.3G，hf-mirror）+ insightface antelopev2（库 symlink）+ EVA-CLIP（首次用 hf-mirror 自动下）
- 参数：蒸馏版 guidance=1.0、steps=4、PuLID strength=1.4

**踩的坑（都解决了）**：
1. numpy 2.3 坏 insightface（`numpy.core.umath`）→ 降 numpy 1.26.4
2. ml_dtypes 0.3.2 缺 `float4_e2m1fn` → 升 0.5.4
3. EVA-CLIP 下载走 huggingface 被 401 → ComfyUI 带 `HF_ENDPOINT=https://hf-mirror.com` 启动
4. **重启 ComfyUI 别用 `pkill -f 'main.py'`**（会误杀新进程）→ 直接 setsid/nohup 启动
5. ComfyUI 日志在 `user/comfyui.log`（不是根目录）

**进度**：FLUX.2 现代同脸图已生成 **14/30**（`comfyui/images/flux2_modern/`），其余 16 张未完成（用户关机暂停）。

**待续**：续跑 16 张 → 验收 → 如脸像则 L5-2 批量出图。

## 下一步（L5+）

1. **测试 LoRA**：挂 `sxgirl` 出 5 个场景验证脸一致性
2. 分镜 JSON 管线（LLM 出分镜 → 批量出图）
3. 图生视频走 Vidu → 配音（GPT-SoVITS）→ FFmpeg 拼片 → 第一条成片

## L5 复盘（2026-08-08）

### L5-2 分镜 JSON 管线 ✅（已完成，未云端出图）
- `pipeline/` 建好：`storyboard/demo_story.json`（5 镜头《雪院回眸》）+ `workflows/sdxl_lora_template.json` + `scripts/batch_generate.py`（dry-run 通过）
- 一致性方案调研：InstantID 过时（维护模式 + ControlNet 底层老）；**PuLID-Flux2 是 2026 主流**（已跑通）；LoRA 仍适合长剧

### L5-3 LTX-2.3 图生视频 ❌（5 次提交失败，止损 ¥3）
- 路径：AutoDL 内置视频模型（绕开 Vidu 充值 ¥500）→ 选 LTX-2.3 22B + Gemma3 fp4 + 公共库 Kijai/LTX2.3_comfy 全套
- 报错轨迹：VAE size mismatch(1024vs256) → TinyVAE 不匹配 → diffusers key 不匹配 → `'Linear' no weight`
- **根因（已查证）**：ComfyUI 0.9.2 正式版只支持 LTX-2 的 256 通道 VAE，**LTX-2.3 的 1024 通道新 latent 需 Nightly 版**（[官方教程](https://docs.comfy.org/tutorials/video/ltx/ltx-2-3) 明确写）。文件清单从第一版就是对的，纯版本不够新
- 资产保留：gemma 8.8G 留在实例（数据保留）；pipeline 代码在本地；symlink 配置在实例
- **下次正确路径**：升级 ComfyUI → 官方 I2V 模板（Template → Video → LTX-2.3）→ 模型全用公共库 + 已下 gemma

### L5-3 ✅ 已跑通（2026-08-08 晚，5 镜头全出片）

**根因修复**：ComfyUI 0.9.2 → **v0.30.1**（`git checkout v0.30.1` + pip 依赖 + 重启）。git 走 ghfast 镜像（`git config url."https://ghfast.top/https://github.com/".insteadOf ...`）。

**工作流关键修正**：不能用自搭的 `SamplerCustom + LTXVScheduler`——**必须用官方模板结构**：
```
UNETLoader + LoraLoaderModelOnly + LTXAVTextEncoderLoader + LTXVConditioning
→ LTXVPreprocess + EmptyLTXVLatentVideo + LTXVImgToVideoInplace
→ RandomNoise + CFGGuider(cfg) + KSamplerSelect(euler) + ManualSigmas
→ SamplerCustomAdvanced → VAEDecode → CreateVideo → SaveVideo
```

**模型组合（Kijai split，公共库零下载）**：`ltx-2-3-22b-dev_transformer_only_fp8_input_scaled`（注意连字符 2-3！）+ distilled LoRA + `gemma_3_12B_it_fp4_mixed` + `LTX23_video_vae`。

**调参教训**：
- **seed 必须换**：固定 seed = 每次同样的"转圈"！换 seed 是关键
- strength 0.5（低 = 运动自由，减少木偶）、cfg 2.0（更服从动作 prompt）
- 提示词要**动作导向**（"turns her whole body, catches snowflake, continuous smooth motion, fluid"），静态描述会转圈/木偶
- 单视频生成 ≈ 2-4 分钟（97帧/832×1216/蒸馏8步）

**磁盘教训**：系统盘仅 30G，模型别堆。dev-fp8(9.2G) 下载是多余（Kijai split 零占盘）+ 引发 No space。公共库无 fp8 单文件 dev-fp8（只有 BF16 43G 跑不动）。

**产出**：`pipeline/clips/s0{1..5}_*.mp4`（5 镜头 4s 竖屏视频）。
**费用**：本次会话实例 ~40 分钟 ≈ ¥1.2
