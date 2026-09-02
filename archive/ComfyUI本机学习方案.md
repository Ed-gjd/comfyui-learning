# ComfyUI 本机学习方案（CPU 沙盒）

> 整理：2026-08-07 ｜ 定位：本机 = **学习沙盒 + 开发环境**；出图/出视频 = **AutoDL 云端**（本机无独显，不追求出图性能）
> 与 [AI短剧ComfyUI知识库.md](AI短剧ComfyUI知识库.md) 配套，本文件管"怎么练"，知识库管"是什么"。

---

## 学习进度记录（2026-08-08 更新）

| 阶段 | 内容 | 状态 |
|---|---|---|
| 阶段 0 | 跑起来：浏览器开 8188、首图 | ✅ 完成 |
| 阶段 1 | 节点图基础：管线原理 + KSampler 五参数 | 🚧 进行中 |
| 阶段 2 | 出图管线搭建（LoRA / IPAdapter / ControlNet） | ⬜ 未开始 |
| 阶段 3 | API 自动化（`submit_and_wait.py`） | ⬜ 未开始 |
| 阶段 4 | 自定义节点开发 | ⬜ 未开始 |
| 阶段 5 | 云端对接 AutoDL | ⬜ 未开始 |

**阶段 1 已学/已验证：**
- ✅ 文生图全流程原理：文字 → CLIP 编码 → 潜空间去噪（KSampler）→ VAE 解码 → 图
- ✅ API 提交/轮询/取图全链路：`POST /prompt` → `GET /history` → `output/`
- ✅ seed 变量实验：同提示词 "black dog"，seed 777 vs 12345 → 主体同、构图/姿态不同
- ✅ 调试教训：**`curl -s` 会吞掉报错，必须用 `-v` 看真相**
- 📌 已产图：`test_first_image.png`（猫 seed42，530s）、`test_dog_seed777.png`（狗 seed777）、`test_dog_seed12345.png`（狗 seed12345）
- 📌 工作流文件：`comfyui-first-workflow.json`（猫 seed42）、`comfyui-dog-workflow.json`（狗，当前 seed=12345）

**待办 / 下一步：**
- [ ] 把 `test_dog_seed777_00002_.png` 改名拷贝为 `test_dog_seed12345.png`
- [ ] 对比两张狗图，口头描述 seed 造成的差异
- [ ] 阶段 1 下一课：只改 `steps` 20→8，看速度/质量权衡
- [ ] 阶段 3：写 `submit_and_wait.py` 一键出图脚本

---

## 一、本机定位（先说清楚）

| 项 | 实测 | 结论 |
|---|---|---|
| GPU | 无 NVIDIA，仅 AMD 集成显卡 512MB | ❌ 不能当出图主力 |
| 内存 | 7.4GB（可用约 4.8GB） | CPU 模式只够跑 SD1.5 级别小模型 |
| CPU | 16 核 | SD1.5 出图约 2–5 分钟/张 |
| 磁盘 | D 盘空闲 85GB；C 盘剩 57GB | 见下方"位置策略" |

**一句话**：本机用来"学会"和"写好自动化脚本"，真正生成去 AutoDL。两边共用同一套工作流 JSON —— 本地调通，云端出片。

## 二、安装清单（已完成 ✅）

- ✅ ComfyUI 源码 + venv：**`~/comfyui`**（WSL2 原生 ext4，快）
- ✅ 模型：**`/mnt/d/comfyui-models`**（D 盘实体），`~/comfyui/models` 是软链 → 省 C 盘
- ✅ Python 环境：`~/comfyui/.venv`（uv 建，Python 3.12，aliyun 镜像装依赖）
- ✅ ComfyUI-Manager 插件：`~/comfyui/custom_nodes/ComfyUI-Manager`
- ✅ 验证模型：SD1.5 **fp16** `v1-5-pruned-emaonly-fp16.safetensors`（ModelScope 下载后本机转 fp16，2GB）
- ✅ **首图验证通过**：`test_first_image.png`（512×512，CPU 用时 530 秒，约 8.8 分钟）
- 启动：`bash ~/comfyui/start_cpu.sh` → 浏览器 `http://127.0.0.1:8188`

> ⚠️ 本机 CPU 出图很慢（512×512 一张约 9 分钟）——**只用来学结构，出图质量/速度交给云端**。
> 📌 fp16 模型：ComfyUI 在 CPU 上会把 fp16 权重转回 fp32 运行（内存 3.3GB，接近 4.8GB 上限）。若内存吃紧可把 KSampler 步数降到 8-10，或分辨率降到 384。

### 重启电脑后恢复（3 步）
```bash
# ① 打开 WSL2 终端（Ubuntu）
# ② 启动 ComfyUI 服务（约 50 秒起好）
bash ~/comfyui/start_cpu.sh
# ③ 浏览器打开 http://127.0.0.1:8188
```
> 文件都在：代码 `~/comfyui`、模型 `/mnt/d/comfyui-models`、文档图片 `cc/`。服务是手动起的，重启后要重跑第 ② 步。

