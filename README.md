# ComfyUI 学习资料（单文档整合版）

> 汇总：2026-08-12 ｜ 把 `cc/` 根目录零散的 ComfyUI 材料整合为一篇，作为**最新入口**。
> 原散文档已归档到 `cc/comfyui/archive/`（被本文档取代，留作追溯）；测试图/云端产物在 `images/`、脚本在 `scripts/`。本文档集成其全部要点 + 规则红线 + 排错速查。
> 配套知识库（"是什么"，13 章）：`cc/AI短剧ComfyUI知识库.md`。工作流 JSON：见本文 §7。

---

## 0. 定位与分工（先说清楚）

| 端 | 定位 | 结论 |
|---|---|---|
| **本机**（WSL2，无独显/7.4GB 内存/16 核） | 学习沙盒 + 开发环境 | 学节点结构、写自动化脚本；出图慢（512² 约 9 分钟/张） |
| **AutoDL 云端**（vGPU-32G ¥1.77/时） | 出图 / 出视频 / 训练主力 | 同一套 workflow JSON 本地调通、云端出片 |

**一句话**：本机用来"学会"，真正生成去 AutoDL。需要 Flux/SDXL/视频/LoRA 训练一律上云。

---

## 1. 环境速查

### 1.1 本机沙盒（CPU）

| 项 | 值 |
|---|---|
| 代码 + venv | WSL2 原生区 `~/comfyui`（Python 3.12 + uv，ComfyUI-Manager 已装） |
| 模型 | D 盘 `/mnt/d/comfyui-models`（`~/comfyui/models` 是软链） |
| 启动 | `bash ~/comfyui/start_cpu.sh` → 浏览器 `http://127.0.0.1:8188`（约 50 秒起好，服务手动起） |
| torch | **必须 +cpu 版**（cuXX 版在无 N 卡机器某些路径硬崩） |
| 验证模型 | SD1.5 fp16 `v1-5-pruned-emaonly-fp16.safetensors`（ModelScope 下载后本机转 fp16，脚本 `/mnt/d/comfyui-models/convert_fp16.py`） |

**分盘策略（踩过坑）**：代码/环境必须放 WSL2 原生区，模型才放 D 盘。一开始全放 `/mnt/d` 启动 8 分钟卡死 —— 9P 跨层文件系统对"成千上万小文件"（torch、节点）慢一个数量级。大模型文件单次读取放 D 盘可接受。

**重启恢复 3 步**：开 WSL2 → `bash ~/comfyui/start_cpu.sh` → 浏览器开 8188。

### 1.2 AutoDL 云端

| 项 | 值 |
|---|---|
| 实例 | 应用市场 ComfyUI纯净版 `2U7NVqfvXy:v1` ／ tzwm 整合包 `dMyRZqDsgL:v20` |
| 显卡 | `v-32g-p`（vGPU-32GB，物理 RTX 4080 分片）¥1.77/时 |
| CLI | `autodl-cli`（Rust，`~/.cargo/bin`）走 `www.autodl.art`（应用实例轨道） |
| 生命周期 | `create --application <id> --app-version v1 --gpu-spec v-32g-p` → `status` → `info`（拿 SSH/端口/价格）→ `stop` → `rm -y` |
| 连接三路 | ① 服务域名直连 `https://u{uid}-{uuid}.bjb1.seetacloud.com:8443` ② SSH ③ SSH 隧道绕代理：`ssh -fN -L 8190:127.0.0.1:6006 -p <port> root@...` |
| 公共模型库 | 实例内 `/.autodl-model`（14T）→ 模型**符号链接直接可用，零下载零占盘** |
| ComfyUI 升级 | `git checkout v0.30.1` + `pip install -r requirements.txt --index-url ...aliyun...`，git 走 ghfast |

