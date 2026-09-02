#!/usr/bin/env bash
# ============================================================
# ComfyUI 学习项目 · 一键恢复脚本（restore.sh）
# 一条命令拉回：资料仓库 + ComfyUI 环境 + 模型 + 起服务
#
# 新机器用法（两条命令）：
#   git clone https://github.com/Ed-gjd/comfyui-learning.git
#   bash comfyui-learning/scripts/restore.sh
#
# 规则：敏感值一律用环境变量 / 占位符，脚本内不写死任何凭证
# ============================================================
set -euo pipefail

# ---------- 配置（环境变量可覆盖；<...> = 未填占位符，会跳过该步并提示） ----------
GH_REPO="${GH_REPO:-Ed-gjd/comfyui-learning}"     # GitHub 私有资料仓库
HF_REPO="${HF_REPO:-edwardhuangm/hongyi-lora}"     # HF 私有模型仓库（LoRA）
COMFYUI_SRC="${COMFYUI_SRC:-$HOME/comfyui}"        # ComfyUI 代码（WSL 原生区）
MODEL_DIR="${MODEL_DIR:-/mnt/d/comfyui-models}"    # 模型目录（D 盘）
HF_TOKEN="${HF_TOKEN:-}"                           # 可选；留空则用 ~/.cache/huggingface/token

SD15_NAME="v1-5-pruned-emaonly-fp16.safetensors"
SD15_URL="${SD15_URL:-<YOUR_MODELSCOPE_URL>}"      # 占位：填 SD1.5 fp16 的 ModelScope 直链
LORA_NAME="hongyi_lora.safetensors"

log()  { printf '\033[1;36m[restore]\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m[restore!]\033[0m %s\n' "$*"; }

# 占位符检测：含 <xxx> 视为未填
is_placeholder() { [[ "$1" == *"<"*">"* ]]; }

# ---------- 0. 依赖与凭证 ----------
for c in git gh hf curl; do
  command -v "$c" >/dev/null 2>&1 || { warn "缺少命令: $c —— 先安装再跑"; exit 1; }
done
gh auth status >/dev/null 2>&1 || warn "gh 未登录：先跑 gh auth login（私有资料仓库必需）"
[ -n "$HF_TOKEN" ] || [ -f "$HOME/.cache/huggingface/token" ] \
  || warn "HF 未登录：先跑 hf auth login（拉 LoRA 必需）"

# ---------- 1. 资料仓库 ----------
if [ ! -f "$PWD/README.md" ] && [ ! -f "$(dirname "$PWD")/README.md" ]; then
  log "克隆资料仓库 → $GH_REPO"
  git clone "https://github.com/$GH_REPO.git"
  cd "$(basename "$GH_REPO")"
fi
# 确保在仓库根目录（允许从 scripts/ 子目录运行）
[ -f "$PWD/README.md" ] || cd ..
log "资料已就位（README + workflows + scripts + pipeline 成片）"

# ---------- 2. ComfyUI 环境（已存在则跳过） ----------
if [ ! -d "$COMFYUI_SRC" ]; then
  log "安装 ComfyUI → $COMFYUI_SRC（国内源）"
  git clone https://github.com/comfyanonymous/ComfyUI.git "$COMFYUI_SRC"
  (
    cd "$COMFYUI_SRC"
    command -v uv >/dev/null || pip install uv
    uv venv .venv --python 3.12
    # shellcheck disable=SC1091
    source .venv/bin/activate
    pip install --index-url https://mirrors.aliyun.com/pypi/simple/ -r requirements.txt
    pip install --index-url https://mirrors.aliyun.com/pytorch-wheels/cpu/ torch
    cat > start_cpu.sh <<'S'
#!/usr/bin/env bash
cd "$(dirname "$0")"
exec .venv/bin/python main.py --cpu --listen 127.0.0.1 --port 8188
S
    chmod +x start_cpu.sh
  )
else
  log "ComfyUI 已在 $COMFYUI_SRC，跳过安装"
fi

# ---------- 3. 模型目录 + 软链 ----------
mkdir -p "$MODEL_DIR/checkpoints" "$MODEL_DIR/loras"
[ -e "$COMFYUI_SRC/models" ] || ln -s "$MODEL_DIR" "$COMFYUI_SRC/models"
log "模型目录: $MODEL_DIR（已软链到 ComfyUI）"

# ---------- 4. 下载模型（已存在则跳过） ----------
ckpt="$MODEL_DIR/checkpoints/$SD15_NAME"
if [ -f "$ckpt" ]; then
  log "SD1.5 已存在，跳过"
elif is_placeholder "$SD15_URL"; then
  warn "SD15_URL 是占位符未填，跳过 SD1.5 下载（在 restore.sh 顶部或环境变量里填 ModelScope 直链）"
else
  log "下载 SD1.5 fp16（ModelScope）→ $ckpt"
  curl -L -C - -o "$ckpt" "$SD15_URL"
fi

lora="$MODEL_DIR/loras/$LORA_NAME"
if [ -f "$lora" ]; then
  log "LoRA 已存在，跳过"
else
  log "下载 LoRA（HF 私有）→ $lora"
  [ -n "$HF_TOKEN" ] && export HF_TOKEN
  hf download "$HF_REPO" "$LORA_NAME" --local-dir "$MODEL_DIR/loras"
fi

# ---------- 5. 启动 ----------
log "启动 ComfyUI（CPU 模式）..."
nohup bash "$COMFYUI_SRC/start_cpu.sh" >/tmp/comfyui.log 2>&1 &
sleep 2
log "浏览器打开 http://127.0.0.1:8188 ；日志: /tmp/comfyui.log"
warn "注：大图批（flux2_modern/char_dataset 等）无云备份，需要的话从原机器拷贝"
