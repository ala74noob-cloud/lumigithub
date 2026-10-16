#!/bin/bash
# 字幕工作室 · 一键安装并启动（Mac）
# 第一次运行会自动安装需要的东西；以后再运行就直接启动。

cd "$(dirname "$0")" || exit 1

say_step() { printf '\n\033[1;33m▶ %s\033[0m\n' "$1"; }
fail() {
  printf '\n\033[1;31m✗ %s\033[0m\n' "$1"
  echo "把上面的内容截图或复制发给 Claude，让它帮你看。"
  read -r -p "按回车关闭…" _
  exit 1
}

if [ "$(uname)" != "Darwin" ]; then
  fail "这个脚本只用于 Mac。"
fi

# 已经在运行了：直接打开网页
if curl -s -o /dev/null http://127.0.0.1:8000/api/presets; then
  echo "字幕工作室已经在运行，正在打开浏览器…"
  open http://localhost:8000
  exit 0
fi

# 1. Homebrew
for b in /opt/homebrew/bin/brew /usr/local/bin/brew; do
  [ -x "$b" ] && eval "$("$b" shellenv)" && break
done
if ! command -v brew >/dev/null 2>&1; then
  say_step "安装 Homebrew（Mac 的软件安装工具）。会让你输入开机密码，输入时屏幕不显示字，输完按回车。"
  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)" \
    || fail "Homebrew 安装失败。"
  for b in /opt/homebrew/bin/brew /usr/local/bin/brew; do
    [ -x "$b" ] && eval "$("$b" shellenv)" && break
  done
  command -v brew >/dev/null 2>&1 || fail "装完 Homebrew 后找不到 brew。"
  # 以后打开终端也能用 brew
  if ! grep -q 'brew shellenv' "$HOME/.zprofile" 2>/dev/null; then
    echo "eval \"\$($(command -v brew) shellenv)\"" >> "$HOME/.zprofile"
  fi
fi

# 2. ffmpeg + Python 3.12
need=()
command -v ffmpeg >/dev/null 2>&1 || need+=(ffmpeg)
brew list python@3.12 >/dev/null 2>&1 || need+=(python@3.12)
if [ ${#need[@]} -gt 0 ]; then
  say_step "安装 ${need[*]}（要几分钟）"
  brew install "${need[@]}" || fail "安装 ${need[*]} 失败。"
fi
PY="$(brew --prefix python@3.12)/bin/python3.12"
[ -x "$PY" ] || fail "找不到 Python 3.12。"

# 3. 独立环境 + 依赖（requirements.txt 变了才重装）
if [ ! -x .venv/bin/python ]; then
  say_step "创建 Python 环境"
  "$PY" -m venv .venv || fail "创建 Python 环境失败。"
fi
REQ_HASH="$(shasum requirements.txt | cut -d' ' -f1)"
if [ "$(cat .venv/.req-hash 2>/dev/null)" != "$REQ_HASH" ]; then
  say_step "安装依赖（第一次大约 5–10 分钟）"
  .venv/bin/python -m pip install --upgrade pip -q
  .venv/bin/python -m pip install -r requirements.txt || fail "安装依赖失败。"
  echo "$REQ_HASH" > .venv/.req-hash
fi

# 4. 字体（失败也不影响使用，会用系统字体）
if [ ! -f fonts/NotoSansCJKsc-Bold.otf ]; then
  say_step "下载字体"
  .venv/bin/python fonts/download_fonts.py || echo "字体下载失败，先用系统字体，以后再运行会重试。"
fi

# 5. Claude API key
if ! grep -qE '^ANTHROPIC_API_KEY=sk-ant-' .env 2>/dev/null; then
  say_step "需要 Claude 的 API key（用来翻译）"
  echo "马上会打开 Anthropic 控制台：登录后点 「Create Key」，复制以 sk-ant- 开头的那串字。"
  sleep 2
  open "https://console.anthropic.com/settings/keys"
  while true; do
    read -r -p "把 key 粘贴到这里，然后按回车： " KEY
    KEY="$(echo "$KEY" | tr -d '[:space:]')"
    case "$KEY" in
      sk-ant-*) break ;;
      "") echo "（先跳过：识别和转写能用，翻译要等填好 key）"; break ;;
      *) echo "看起来不对，key 应该以 sk-ant- 开头，再试一次。（直接按回车可以先跳过）" ;;
    esac
  done
  [ -f .env ] || cp .env.example .env
  if [ -n "$KEY" ]; then
    grep -v '^ANTHROPIC_API_KEY=' .env > .env.tmp
    { echo "ANTHROPIC_API_KEY=$KEY"; cat .env.tmp; } > .env
    rm -f .env.tmp
    chmod 600 .env
    echo "已保存。"
  fi
fi

# 6. 启动，服务起来后自动打开浏览器
say_step "启动字幕工作室。用的时候别关这个窗口；要退出就关掉它。"
(
  for _ in $(seq 1 60); do
    if curl -s -o /dev/null http://127.0.0.1:8000/api/presets; then open http://localhost:8000; exit 0; fi
    sleep 1
  done
) &
.venv/bin/python app.py || fail "启动失败。"