**关键坑**：
- `info` 返回的 `payg_price` **单位是"厘"**（1770 = ¥1.77/时），不是分
- CLI 轨道便宜卡（3060/3080Ti）不在，只在网页；探测规格别用真实 `create`（生成未付款订单）
- 余额不足可能=**充错平台**（autodl.com vs autodl.art 钱包独立）
- Windows 本机代理会挡云端域名 → 用 SSH 隧道绕
- 后台起远程进程：`setsid + </dev/null + >log`，否则 SSH 断开进程被杀
- 重启 ComfyUI **别用 `pkill -f 'main.py'`**（误杀新进程）；ComfyUI 日志在 `user/comfyui.log`

### 1.3 一键恢复（新机器 / 重装）

两条命令拉回整个项目（资料 + ComfyUI + 模型 + 起服务）：

```bash
git clone https://github.com/Ed-gjd/comfyui-learning.git
bash comfyui-learning/scripts/restore.sh
```

- 脚本流程：拉资料 → 补装 ComfyUI（国内源，已存在跳过）→ 下模型（存在跳过）→ 启动 `127.0.0.1:8188`
- **敏感值全用环境变量/占位符**：`HF_TOKEN`（或先 `hf auth login`，token 存 `~/.cache/huggingface/token`）、`SD15_URL`（ModelScope 直链，在 `scripts/restore.sh` 顶部填，占位符不填会自动跳过）
- 私有仓库首次要 `gh auth login`
- 仓库**不含**：LoRA 模型（脚本自动从 HF `edwardhuangm/hongyi-lora` 拉）、大图批（flux2_modern / char_dataset 等无云备份，需要时从原机器拷贝）

---

## 2. 网络方案

本机网络一律走**国内镜像方案**（GitHub/pip/HF 均被墙时）：

| 用途 | 兜底命令 |
|---|---|
| GitHub | `git config --global url."https://ghfast.top/https://github.com/".insteadOf "https://github.com/"` |
| pip | `--index-url https://mirrors.aliyun.com/pypi/simple/`（TUNA/SJTU 403） |
| pytorch CPU wheel | `https://mirrors.aliyun.com/pytorch-wheels/cpu/` |
| 模型（国内） | ModelScope `modelscope.cn/models/{org}/{name}/resolve/master/{file}`，大文件 `curl -C -` 续传 |
| 模型（云端） | 一律 `HF_ENDPOINT=https://hf-mirror.com`，wget `-c` 断点续传 |

---

## 3. 学习路线

### 3.1 本机 5 阶段（总路线，产出物导向）

| 阶段 | 内容 | 状态 |
|---|---|---|
| 0 | 跑起来：8188 界面 + 首图 | ✅ |
| 1 | 节点图基础：管线原理 + KSampler 五参数（steps/CFG/seed/sampler/scheduler） | 🚧 |
| 2 | 出图管线：LoRA / IPAdapter / ControlNet | ⬜ |
| 3 | API 自动化：`POST /prompt` → `GET /history` → `GET /view` | ⬜ |
| 4 | 自定义节点开发（`INPUT_TYPES`/`RETURN_TYPES`/`FUNCTION`） | ⬜ |
| 5 | 云端对接 AutoDL（同 workflow 本地↔云端都出图） | ⬜ |

阶段 1 已学：文生图全流程（文字→CLIP→潜空间去噪→VAE 解码）、API 提交/轮询/取图链路、seed 变量实验（同提示词主体同构图异）。**调试教训：`curl -s` 吞报错，必须 `-v` 看真相。**

### 3.2 本地 8 课实操（从易到难）

| # | 课程 | 新概念 | 需下载 | 状态 |
|---|---|---|---|---|
| 1 | 图生图 img2img | `denoise` 重绘强度（0.2 微调 / 0.8 重画 / 1.0=文生图） | 无 | ✅ 08-08 |
| 2 | 局部重绘 inpaint | mask 遮罩（新版节点名 `LoadImageMask`） | 无 | ✅ 08-08 |
| 3 | API 自动化脚本 | `submit_and_wait.py` 一键出图 | 无 | ✅ 08-08 |
| 4 | ControlNet 姿势控制 | OpenPose 骨架锁结构（短剧分镜关键） | ~700MB | ✅ 08-08 |
| 5 | IPAdapter 风格参考 | 参考图驱动画风 | ~100MB | ⬜ |
| 6 | LoRA 角色/画风 | LoRA 注入 | ~200MB | ⬜ |
| 7 | 高清放大/修复 | Real-ESRGAN | ~70MB | ⬜ |
| 8 | 自定义节点 | 节点类结构 | 无 | ⬜ |