### 位置策略（踩过坑，重要）
**代码/环境必须放 WSL2 原生区，模型才放 D 盘**。一开始全放 `/mnt/d`，启动 8 分钟没起来 —— 9P 跨层文件系统对"成千上万小文件"（torch、节点文件）慢一个数量级。实测 wchan 卡在 `p9_client_rpc`。
- 原生区：`~/comfyui`（代码 92MB + venv 6GB，启动 ~1 分钟）
- D 盘：`/mnt/d/comfyui-models`（模型大文件，单次读取可接受）
- 模型下载/新增命令：`curl -L -o /mnt/d/comfyui-models/checkpoints/xxx.safetensors "https://modelscope.cn/models/{org}/{name}/resolve/master/{file}"`

### 本机网络坑（踩过，记下）
| 坑 | 解 |
|---|---|
| github.com DNS 被污染 | git 全局改写走 ghfast：`git config --global url."https://ghfast.top/https://github.com/".insteadOf "https://github.com/"` |
| pypi.org 不通 | 用 aliyun 镜像：`--index-url https://mirrors.aliyun.com/pypi/simple/` |
| 镜像包版本滞后 | requirements 里 `comfy-kitchen==0.2.27` 放宽为 `>=0.2.26`（aliyun 最新到 0.2.26） |
| huggingface 不通 | 模型走 ModelScope：`modelscope.cn/models/{org}/{name}/resolve/master/{file}` |
| Windows 本机代理 | 早前只绑 Windows 回环，WSL2 用不上；已改走国内直连方案 |

## 三、学习路线（5 阶段，每阶段有产出物）

### 阶段 0 · 跑起来（今天）
- 目标：启动 server，浏览器看到 ComfyUI 界面，加载默认工作流
- 产出：`http://127.0.0.1:8188` 能开 + 一个默认 workflow 截图存知识库
- 验收标准：界面右上角无报错

### 阶段 1 · 节点图基础（学 UI）
- 目标：搞懂"加载模型 → 正向提示词 → 反向提示词 → KSampler → VAE 解码 → 保存"这条主线
- 知识点：KSampler 五个关键参数 —— steps（迭代步数）/ CFG（提示词服从度）/ seed（随机种子）/ sampler（采样器）/ scheduler（调度器）
- 产出：用 SD1.5 出第一张 CPU 图（512×512，steps 20，约 2–5 分钟），**保存 workflow JSON**
- 验收：能改动 seed/提示词并复现不同结果

### 阶段 2 · 出图管线搭建（学工作流）
- 目标：搭出你知识库 §06 角色一致性 的骨架：**文生图 → LoRA → IPAdapter 参考图 → ControlNet 结构控制**
- 知识点：LoRA 加载、参考图传入、ControlNet 条件输入（换不同的 ControlNet 类型）
- 产出：一个"角色一致"双图对比工作流（CPU 慢，可把步数降到 8–10 验证拓扑）
- 验收：同一角色两张图五官/服装一致

### 阶段 3 · API 自动化（你的强项，重点）
- 目标：脱离界面，用 Python 驱动 ComfyUI
- 知识点：POST `/prompt` 提交工作流、GET `/history` 查状态、GET `/view` 取图
- 产出：`submit_and_wait.py` —— 输入一个 workflow JSON，自动提交→轮询→下载图片
- 验收：命令行一句 `python submit_and_wait.py my_workflow.json` 出图
- **这是通向"自动化建模 + 程序化动画"的关键一步**，和你 Blender 脚本自动化的目标同构

### 阶段 4 · 自定义节点开发（学扩展）
- 目标：写第一个自定义 Python 节点，注册进 ComfyUI
- 知识点：节点类结构（`INPUT_TYPES` / `RETURN_TYPES` / `FUNCTION`）、`custom_nodes` 目录、重启生效
- 产出：一个自定义节点（例：把输出图加个水印/改尺寸），放进 `custom_nodes/` 可用
- 验收：界面节点面板出现你的节点并跑通

### 阶段 5 · 云端对接（衔接生产）
- 目标：把本地验证好的 workflow JSON 和脚本一键切到 AutoDL（GPU 实例）
- 做法：AutoDL 装同样 ComfyUI → 上传 workflow JSON + `submit_and_wait.py` → 出图/出视频
- 产出：`deploy_to_autodl.sh` 脚本 + 一份"本地↔云端切换说明"
- 验收：同一工作流文件，本地和云端都出图

## 四、优点总结（为什么要装本机）

1. **零成本练习**：节点、工作流、API、自定义节点，本地随便试，不烧云钱
2. **开发迭代快**：写自定义节点/脚本，本地起服务即改即测；云端一次部署成本高
3. **和你的强项匹配**：你的目标是自动化，核心开发（脚本、节点、JSON 工作流）全在本地干
4. **网络通了就不贵**：全靠国内源（aliyun/ghfast/ModelScope），不用花钱买流量
5. **知识库沉淀有依托**：每个阶段产出物（workflow、脚本、截图）直接进 `AI短剧ComfyUI知识库.md`

## 五、何时不用本机

- 需要 Flux / SDXL 级别出图 → AutoDL
- 需要出视频 → 直接 Vidu / AutoDL（本机没显卡，跑不了视频模型）
- 需要 LoRA 训练 → 云端（§07 云端训练）

---
> 环境搭建过程如果遇到问题，参考本文件"网络坑"一节；版本信息用前以官网实时价/版本为准。