> 原则：**本机能跑的全在本机练**（结构），跑不动（视频/Flux/LoRA 训练）才上云。

### 3.3 云端 L1-L5（AI 短剧生产链路）

| 阶段 | 内容 | 状态 |
|---|---|---|
| L1 | 实例生命周期（5 命令） | ✅ ¥0.04 |
| L2 | 连接 ComfyUI（域名直连/SSH/隧道） | ✅ |
| L3 | 云端出图 6 张（SD1.5，单张 2.2s） | ✅ ~¥1.0 |
| L4 | 角色 LoRA 训练（SDXL 24 张 + kohya，loss 0.31→0.114） | ✅ ~¥1.7 |
| L4b | FLUX.2-Klein 现代同脸图（PuLID-Flux2 锁脸） | 🔶 14/30 |
| L5-2 | 分镜 JSON 管线（`pipeline/`） | ✅ |
| L5-3 | LTX-2.3 图生视频（5 镜头全出片） | ✅ ~¥1.2 |
| L5-4 | 配音（GPT-SoVITS）+ FFmpeg 拼片 → 第一条成片 | ⬜ |

---

## 4. 跑通配方（直接抄）

### 4.1 LTX-2.3 图生视频（L5-3，最重要的一次突破）

**环境**：AutoDL vGPU-32G + **ComfyUI ≥ v0.30.1**（0.9.2 不支持 LTX-2.3！）。

**模型清单**（公共库 symlink 零占盘）：`ltx-2-3-22b-dev_transformer_only_fp8_input_scaled`（**连字符 2-3**）+ `ltx-2.3-22b-distilled-lora-dynamic` + `LTX23_video_vae_bf16` + `ltx-2.3_text_projection_bf16`（放 checkpoints/）+ `gemma_3_12B_it_fp4_mixed`（8.8G，留实例复用）。

**工作流（必须官方模板结构，勿自搭！）**：
```
UNETLoader(dev transformer, fp8_e4m3fn_fast)
  → LoraLoaderModelOnly(distilled LoRA, 0.5)
LTXAVTextEncoderLoader(text_encoder=gemma, ckpt_name=text_projection)
  → CLIPTextEncode pos/neg → LTXVConditioning(frame_rate=24)
LoadImage(首帧) → LTXVPreprocess(img_compression=18)
EmptyLTXVLatentVideo(832,1216,97,1) → LTXVImgToVideoInplace(strength=0.5)
RandomNoise(seed!) + CFGGuider(cfg=2.0) + KSamplerSelect(euler) + ManualSigmas
  → SamplerCustomAdvanced → VAEDecode → CreateVideo(fps=24) → SaveVideo
```
（对应 JSON：`workflows/ltx23_i2v_a.json` / `ltx23_i2v_b.json` / `ltx_img2video.json`）

**参数配方**：

| 参数 | 值 | 为什么 |
|---|---|---|
| **seed** | **每镜头换** | 固定 seed = 每次同样"转圈"（最大坑） |
| strength | 0.5 | 低=运动自由，减木偶 |
| cfg | 2.0 | 高=动作服从提示词 |
| 提示词 | **动作导向英文** | 静态描述→转圈/木偶 |
| 时长 | 97 帧 / 832×1216 / 蒸馏 8 步 ≈ 4s 竖屏 | 单视频 ≈2-4 分钟 |

**动作导向提示词模板**：
```
A Chinese woman in <服装> <场景>. She <明确动作弧线>,
<肢体细节>, <环境动态>. Continuous smooth motion,
fluid natural movement. Cinematic <景别>, <光线>.
```

### 4.2 LoRA 训练要点（L4）

- 数据集子文件夹命名 **`10_sxgirl`**（`重复数_类名` 前缀）—— 之前"找不到数据"的根因
- 用 **CLI 参数**（非 TOML），`--dataset_repeats` 是这个版本的正确名
- 必须设 `HF_ENDPOINT=https://hf-mirror.com`（否则拉 CLIP 配置超时）
- 参数：SDXL 1024²、rank32、lr1e-4、8 epochs、1920 步、bf16
- 产出：`cc/comfyui/images/lora/hongyi_lora.safetensors`（218M）
- 遗留：训练素材是"文字生成"的脸，一致性不完美 → 下次 IPAdapter 锁脸重生成 24 张

### 4.3 FLUX.2-Klein 锁脸（PuLID-Flux2）

- 应用：Flux-2-Klein-ComfyUI（aistudent id=129 v1），自带 torch 2.8 + FLUX.2-Klein 全预装 + **flux2 编码器类型**（老 ComfyUI 没有）
- 模型：`flux-2-klein-4b`（蒸馏 4 步，快 8 倍）；编码器 `qwen_3_4b` + CLIPLoader **type=flux2**
- 锁脸：PuLID-Flux2 + `pulid_flux2_klein_v1.safetensors` + insightface antelopev2 + EVA-CLIP
- 参数：蒸馏版 guidance=1.0、steps=4、PuLID strength=1.4
- 结论：**PuLID-Flux2 是 2026 主流**（InstantID 过时）；LoRA 仍适合长剧

---

## 5. 模型选型与规则（红线，别踩）

1. **Wan 视频模型全平台禁用**（百炼/AutoDL/ComfyUI 都算，太贵），视频一律走 **Vidu 图生视频**。
   - ✅ **例外仅 3 个**：Wan-Dancer-14B（音乐→舞蹈）、Wan2.2-Animate（动作迁移/换人）、TurboWan2.2-I2V-A14B（720P 高速 I2V，公共库 `TurboDiffusion/TurboWan2.2-I2V-A14B-720P`）
   - ⚠️ 边界：禁的是 Wan **视频**模型；通义万相 wanx **图像**、qwen3-tts-flash 等不受限
2. **图像不走千问云 API**（qwen-image-\* / qwen-vl-\* 云通道不稳：ImageSynthesis AccessDenied、OpenAI 兼容 429），图像路线 = ComfyUI（AutoDL 租卡 + Flux）。
   - ✅ **本地推理的 qwen-image 模型可用**（在租的 GPU 上跑模型文件，不走云 API 不按张收费）
3. **任何视频生成前必须明文展示**目的/原因/预算/参数，等批准才动。
4. 定位：**先用平台验证（小云雀/纳逗Pro/可灵/即梦），再自建 ComfyUI 沉淀角色 LoRA 资产**，两者混合用。

---

## 6. 排错速查

| 症状 | 根因 | 解法 |
|---|---|---|
| LTX-2.3 VAE `size mismatch 1024 vs 256` | ComfyUI 版本旧（0.9.2 只认 256 通道 LTX-2 VAE） | 升级 ComfyUI ≥0.30（VAE 版本判断在 `comfy/sd.py`，按 `decoder.up_blocks...conv1.weight` 通道数：512→v0、1024→v1/v2） |
| `'Linear' no weight`（CLIP/gemma 阶段） | 0.9.2 走旧路 `ltxv_te`(T5 架构) 加载 gemma 权重对不上 | 升级 ComfyUI（0.30+ 用 `ltxav_te` 完整路径 + `LTXAVGemmaTokenizer`） |
| 出图报错被吞 | `curl -s` 静默 | 用 `curl -v` 看真相 |
| insightface `numpy.core.umath` | numpy 2.3 太新 | 降 numpy 1.26.4 |
| `float4_e2m1fn` 缺失 | ml_dtypes 0.3.2 旧 | 升 ml_dtypes 0.5.4 |
| EVA-CLIP 下载 401 | HF 被墙 | ComfyUI 带 `HF_ENDPOINT=https://hf-mirror.com` 启动 |
| 重启后新进程被杀 | `pkill -f main.py` 误杀 | 直接 setsid/nohup 启动；日志看 `user/comfyui.log` |
| No space（实例 30G） | 模型堆盘 | 用公共库 `/.autodl-model` symlink 零占盘；Kijai split 别下 dev-fp8(9.2G) 单文件 |
| 训练"找不到数据" | 数据集目录名错 | 子目录命名 `重复数_类名`，如 `10_sxgirl` |
| ComfyUI 启动卡死端口不监听 | Manager 拉境外注册表超时（纯净版） | 换 tzwm 整合包 / 配代理 |
| 模型名搞混 | LTX 连字符 2-3 vs 点号 2.3 | 文件名 `ltx-2-3-...` 正确，`2.3` 是版本号 |
| 固定 seed 视频总"转圈" | seed 复用 | **每镜头换 seed** |

**通用教训**：不确定格式/兼容时**先单节点试加载一次，再全量提交，别连续烧钱试错**。

---

## 7. 产物索引

### workflows/（13 个 JSON）
- 本机基础：`comfyui-first-workflow.json`（首图猫）、`comfyui-dog-workflow.json`（狗）、`comfyui-img2img-workflow.json`、`comfyui-img2img-dn08.json`（denoise 0.8）、`comfyui-img2img-lying.json`、`comfyui-inpaint-workflow.json`、`comfyui-controlnet-pose.json`
- 云端：`sdxl_lora_template.json`、`InstantID锁脸工作流.json` / `InstantI.json`（InstantID，UI 格式）、`ltx23_i2v_a.json` / `ltx23_i2v_b.json` / `ltx_img2video.json`（LTX-2.3 I2V）

### 成片/图（仍在原位置）
- **5 镜头 LTX-2.3 视频**：`cc/pipeline/clips/s0{1..5}_*.mp4`（v3_tuned 为调参最终版）
- 分镜管线：`cc/pipeline/`（storyboard/demo_story.json + scripts/batch_generate.py + workflows/）
- 测试图：`cc/comfyui/images/`（l3_first、sdxl_test、scene_*\*、flux2_modern、lora_test、local-practice 等）；出图复盘在 `images/出图命令复盘.md`、参数在 `images/出图记录.txt`
- 角色 LoRA：`cc/comfyui/images/lora/hongyi_lora.safetensors` + 训练素材 `images/char_dataset/`

### 关键脚本
- `cc/comfyui/scripts/submit_and_wait.py` — 读 workflow JSON → 提交 → 轮询 → 下载图（API 自动化，本地阶段 3）
- `cc/pipeline/scripts/batch_generate.py` — 多镜头批量提交（L5-2）
- `/mnt/d/comfyui-models/convert_fp16.py` — ModelScope fp32 → fp16 流式转换

---

## 8. 协作规则（实操时的行为约定，2026-08-08 订正）

1. **AI 执行全部命令，命令全程亮给你看** —— 你盯着每一步，看不懂就喊停
2. **素材 AI 优先找**（模型/参考图，ModelScope/联网），找不到先问你或上网找经典数据
3. **每课有验收标准**，结果（图/产物）都展示给你，验过才进下一课
4. 报错用 `curl -v` 看真相，AI 排查过程展示给你
5. 每课产出存 `cc/`，进度记到本文件

---

## 9. 成本记录（实测）

| 会话 | 内容 | 花费 |
|---|---|---|
| L1 | 生命周期 | ¥0.04 |
| L2（纯净版） | 连接尝试 | ~¥0.5 |
| L3（tzwm） | 出图 6 张 | ~¥1.0 |
| L4 | LoRA 训练 39 分钟 + 出图 | ~¥1.7 |
| L5-3 | LTX-2.3 视频（含 5 次失败止损 ¥3） | ~¥1.2 |
| **累计** | | **约 ¥10-15 内** |

> 备忘：LTX-2.3 开源运动仍偏机械，自然动作选 Vidu 商用；云上继续跑 FLUX.2 同脸图剩余 16 张 + L5-4 配音拼片。
